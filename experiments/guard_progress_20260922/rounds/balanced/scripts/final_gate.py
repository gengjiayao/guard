"""Verify the complete frozen matrix, matched controls and raw evidence."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REPO = Path('/home/gengjiayao/ict/guard-balanced-cohort')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def main():
    base = ROOT/'holdout'
    manifest = json.loads((base/'confirmation-manifest.json').read_text())
    series = json.loads((base/'series-manifest.json').read_text())
    assert manifest['hashes'] == series['hashes']
    for name, expected in manifest['hashes'].items():
        assert sha(REPO/name) == expected, name
    inputs = json.loads((ROOT/'input-provenance.json').read_text())
    for name, expected in inputs['topology_sha256'].items():
        assert sha(REPO/name) == expected, name
    tasks = manifest['tasks'] + series['tasks']
    records = {p.parent.name:json.loads(p.read_text()) for p in (base/'runs').glob('*/result.json')}
    assert len(tasks) == len({t['key'] for t in tasks})
    assert set(records) == {t['key'] for t in tasks}, (len(records),len(tasks))
    assert all(r['status']=='completed' for r in records.values())
    analysis = json.loads((base/'analysis.json').read_text())
    assert not analysis['failures'], analysis['failures']
    rows = {r['key']:r for r in analysis['runs']}
    assert set(rows)==set(records)
    assert all(r['metrics']['completion_fraction']==1 for r in rows.values())
    effects = json.loads((ROOT/'confirmation-evidence.json').read_text())
    assert effects['analysis_sha256']==sha(base/'analysis.json')

    def config(r):
        values = {}
        for line in Path(r['config']).read_text().splitlines():
            pair = line.split(maxsplit=1)
            if len(pair)==2:
                values[pair[0]]=pair[1]
        return values

    matched = []
    for task in tasks:
        if task['arm']!='receiver_only':
            continue
        key = task['key']
        fullkey = key.rsplit('-receiver_only',1)[0]+'-guard'
        f, a = config(records[fullkey]), config(records[key])
        # Output and private input paths are intentionally unique per run.
        differences = {k:(f.get(k),a.get(k)) for k in set(f)|set(a)
                       if f.get(k)!=a.get(k) and 'FILE' not in k and 'OUTPUT' not in k}
        assert differences == {'GUARD_FABRIC_CONTROL':('1','0')}, (key,differences)
        assert f['CC_MODE']==a['CC_MODE']=='11'
        assert rows[key]['metrics']['hpcc_changes']==0, key
        assert rows[key]['flow_sha256']==rows[fullkey]['flow_sha256']
        assert rows[key]['completion_identity_sha256']==rows[fullkey]['completion_identity_sha256']
        matched.append(key)

    development = json.loads((ROOT/'analysis.json').read_text())
    devtasks = [t for p in ROOT.glob('*-manifest.json') for t in json.loads(p.read_text())['tasks']]
    devrecords = {p.parent.name:json.loads(p.read_text()) for p in (ROOT/'runs').glob('*/result.json')}
    assert set(devrecords)=={t['key'] for t in devtasks}
    assert len(development['runs'])+len(development['failures'])==len(devrecords)
    # The observed directory collision is a preserved failed attempt, not a lost run.
    assert all(r['status']=='completed' or
               (r['key']=='fb40-s301-common_h128_min12' and r['status']=='error')
               for r in devrecords.values())
    assert 'fb40-s301-collision_fixed_h128_min12' in devrecords

    archive_index = json.loads((ROOT/'raw_index.json').read_text())
    expected_archives = {f'raw/{k}.tar.gz' for k in devrecords} | {
        f'holdout/raw/{k}.tar.gz' for k in records}
    assert set(archive_index)==expected_archives
    metrics = {(str(b.relative_to(ROOT)),p.parent.name):json.loads(p.read_text())
               for b in [ROOT,base] for p in (b/'runs').glob('*/metrics.json')}
    def verify(item):
        name, index = item
        path = ROOT/name
        assert sha(path)==index['sha256'], name
        b = base if name.startswith('holdout/') else ROOT
        result = (records if b==base else devrecords)[index['key']]
        assert result['status']==index['status']
        with tarfile.open(path,'r:gz') as tar:
            assert json.load(tar.extractfile('record/result.json'))==result
            if result['status']=='completed':
                row = metrics[(str(b.relative_to(ROOT)),index['key'])]
                for field,suffix in [('fct_sha256','_out_fct.txt'),
                                     ('stats_sha256','_out_guard_stats.txt'),
                                     ('queue_sha256','_out_queue_stats.txt')]:
                    member = next(n for n in tar.getnames() if n.startswith('raw/') and n.endswith(suffix))
                    assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==row[field], (name,field)
        return result['status']
    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(verify,archive_index.items()))
    output = dict(status='passed', source_commit=manifest['source_commit'],
                  confirmation_runs=len(records), development_attempts=len(devrecords),
                  completed_development_runs=len(development['runs']),
                  preserved_development_failures=development['failures'],
                  archived_attempts=len(statuses), complete_simulations=statuses.count('completed'),
                  matched_receiver_only_controls=matched, source_and_build='match frozen hashes',
                  all_flow_identities='verified within every study and seed',
                  raw_archives='all archive, result, FCT, stats and queue hashes verified',
                  performance='Correctness checks do not imply universal performance dominance.')
    (ROOT/'validation_checks.json').write_text(json.dumps(output,indent=2)+'\n')
    print('PASS',len(records),'confirmation runs;',len(devrecords),'development attempts;',len(matched),'matched controls')


if __name__=='__main__':
    main()
