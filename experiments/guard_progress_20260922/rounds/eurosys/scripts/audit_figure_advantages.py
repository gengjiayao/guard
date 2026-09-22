"""Audit paired effects from existing validated runs; does not rerun experiments."""
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T4 = 2.7764451051977987


def effect(guard, baseline):
    seeds = sorted(set(guard) & set(baseline))
    if len(seeds) != 5 or any(baseline[s] <= 0 for s in seeds):
        return None
    changes = [(guard[s] / baseline[s] - 1) * 100 for s in seeds]
    mean = statistics.mean(changes)
    half = T4 * statistics.stdev(changes) / len(seeds) ** 0.5
    return dict(seeds=seeds, guard_mean=statistics.mean(guard[s] for s in seeds),
                baseline_mean=statistics.mean(baseline[s] for s in seeds),
                paired_percent_changes=changes, percent_change=mean,
                ci95=[mean - half, mean + half])


def main():
    runs = json.loads((ROOT / 'analysis.json').read_text())['runs']
    groups = {}
    for run in runs:
        groups.setdefault(run['study'], {}).setdefault(run['arm'], {})[run['seed']] = run
    comparisons = []
    for study, arms in sorted(groups.items()):
        if 'guard' not in arms:
            continue
        for arm, baselines in sorted(arms.items()):
            if arm == 'guard':
                continue
            guards = arms['guard']
            metrics = set.intersection(*(set(r['metrics']) for r in [*guards.values(), *baselines.values()]))
            for metric in sorted(metrics):
                g = {s: r['metrics'][metric] for s, r in guards.items()}
                b = {s: r['metrics'][metric] for s, r in baselines.items()}
                if not all(isinstance(x, (float, int)) for x in [*g.values(), *b.values()]):
                    continue
                result = effect(g, b)
                if result:
                    comparisons.append(dict(study=study, baseline=arm, metric=metric, **result))
            if study in ('ali30', 'ali50'):
                for i in range(8):
                    for metric in ('mean', '95', '99', '99.9'):
                        result = effect({s: r['bins'][i][metric] for s, r in guards.items()},
                                        {s: r['bins'][i][metric] for s, r in baselines.items()})
                        if result:
                            comparisons.append(dict(study=study, baseline=arm,
                                metric='bin_slowdown_' + metric, bin_index=i,
                                lo=guards[min(guards)]['bins'][i]['lo'],
                                hi=guards[min(guards)]['bins'][i]['hi'], **result))
    result = dict(method='Mean of five seed-paired percentage changes, t(4) pointwise 95% CI; no multiplicity correction. Zero denominators omitted. Direction of benefit depends on metric; counters are not performance outcomes.',
                  input_sha256=hashlib.sha256((ROOT / 'analysis.json').read_bytes()).hexdigest(),
                  comparisons=comparisons)
    output = ROOT / 'audit/figure-advantage-effects.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    for study, baseline, metric in [('hybrid', 'receiver_only', 'fct_mean_us'),
            ('hybrid', 'receiver_only', 'queue_worst_port_fixed_mean_us'),
            ('hybrid', 'lambda1', 'span_ms'), ('ali50', 'no_oflm', 'grants')]:
        item = next(x for x in comparisons if x['study'] == study and x['baseline'] == baseline and x['metric'] == metric)
        print(study, baseline, metric, round(item['percent_change'], 3), item['ci95'])
    print(f'Wrote {len(comparisons)} paired comparisons to {output}')


if __name__ == '__main__':
    main()
