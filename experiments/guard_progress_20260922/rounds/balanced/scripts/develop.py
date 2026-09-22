"""Versioned development attempts; every profile applies across workloads."""
import argparse
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'guard_eurosys_20260921'
sys.path.insert(0, str(OLD/'scripts'))
import campaign
import analyze
campaign.ROOT = analyze.ROOT = ROOT
BASE = dict(guard_tail_congestion_gate=1, guard_adaptive_fabric_target=1,
            guard_queue_budget_bdps=4)
PROFILES = {
    'prior': dict(BASE, guard_receiver_concurrency=1, guard_concurrency_min_bdps=12),
    'no_k': BASE,
    'fair_half': dict(BASE, guard_min_share_fraction=.5),
    'fair_full': dict(BASE, guard_min_share_fraction=1),
    'short_adapt': dict(BASE, guard_adaptive_target_max_bdps=8),
    'short_adapt_fair': dict(BASE, guard_adaptive_target_max_bdps=8, guard_min_share_fraction=.5),
    'tail1': dict(BASE, guard_tail_bypass_bdps=1),
    'no_tail': dict(BASE, guard_tail_bypass=0),
    'no_adapt': dict(BASE, guard_adaptive_fabric_target=0),
    'short_ack1': dict(BASE, guard_adaptive_target_max_bdps=8, guard_ack_interval_packets=1),
    'short_quantum8': dict(BASE, guard_adaptive_target_max_bdps=8, guard_srpt_quantum_packets=8),
    'short_priority': dict(BASE, guard_adaptive_target_max_bdps=8, guard_initial_window_priority=1),
    'old': {},
}
for horizon in [64, 128]:
    for fraction in [0, .25, .5]:
        PROFILES[f'h{horizon}_f{int(fraction*100)}'] = dict(BASE,
            guard_adaptive_target_max_bdps=8, guard_receiver_concurrency=1,
            guard_concurrency_min_bdps=1, guard_scheduling_horizon_bdps=horizon,
            guard_min_share_fraction=fraction)
PROFILES['h128_min12'] = dict(PROFILES['h128_f0'], guard_concurrency_min_bdps=12)
PROFILES['h128_alladapt'] = dict(PROFILES['h128_f0'], guard_adaptive_target_max_bdps=0)
PROFILES['h128_lambda1'] = dict(PROFILES['h128_f0'], guard_lambda=1)
PROFILES['h128_lambda14'] = dict(PROFILES['h128_f0'], guard_lambda=1.4)
PROFILES['h128_k2'] = dict(PROFILES['h128_f0'], guard_receiver_concurrency=2)
PROFILES['h128_k4'] = dict(PROFILES['h128_f0'], guard_receiver_concurrency=4)
PROFILES['h128_rr'] = dict(PROFILES['h128_f0'], guard_sender_srpt=0)
PROFILES['h128_reclaim'] = dict(PROFILES['h128_f0'], guard_cap_aware_reclaim=1)
PROFILES['h128_work'] = dict(PROFILES['h128_f0'], guard_work_conserving=1, guard_rebalance_interval_us=8)
PROFILES['h128_min12_reclaim'] = dict(PROFILES['h128_min12'], guard_cap_aware_reclaim=1)
PROFILES['h128_min12_ack1'] = dict(PROFILES['h128_min12'], guard_ack_interval_packets=1)
PROFILES['h128_min12_ack4'] = dict(PROFILES['h128_min12'], guard_ack_interval_packets=4)
PROFILES['matched'] = dict(PROFILES['h128_min12'], guard_fabric_control=0)
PROFILES['legacy_rx'] = dict(PROFILES['h128_min12'], __cc='guard-active-only')
PROFILES['h128_no_tail'] = dict(PROFILES['h128_f0'], guard_tail_bypass=0)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--studies', nargs='+', required=True)
    p.add_argument('--profiles', nargs='+', required=True)
    p.add_argument('--seed', type=int, default=301)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--round', required=True)
    p.add_argument('--repo', default='/home/gengjiayao/ict/guard-balanced')
    a = p.parse_args()
    campaign.REPO = Path(a.repo)
    os.environ['GUARD_REPO'] = a.repo
    manifest = OLD/'manifest.json' if a.seed < 400 else ROOT.parent/'guard_optimization_20260921/holdout/confirmation-manifest.json'
    tasks = []
    for original in json.loads(manifest.read_text())['tasks']:
        if original['arm'] != 'guard' or original['seed'] != a.seed or original['study'] not in a.studies:
            continue
        for profile in a.profiles:
            task = copy.deepcopy(original)
            task['extra'] = dict(PROFILES[profile])
            task['cc'] = task['extra'].pop('__cc', 'guard')
            task['arm'] = a.round+'_'+profile
            task['key'] = f"{task['study']}-s{task['seed']}-{task['arm']}"
            tasks.append(task)
    assert len(tasks) == len(a.studies)*len(a.profiles)
    paths = [campaign.REPO/'run.py', campaign.REPO/'src/point-to-point/model/rdma-hw.cc',
             campaign.REPO/'src/point-to-point/model/rdma-hw.h', campaign.REPO/'build/scratch/network-load-balance',
             *sorted((campaign.REPO/'build').glob('libns3.19-*-optimized.so'))]
    record = dict(phase='development; observed seeds', tasks=tasks,
                  hashes={str(f.relative_to(campaign.REPO)):campaign.sha(f) for f in paths},
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=campaign.REPO,text=True).strip(),
                  source_diff=subprocess.check_output(['git','diff'],cwd=campaign.REPO,text=True))
    path = ROOT/(a.round+'-manifest.json')
    if path.exists():
        assert json.loads(path.read_text()) == record
    else:
        campaign.save(path, record)
    def run(task):
        result = campaign.run_one(task)
        if result['status'] == 'completed':
            m = analyze.summarize(result)['metrics']
            print('METRICS', task['key'], {k:m[k] for k in ['fct_mean_us','span_ms','drops','queue_worst_port_fixed_mean_us']}, flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in concurrent.futures.as_completed([pool.submit(run,t) for t in tasks]):
            f.result()

if __name__ == '__main__':
    main()
