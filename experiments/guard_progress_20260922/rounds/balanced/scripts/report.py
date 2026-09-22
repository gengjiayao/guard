"""Produce paired outcome evidence and vector plots for the frozen candidate."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'holdout'
OUT = ROOT / 'figures'
OUT.mkdir(exist_ok=True)
T4 = 2.7764451051977987
STUDIES = ['ali30', 'ali50', 'web40', 'fb40', 'fabric', 'receiver2', 'receiver',
           'hybrid', 'fairness', 'alltoall', 'allreduce_dp2', 'ring']
NAMES = ['Storage 30%', 'Storage 50%', 'Web search', 'Analytics', 'Fabric',
         '2-sender incast', '4-sender incast', 'Mixed bottleneck', 'Dynamic sharing',
         'All-to-All', 'DP2 exchange', 'Ring']
METRICS = ['fct_mean_us', 'slowdown_p99', 'span_ms', 'queue_worst_port_fixed_mean_us',
           'drops', 'timeout_recoveries', 'grants', 'mean_flow_goodput_gbps']


def ci(values):
    mean = statistics.mean(values)
    half = T4 * statistics.stdev(values) / len(values) ** .5
    return mean, half


def main():
    data = json.loads((DATA / 'analysis.json').read_text())
    groups = defaultdict(dict)
    for r in data['runs']:
        groups[r['study'], r['arm']][r['seed']] = r
    paired = []
    for (study, baseline), b in sorted(groups.items()):
        if baseline == 'guard':
            continue
        g = groups[study, 'guard']
        seeds = sorted(g.keys() & b.keys())
        if len(seeds) != 5:
            continue
        for metric in METRICS:
            gv = [g[s]['metrics'][metric] for s in seeds]
            bv = [b[s]['metrics'][metric] for s in seeds]
            if any(x <= 0 for x in bv):
                continue
            values = [100 * (x / y - 1) for x, y in zip(gv, bv)]
            m, h = ci(values)
            paired.append(dict(study=study, baseline=baseline, metric=metric,
                               seeds=seeds, values=values, percent_change=m, ci95=[m-h, m+h],
                               guard_mean=statistics.mean(gv), baseline_mean=statistics.mean(bv),
                               run_keys=[g[s]['key'] for s in seeds] + [b[s]['key'] for s in seeds]))
    index = {(r['study'], r['baseline'], r['metric']): r for r in paired}
    plt.rcParams.update({'font.size': 10, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 3, figsize=(12, 6.5), sharey=True)
    for ax, metric, title in zip(axes, ['fct_mean_us', 'span_ms', 'queue_worst_port_fixed_mean_us'],
                                 ['Mean flow completion time', 'Trace completion span', 'Worst-port mean queue']):
        ax.axvline(0, color='0.4', lw=.8)
        for i, study in enumerate(STUDIES):
            row = index.get((study, 'old_guard', metric))
            if row:
                v = row['percent_change']; lo, hi = row['ci95']
                color = '#167548' if hi < 0 else '#b34438' if lo > 0 else '#555555'
                ax.errorbar(v, i, xerr=[[v-lo], [hi-v]], fmt='o', color=color, capsize=3)
            else:
                ax.text(.03, i, 'pending', transform=ax.get_yaxis_transform(), color='0.6')
        ax.set_title(title)
        ax.set_xlabel('Change from previous GUARD (%)\nNegative is better')
        ax.grid(axis='x', alpha=.2)
    axes[0].set_yticks(range(len(STUDIES)), NAMES)
    axes[0].set_ylim(len(STUDIES)-.5, -.5)
    fig.suptitle('One frozen candidate; paired seeds 501–505; pointwise 95% intervals')
    fig.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(OUT / ('optimization_effects.' + ext), dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(14, 6.5), sharey=True)
    for ax, baseline, label in zip(axes, ['hpcc', 'homa', 'dcqcn', 'timely'], ['HPCC', 'Homa', 'DCQCN', 'TIMELY']):
        ax.axvline(0, color='0.4', lw=.8)
        for i, study in enumerate(STUDIES):
            row = index.get((study, baseline, 'fct_mean_us'))
            if row:
                v = row['percent_change']; lo, hi = row['ci95']
                color = '#167548' if hi < 0 else '#b34438' if lo > 0 else '#555555'
                ax.errorbar(v, i, xerr=[[v-lo], [hi-v]], fmt='o', color=color, capsize=3)
            else:
                ax.text(.03, i, 'not evaluated', transform=ax.get_yaxis_transform(), color='0.6', fontsize=8)
        ax.set_title('Candidate vs. ' + label)
        ax.set_xlabel('Mean-FCT change (%)\nNegative is better')
        ax.grid(axis='x', alpha=.2)
    axes[0].set_yticks(range(len(STUDIES)), NAMES)
    axes[0].set_ylim(len(STUDIES)-.5, -.5)
    fig.suptitle('Mean-FCT changes; paired seeds 501–505; pointwise 95% intervals')
    fig.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(OUT / ('baseline_comparison.' + ext), dpi=170)
    plt.close(fig)

    fairness = {}
    arms = ['old_guard', 'guard', 'hpcc', 'homa', 'dcqcn', 'timely']
    labels = ['Previous\nGUARD', 'Candidate\nGUARD', 'HPCC', 'Homa', 'DCQCN', 'TIMELY']
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    for i, arm in enumerate(arms):
        runs = groups['fairness', arm]
        if len(runs) == 5:
            values = []
            for r in runs.values():
                v = np.loadtxt(next(Path(r['output_dir']).glob('*_flow_bw.txt')), ndmin=2)
                rates = np.array([v[(v[:,1] == s) & (v[:,0] > 1e7) & (v[:,0] <= 1.2e7),5].sum()/20 for s in range(4)])
                values.append(float(rates.sum()**2/(4*(rates**2).sum())))
            m, h = ci(values)
            fairness[arm] = dict(mean=m, ci95=[m-h,m+h], values=values)
            axes[0].bar(i, m, yerr=h, capsize=3, color='#467da2')
            axes[0].text(i, m+h+.012, f'{m:.3f}', ha='center', fontsize=8)
        ring = list(groups['ring', arm].values())
        if len(ring) == 5:
            for ax, metric in zip(axes[1:], ['span_ms', 'drops']):
                m, h = ci([r['metrics'][metric] for r in ring])
                ax.bar(i, m, yerr=h, capsize=3, color='#467da2')
                if metric == 'span_ms':
                    ax.text(i, m+h+1.3, f'{m:.2f}', ha='center', fontsize=8)
                if metric == 'drops' and m == 0:
                    ax.text(i, 0, '0', ha='center', va='bottom', fontsize=9)
    axes[0].set_title('Dynamic-sharing equality')
    axes[0].set_ylabel('Jain index, 10–12 ms')
    axes[0].set_ylim(0, 1.08)
    axes[1].set_title('Ring completion span')
    axes[1].set_ylabel('Time (ms)')
    axes[2].set_title('Ring dropped packets')
    axes[2].set_ylabel('Packets (symlog scale)')
    axes[2].set_yscale('symlog', linthresh=1)
    for ax in axes:
        ax.set_xticks(range(6), labels, rotation=40, ha='right')
        ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(OUT / ('safety_and_fairness.' + ext), dpi=170)
    plt.close(fig)
    output = dict(analysis_sha256=hashlib.sha256((DATA/'analysis.json').read_bytes()).hexdigest(),
                  method='Five seed-paired changes; pointwise t(4) 95% CI; no multiplicity correction.',
                  validated_runs=len(data['runs']), failures=data['failures'],
                  comparisons=paired, fairness=fairness)
    (ROOT / 'confirmation-evidence.json').write_text(json.dumps(output, indent=2)+'\n')
    print('Wrote', len(paired), 'comparisons and three vector figures')


if __name__ == '__main__':
    main()
