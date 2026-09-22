"""Freeze and run the selected profile on fresh, paired seeds without retuning."""
import argparse
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1] / 'holdout'
OLD = ROOT.parent.parent / 'guard_eurosys_20260921'
REPO = Path('/home/gengjiayao/ict/guard-balanced-cohort')
sys.path.insert(0, str(OLD / 'scripts'))
import campaign
import analyze
campaign.ROOT = ROOT
campaign.REPO = REPO
analyze.ROOT = ROOT
os.environ['GUARD_REPO'] = str(REPO)
PROFILE = dict(guard_adaptive_fabric_target=1, guard_tail_congestion_gate=1,
               guard_queue_budget_bdps=4, guard_receiver_concurrency=1,
               guard_concurrency_min_bdps=12, guard_adaptive_target_max_bdps=8,
               guard_scheduling_horizon_bdps=128)


def freeze():
    target = ROOT / 'confirmation-manifest.json'
    if target.exists():
        raise RuntimeError('Confirmation is already frozen')
    assert not subprocess.check_output(['git','diff','--name-only'], cwd=REPO, text=True).strip(), 'Commit tested source before freezing'
    ROOT.mkdir(exist_ok=True)
    if not (ROOT/'manifest.json').exists():
        campaign.SEEDS = [501,502,503,504,505]
        campaign.prepare()
    old = json.loads((ROOT / 'manifest.json').read_text())
    tasks = []
    for t in old['tasks']:
        task = copy.deepcopy(t)
        if task['cc'] in ('guard', 'guard-active-only'):
            task['extra'] = PROFILE | task['extra']
        tasks.append(task)
        if t['arm'] == 'guard':
            control = copy.deepcopy(t)
            control['arm'] = 'old_guard'
            control['key'] = f"{t['study']}-s{t['seed']}-old_guard"
            tasks.append(control)
    for task in list(tasks):
        if task['arm'] == 'receiver_only':
            legacy = copy.deepcopy(task)
            legacy['arm'] = 'receiver_only_legacy'
            legacy['key'] = f"{legacy['study']}-s{legacy['seed']}-receiver_only_legacy"
            tasks.append(legacy)
            task['cc'] = 'guard'
            task['extra']['guard_fabric_control'] = 0
    for seed in old['seeds']:
        rng = random.Random(seed)
        flow = ROOT / 'flows' / f'receiver2-s{seed}.txt'
        campaign.flow_file(flow, [(s, 8, 3, 8 * 1048576, 2.001 + rng.uniform(0, .5e-6)) for s in [0, 4]])
        for arm in ('guard', 'old_guard', 'hpcc', 'homa', 'dcqcn', 'timely', 'receiver_only', 'receiver_only_legacy'):
            t = copy.deepcopy(next(t for t in tasks if t['study'] == 'receiver' and t['seed'] == seed and t['arm'] == arm))
            t.update(study='receiver2', flow=str(flow), flow_sha256=campaign.sha(flow), flow_count=2)
            t['key'] = f'receiver2-s{seed}-{arm}'
            tasks.append(t)
    for seed in old['seeds']:
        for arm in ('receiver_only', 'receiver_only_legacy'):
            t = copy.deepcopy(next(t for t in tasks if t['study'] == 'ring' and t['seed'] == seed and t['arm'] == 'guard'))
            t['arm'] = arm
            t['cc'] = 'guard' if arm == 'receiver_only' else 'guard-active-only'
            if arm == 'receiver_only':
                t['extra']['guard_fabric_control'] = 0
            t['key'] = f"ring-s{seed}-{arm}"
            tasks.append(t)
    for study in ('fabric', 'hybrid'):
        for arm in ('guard', 'old_guard', 'hpcc', 'homa', 'dcqcn', 'timely', 'receiver_only', 'receiver_only_legacy'):
            t = copy.deepcopy(next(t for t in tasks if t['study'] == study and t['seed'] == 501 and t['arm'] == arm))
            t['study'] += '_series'
            t['monitor'] = 'full'
            t['extra'].update(qlen_monitoring_interval=1000, sw_monitoring_interval=1000)
            t['key'] = f"{t['study']}-s501-{arm}"
            tasks.append(t)
    for folder in ('runs', 'scripts'):
        (ROOT / folder).mkdir(exist_ok=True)
    shutil.copy2(ROOT.parent / 'scripts/config_only.py', ROOT / 'scripts/config_only.py')
    hashes = {str(p.relative_to(REPO)): campaign.sha(p) for p in
              [REPO/'build/scratch/network-load-balance', *sorted((REPO/'build').glob('libns3.19-*-optimized.so')),
               REPO/'run.py', REPO/'src/point-to-point/model/rdma-hw.cc', REPO/'src/point-to-point/model/rdma-hw.h', REPO/'scratch/network-load-balance.cc']}
    manifest = dict(phase='independent confirmation; no parameter changes after opening outcomes',
                    seeds=old['seeds'], profile=PROFILE,
                    source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                    hashes=hashes, tasks=tasks,
                    questions=['Does the ring loss collapse disappear?',
                               'Do directed receiver and mixed tests improve?',
                               'Does the receiver cohort policy recover storage, DP2, and fairness without losing Ring safety?',
                               'What latency, tail, fairness, and queue regressions remain across all workloads?'],
                    decision='Report all outcomes. No universal dominance claim unless each relevant comparison supports it. A candidate with material regressions will remain experimental, not replace the default.')
    campaign.save(target, manifest)
    print('Frozen', len(tasks), 'runs', manifest['source_commit'], flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['freeze', 'run', 'analyze'])
    p.add_argument('--studies', nargs='+')
    p.add_argument('--arms', nargs='+')
    p.add_argument('--workers', type=int, default=10)
    args = p.parse_args()
    if args.mode == 'freeze':
        return freeze()
    if args.mode == 'analyze':
        return analyze.main()
    m = json.loads((ROOT / 'confirmation-manifest.json').read_text())
    for name, expected in m['hashes'].items():
        assert campaign.sha(REPO / name) == expected, f'Frozen source/build changed: {name}'
    extra = ROOT/'series-manifest.json'
    all_tasks = m['tasks'] + (json.loads(extra.read_text())['tasks'] if extra.exists() else [])
    tasks = [t for t in all_tasks if (not args.studies or t['study'] in args.studies)
             and (not args.arms or t['arm'] in args.arms)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for f in concurrent.futures.as_completed([pool.submit(campaign.run_one, t) for t in tasks]):
            f.result()
    print('Finished requested shard', len(tasks), flush=True)


if __name__ == '__main__':
    main()
