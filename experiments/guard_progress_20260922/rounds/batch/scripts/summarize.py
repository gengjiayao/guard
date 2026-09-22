"""Validate every recorded development attempt and expose all tradeoffs."""
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/upstream'))
import analyze
analyze.ROOT = ROOT


def main():
    manifests = {p.stem:json.loads(p.read_text()) for p in ROOT.glob('*-manifest.json')}
    tasks = {t['key']:t for m in manifests.values() for t in m['tasks']}
    assert len(tasks)==sum(len(m['tasks']) for m in manifests.values())
    records = {p.parent.name:json.loads(p.read_text()) for p in (ROOT/'runs').glob('*/result.json')}
    assert set(records)==set(tasks), sorted(set(tasks)-set(records))
    rows, failures = [], []
    groups = defaultdict(list)
    for key, record in sorted(records.items()):
        for field in ['flow_sha256','seed','study','extra','cc']:
            assert record[field]==tasks[key][field], (key,field)
        if record['status']!='completed':
            failures.append(record)
            continue
        analyze.REPO = Path(record['output_dir']).parents[2]
        row = analyze.summarize(record)
        assert row['metrics']['completion_fraction']==1
        rows.append(row)
        groups[row['study'],row['seed']].append(row)
    for key, group in groups.items():
        assert len({r['flow_sha256'] for r in group})==1, key
        assert len({r['completion_identity_sha256'] for r in group})==1, key
    output = dict(stage='development only; observed seed 301',
                  attempts=len(records), completed=len(rows), failures=failures,
                  diagnostic_prefix_runs=sum('prefix' in r['study'] for r in rows),
                  complete_original_trace_runs=sum('prefix' not in r['study'] for r in rows),
                  runs=rows, goal_status='active; no universal advantage or independent validation claimed')
    (ROOT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Validated',len(rows),'complete development simulations;',len(failures),'preserved failed attempts')


if __name__=='__main__':
    main()
