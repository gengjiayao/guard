"""Preserve raw outputs for every finished attempt, including rejected runs."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def archive(path):
    result = json.loads(path.read_text())
    base = path.parents[2]
    output = base / 'raw' / (result['key'] + '.tar.gz')
    output.parent.mkdir(exist_ok=True)
    if not output.exists():
        tmp = output.with_suffix('.tmp')
        with tmp.open('wb') as f, gzip.GzipFile(filename='', mode='wb', fileobj=f, mtime=0, compresslevel=3) as gz, tarfile.open(fileobj=gz, mode='w|') as tar:
            files = [(p, 'record/' + p.name) for p in path.parent.iterdir() if p.is_file()]
            if 'output_dir' in result:
                files += [(p, 'raw/' + p.name) for p in Path(result['output_dir']).iterdir() if p.is_file()]
            for p, name in sorted(files, key=lambda x: x[1]):
                info = tar.gettarinfo(str(p), arcname=name)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                with p.open('rb') as src:
                    tar.addfile(info, src)
        tmp.replace(output)
    return str(output.relative_to(ROOT)), dict(sha256=sha(output), status=result['status'],
                                              key=result['key'], bytes=output.stat().st_size)


def main():
    paths = sorted((ROOT/'runs').glob('*/result.json')) + sorted((ROOT/'holdout/runs').glob('*/result.json'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        index = dict(pool.map(archive, paths))
    (ROOT/'raw_index.json').write_text(json.dumps(index, indent=2)+'\n')
    print('Archived', len(index), 'finished attempts, including failures')


if __name__ == '__main__':
    main()
