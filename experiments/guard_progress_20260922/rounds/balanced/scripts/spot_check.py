"""Independently recompute FCT means, including the predeclared warmup rule."""
import json
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT/'confirmation-evidence.json').read_text())
    output = {'method': 'Raw FCT column 6 in ns; published cohort uses input start time '
              '(column 5) > (2 + frozen warmup) seconds. All completions are retained '
              'for eligible starts, without a completion-time cutoff.', 'studies': {}}
    for study in ['ali50', 'allreduce_dp2']:
        scopes = {scope: {} for scope in ['all_flows_including_warmup', 'published_cohort']}
        for arm in ['guard', 'old_guard', 'homa']:
            for means in scopes.values():
                means[arm] = []
            for seed in range(501, 506):
                path = ROOT/'holdout/runs'/f'{study}-s{seed}-{arm}'
                record = json.loads((path/'result.json').read_text())
                assert record['status'] == 'completed'
                raw = np.loadtxt(next(Path(record['output_dir']).glob('*_out_fct.txt')),
                                 usecols=(5, 6), dtype=np.int64, ndmin=2)
                cutoff = int((2 + record['warmup'])*1e9)
                selected = raw[raw[:, 0] > cutoff, 1]/1000
                scopes['all_flows_including_warmup'][arm].append(float(raw[:, 1].mean()/1000))
                scopes['published_cohort'][arm].append(float(selected.mean()))
                saved = json.loads((path/'metrics.json').read_text())['metrics']
                assert np.isclose(selected.mean(), saved['fct_mean_us'], rtol=1e-12)
                assert len(selected) == saved['eligible_flows']
        output['studies'][study] = {}
        for scope, means in scopes.items():
            effects = {}
            for baseline in ['old_guard', 'homa']:
                values = [100*(g/b-1) for g, b in zip(means['guard'], means[baseline])]
                mean = statistics.mean(values)
                half = 2.7764451051977987*statistics.stdev(values)/5**.5
                effects[baseline] = {'mean': mean, 'ci95': [mean-half, mean+half]}
                if scope == 'published_cohort':
                    item = next(x for x in evidence['comparisons'] if x['study']==study
                                and x['baseline']==baseline and x['metric']=='fct_mean_us')
                    assert np.isclose(mean, item['percent_change'], rtol=1e-12)
                    assert np.allclose([mean-half, mean+half], item['ci95'], rtol=1e-12)
            output['studies'][study][scope] = {'mean_fct_us_by_seed': means, 'changes': effects}
    output['status'] = 'passed; 30 raw run means and four paired comparisons match published metrics'
    (ROOT/'raw-fct-spot-check.json').write_text(json.dumps(output, indent=2)+'\n')
    print(output['status'])


if __name__ == '__main__':
    main()
