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
REPO = Path('/home/gengjiayao/ict/guard-homastable')
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
SHARED = dict(BASE, guard_single_sender_shared_cap_bdps=128)
TRACE = dict(guard_controller_trace=1, guard_controller_max_lines=300000,
             guard_controller_sample_ns=100000)
PROFILES = {'shared': SHARED,
            'shared_trace': dict(SHARED, **TRACE),
            'shared_l10': dict(SHARED, guard_lambda=1)}
for bound in [8,32]:
    PROFILES[f'recovery{bound}'] = dict(SHARED, guard_recovery_max_rtts=bound)
    PROFILES[f'recovery{bound}_trace'] = dict(PROFILES[f'recovery{bound}'], **TRACE)
PROFILES['startup_wide'] = dict(SHARED, guard_startup_fairshare_bdps=128)
PROFILES['startup_peer'] = dict(PROFILES['startup_wide'], guard_startup_same_peer=1)
PROFILES['peer_trace'] = dict(PROFILES['startup_peer'], guard_controller_trace=1, guard_controller_max_lines=300000, guard_controller_sample_ns=1000)
PROFILES['shared_fb_trace'] = dict(SHARED, guard_controller_trace=1, guard_controller_max_lines=300000, guard_controller_sample_ns=1000)
PROFILES['joint8'] = dict(PROFILES['startup_peer'], guard_recovery_max_rtts=8)
PROFILES['joint32'] = dict(PROFILES['startup_peer'], guard_recovery_max_rtts=32)
PROFILES['joint32_l10'] = dict(PROFILES['joint32'], guard_lambda=1)
PROFILES['joint32_trace'] = dict(PROFILES['joint32'], **TRACE)
PROFILES['joint8_fb_trace'] = dict(PROFILES['joint8'], guard_controller_trace=1, guard_controller_max_lines=300000, guard_controller_sample_ns=1000)
PROFILES['l10_ack1'] = dict(PROFILES['shared_l10'], guard_ack_interval_packets=1)
PROFILES['l10_last'] = dict(PROFILES['shared_l10'], guard_keep_last_hop_int=1)
PROFILES['l10_ack1_last'] = dict(PROFILES['l10_ack1'], guard_keep_last_hop_int=1)
PROFILES['recovery8_l10'] = dict(PROFILES['recovery8'], guard_lambda=1)
for name in ['joint32_l10','shared_l10','l10_ack1','l10_last','l10_ack1_last']:
    PROFILES[name+'_trace'] = dict(PROFILES[name], **TRACE)
for name in ['shared','joint32','joint32_l10','shared_l10']:
    PROFILES[name+'_deadline'] = dict(PROFILES[name], guard_ack_max_delay_rtts=1)
PROFILES['joint32_l10_deadline_trace'] = dict(PROFILES['joint32_l10_deadline'], **dict(TRACE, guard_controller_sample_ns=1000000))
for name in ['l10_ack1','l10_ack1_last']:
    PROFILES[name+'_trace_full'] = dict(PROFILES[name+'_trace'], guard_controller_max_lines=300000, guard_controller_sample_ns=1000000)
for name in ['shared','joint32','joint32_l10_deadline']:
    PROFILES[name+'_cursor'] = dict(PROFILES[name], guard_sender_fair_cursor=1)
for baseline in ['hpcc','homa','dcqcn','timely']:
    PROFILES[baseline] = {'__cc':baseline}

for enabled,label in [(0,'legacy'),(1,'stable')]:
    for buckets,suffix in [(0,'a'),(0,'b'),(11,'small'),(257,'large')]:
        PROFILES['homa_'+label+'_'+suffix] = dict(__cc='homa', homa_stable_resend_order=enabled, homa_diagnostic_hash_buckets=buckets)

for name in ['shared','joint32','shared_l10']:
    PROFILES[name+'_cursor'] = dict(PROFILES[name], guard_sender_fair_cursor=1)
    PROFILES[name+'_batch'] = dict(PROFILES[name+'_cursor'], guard_sender_ack_batch=1)
PROFILES['shared_l10_batch_trace'] = dict(PROFILES['shared_l10_batch'], **dict(TRACE, guard_controller_sample_ns=1000000))

PROFILES['shared_l10_cursor_trace'] = dict(PROFILES['shared_l10_cursor'], **dict(TRACE, guard_controller_sample_ns=1000000))
for name in ['shared','joint32','shared_l10']:
    PROFILES[name+'_budget'] = dict(PROFILES[name+'_cursor'], guard_sender_service_budget=1)
for name in ['shared','shared_l10']:
    PROFILES[name+'_budget_batch'] = dict(PROFILES[name+'_budget'], guard_sender_ack_batch=1)
PROFILES['shared_l10_budget_trace'] = dict(PROFILES['shared_l10_budget'], **dict(TRACE, guard_controller_sample_ns=1000000))

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
    snapshot = ROOT/'harness_snapshots'/args.round
    if not snapshot.exists():
        import shutil
        shutil.copytree(ROOT/'scripts', snapshot, ignore=shutil.ignore_patterns('__pycache__'))
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
