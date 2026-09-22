"""Frozen per-round development probes; no outcome-dependent task replacement."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = Path('/home/gengjiayao/ict/guard-flowaware')
OLD = ROOT.parent/'guard_eurosys_20260921'
sys.path.insert(0, str(ROOT/'scripts/upstream'))
import campaign
import analyze
campaign.ROOT = analyze.ROOT = ROOT
campaign.REPO = analyze.REPO = REPO
os.environ['GUARD_REPO'] = str(REPO)
BASE = dict(guard_tail_congestion_gate=1, guard_adaptive_fabric_target=1,
            guard_queue_budget_bdps=4, guard_adaptive_target_max_bdps=8,
            guard_receiver_concurrency=1, guard_concurrency_min_bdps=12,
            guard_scheduling_horizon_bdps=128)
PROFILES = {'reference': BASE,
            'single_order': dict(BASE, guard_single_sender_order=1),
            'single_no_fabric': dict(BASE, guard_single_sender_order=1, guard_fabric_control=0)}
for size in [2, 4, 8]:
    PROFILES[f'window{size}'] = dict(BASE, guard_post_grant_window_bdps=size)
    PROFILES[f'order_window{size}'] = dict(BASE, guard_single_sender_order=1,
                                        guard_post_grant_window_bdps=size)
PROFILES['order_window4_no_fabric'] = dict(PROFILES['order_window4'], guard_fabric_control=0)
for threshold in [1, 128]:
    for size in [1, 2, 4]:
        PROFILES[f'share{threshold}_window{size}'] = dict(BASE,
            guard_single_sender_shared_cap_bdps=threshold, guard_post_grant_window_bdps=size)
for gain in [1.0, 1.2, 1.4]:
    for size in [1, 2]:
        PROFILES[f'share128_l{int(gain*10)}_window{size}'] = dict(
            PROFILES[f'share128_window{size}'], guard_lambda=gain)
for exponent in [0, .5, 1.5, 2]:
    PROFILES[f'weight{int(exponent*10)}'] = dict(PROFILES['share128_window1'],
                                              guard_remaining_exponent=exponent)
PROFILES['weight5_window2'] = dict(PROFILES['share128_window2'], guard_remaining_exponent=.5)
PROFILES['service'] = dict(PROFILES['share128_window1'], guard_sender_service_time=1)
PROFILES['service_window2'] = dict(PROFILES['share128_window2'], guard_sender_service_time=1)
PROFILES['service_weight5'] = dict(PROFILES['service'], guard_remaining_exponent=.5)
for slots in [2, 4, 8, 16]:
    PROFILES[f'slots{slots}'] = dict(PROFILES['share128_window1'], guard_single_sender_shared_slots=slots)
for baseline in ['hpcc','homa','dcqcn','timely']:
    PROFILES[baseline] = {'__cc':baseline}


def main():
    global REPO
    parser = argparse.ArgumentParser()
    parser.add_argument('--studies', nargs='+', required=True)
    parser.add_argument('--profiles', nargs='+', choices=sorted(PROFILES), required=True)
    parser.add_argument('--round', required=True)
    parser.add_argument('--workers', type=int, default=12)
    parser.add_argument('--repo', default=str(REPO))
    parser.add_argument('--prefix-buckets', type=int, default=0,
                        help='diagnostic prefix of DP2; never a replacement for the original trace')
    args = parser.parse_args()
    REPO = Path(args.repo)
    campaign.REPO = analyze.REPO = REPO
    os.environ['GUARD_REPO'] = str(REPO)
    if args.prefix_buckets:
        assert args.studies==['allreduce_dp2'] and 1<=args.prefix_buckets<=80
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'], cwd=REPO, text=True).strip()
    tasks = []
    original = json.loads((OLD/'manifest.json').read_text())
    for task in original['tasks']:
        if task['seed']!=301 or task['arm']!='guard' or task['study'] not in args.studies:
            continue
        for profile in args.profiles:
            item = copy.deepcopy(task)
            if args.prefix_buckets:
                item['study'] += '_prefix'+str(args.prefix_buckets)
                inputs = ROOT/'diagnostic-flows'
                inputs.mkdir(exist_ok=True)
                flow = inputs/(item['study']+'-s301.txt')
                lines = Path(item['flow']).read_text().splitlines()[1:]
                lines = lines[:16*args.prefix_buckets]
                content = str(len(lines))+'\n'+'\n'.join(lines)+'\n'
                if flow.exists():
                    assert flow.read_text()==content
                else:
                    flow.write_text(content)
                item.update(flow=str(flow),flow_sha256=campaign.sha(flow),flow_count=len(lines),
                            duration=args.prefix_buckets*.0025+.005,monitor='full')
            item['arm'] = args.round+'_'+profile
            item['key'] = f"{item['study']}-s301-{item['arm']}"
            item['extra'] = dict(PROFILES[profile])
            item['cc'] = item['extra'].pop('__cc','guard')
            tasks.append(item)
    assert len(tasks)==len(args.studies)*len(args.profiles)
    files = [REPO/'build/scratch/network-load-balance', *sorted((REPO/'build').glob('libns3.19-*-optimized.so'))]
    hashes = {str(p.relative_to(REPO)): campaign.sha(p) for p in files}
    record = dict(phase='development on observed seed 301; never independent confirmation',
        tasks=tasks, hashes=hashes,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip(),
        harness_hashes={str(p.relative_to(ROOT)):campaign.sha(p) for p in (ROOT/'scripts').rglob('*.py')},
        topology_hashes={name:campaign.sha(REPO/'config'/f'{name}.txt') for name in {t['topo'] for t in tasks}})
    manifest = ROOT/(args.round+'-manifest.json')
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        for field in ['tasks','hashes','source_commit','topology_hashes']:
            assert previous[field]==record[field], field
    else:
        campaign.save(manifest,record)
    def run(task):
        result = campaign.run_one(task)
        if result['status']=='completed':
            m = analyze.summarize(result)['metrics']
            print('METRICS', task['key'], {k:m[k] for k in
                ['fct_mean_us','slowdown_p99','span_ms','queue_worst_port_fixed_mean_us','drops']}, flush=True)
        return result
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = [f.result() for f in as_completed([pool.submit(run,t) for t in tasks])]
    assert all(campaign.sha(REPO/p)==h for p,h in hashes.items()), 'build changed during round'
    print('ROUND FINISHED', args.round, len(results), 'failures',
          [r['key'] for r in results if r['status']!='completed'], flush=True)


if __name__=='__main__':
    main()
