"""Verify the reported confirmation cohort and all archived attempts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REPO = Path('/home/gengjiayao/ict/guard-optimization')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    manifest = json.loads((ROOT/'holdout/confirmation-manifest.json').read_text())
    for name, expected in manifest['hashes'].items():
        assert sha(REPO/name) == expected, name
    wanted = manifest['tasks']  # Follow-up completes the original 75 missing cells.
    records = {p.parent.name: json.loads(p.read_text()) for p in (ROOT/'holdout/runs').glob('*/result.json')}
    assert set(records) == {t['key'] for t in wanted}
    assert all(r['status'] == 'completed' for r in records.values())
    analysis = json.loads((ROOT/'holdout/analysis.json').read_text())
    assert not analysis['failures']
    assert {r['key'] for r in analysis['runs']} == set(records)
    effects = json.loads((ROOT/'confirmation-evidence.json').read_text())
    assert effects['analysis_sha256'] == sha(ROOT/'holdout/analysis.json')
    metrics = {}
    for base in (ROOT, ROOT/'holdout'):
        for path in (base/'runs').glob('*/metrics.json'):
            metrics[str(base.relative_to(ROOT)) + '/' + path.parent.name] = json.loads(path.read_text())
    index = json.loads((ROOT/'raw_index.json').read_text())

    def verify(item):
        name, entry = item
        path = ROOT/name
        assert sha(path) == entry['sha256'], name
        base = ROOT/'holdout' if name.startswith('holdout/') else ROOT
        result = json.loads((base/'runs'/entry['key']/'result.json').read_text())
        assert result['status'] == entry['status']
        with tarfile.open(path, 'r:gz') as tar:
            saved = json.load(tar.extractfile('record/result.json'))
            assert saved == result, name
            row = metrics.get(str(base.relative_to(ROOT)) + '/' + entry['key'])
            if result['status'] == 'completed':
                assert row is not None, name
                members = tar.getnames()
                checks = [('fct_sha256', '_out_fct.txt'), ('stats_sha256', '_out_guard_stats.txt'),
                          ('queue_sha256', '_out_queue_stats.txt')]
                for field, suffix in checks:
                    member = next(n for n in members if n.startswith('raw/') and n.endswith(suffix))
                    assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == row[field], (name,field)
        return entry['status']

    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(verify, index.items()))
    report = dict(status='passed', confirmation_runs=len(records),
                  archived_attempts=len(index), completed_simulations=statuses.count('completed'),
                  rejected_or_failed_attempts=len(statuses)-statuses.count('completed'),
                  planned_but_unexecuted=[t['key'] for t in manifest['tasks'] if t['key'] not in records],
                  source_build_hashes='match frozen confirmation manifest',
                  raw_checks='All archives, result records, and completed FCT/stats/queue hashes verified',
                  performance_decision='Experimental only; not promoted because of storage, DP2, and fairness regressions')
    (ROOT/'validation_checks.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k:v for k,v in report.items() if k != 'planned_but_unexecuted'})


if __name__ == '__main__':
    main()
