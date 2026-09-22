"""Resumable development trials; old paper results remain immutable."""
import argparse
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'guard_eurosys_20260921'
sys.path.insert(0, str(OLD / 'scripts'))
import campaign
import analyze
campaign.ROOT = ROOT
analyze.ROOT = ROOT

PROFILES = {
    'default': {},
    'tail_gate': {'guard_tail_congestion_gate': 1},
    'tail_gate_k1': {'guard_tail_congestion_gate': 1, 'guard_receiver_concurrency': 1},
    'tail1': {'guard_tail_bypass_bdps': 1},
    'lambda1_gate': {'guard_lambda': 1, 'guard_tail_congestion_gate': 1},
    'adaptive_gate': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1},
    'adaptive_gate_k1': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                         'guard_receiver_concurrency': 1},
    'lambda1_gate_k1': {'guard_lambda': 1, 'guard_tail_congestion_gate': 1,
                        'guard_receiver_concurrency': 1},
    'adaptive_gate_k1_min1': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                             'guard_receiver_concurrency': 1, 'guard_concurrency_min_bdps': 1},
    'adaptive_gate_k1_reclaim': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                                'guard_receiver_concurrency': 1, 'guard_cap_aware_reclaim': 1},
    'adaptive_gate_k1_window': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                               'guard_receiver_concurrency': 1,
                               'guard_transport_window_floor_rtt_ns': 8320,
                               'guard_transport_window_ack_slack_packets': 16,
                               'guard_transport_window_whole_flow_first_gate': 1},
    'adaptive_gate_k1_ack1': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                             'guard_receiver_concurrency': 1, 'guard_ack_interval_packets': 1},
    'adaptive_gate_k1_min12': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                              'guard_receiver_concurrency': 1, 'guard_concurrency_min_bdps': 12},
    'adaptive_gate_k4_min12': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                              'guard_receiver_concurrency': 4, 'guard_adaptive_elephant_concurrency': 1,
                              'guard_concurrency_min_bdps': 12},
    'adaptive_gate_e2': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                         'guard_remaining_exponent': 2},
    'adaptive_gate_budget4': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                              'guard_queue_budget_bdps': 4},
    'adaptive_gate_budget4_k1': {'guard_adaptive_fabric_target': 1, 'guard_tail_congestion_gate': 1,
                                'guard_queue_budget_bdps': 4, 'guard_receiver_concurrency': 1,
                                'guard_concurrency_min_bdps': 12},
}
_v34 = json.loads((campaign.REPO / 'experiments/campaigns/guard_v34_cap_triggered_refresh_development.json').read_text())
PROFILES['serialized'] = {k: v for k, v in _v34['defaults'].items() if k.startswith('guard_')}
PROFILES['serialized'].update({k: v for k, v in _v34['arms']['guard_ack_slack_window'].items() if k.startswith('guard_')})
PROFILES['serialized_safe'] = dict(PROFILES['serialized'], guard_tail_congestion_gate=1, guard_adaptive_fabric_target=1)


def run(t):
    r = campaign.run_one(t)
    if r['status'] == 'completed':
        m = analyze.summarize(r)
        print('METRICS', t['key'], json.dumps({k: m['metrics'][k] for k in
              ['fct_mean_us', 'span_ms', 'drops', 'queue_worst_port_fixed_mean_us', 'hpcc_changes']}), flush=True)
    return r


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--studies', nargs='+', default=['hybrid', 'ring'])
    p.add_argument('--profiles', nargs='+', default=list(PROFILES))
    p.add_argument('--seeds', nargs='+', type=int, default=[301])
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--round', default='diagnosis')
    p.add_argument('--repo', default=str(campaign.REPO))
    p.add_argument('--variant', default='')
    args = p.parse_args()
    campaign.REPO = Path(args.repo)
    os.environ['GUARD_REPO'] = args.repo
    old = json.loads((OLD / 'manifest.json').read_text())
    tasks = []
    for template in old['tasks']:
        if template['arm'] != 'guard' or template['study'] not in args.studies or template['seed'] not in args.seeds:
            continue
        for profile in args.profiles:
            task = copy.deepcopy(template)
            task['arm'] = args.variant + profile
            task['key'] = f"{task['study']}-s{task['seed']}-{task['arm']}"
            task['extra'].update(PROFILES[profile])
            tasks.append(task)
    manifest = dict(phase='development, not held-out validation', old_manifest_sha256=campaign.sha(OLD/'manifest.json'),
                    binary_sha256=campaign.sha(campaign.REPO/'build/scratch/network-load-balance'),
                    rdma_source_sha256=campaign.sha(campaign.REPO/'src/point-to-point/model/rdma-hw.cc'),
                    point_to_point_library_sha256=campaign.sha(campaign.REPO/'build/libns3.19-point-to-point-optimized.so'),
                    profiles={p: PROFILES[p] for p in args.profiles}, tasks=tasks)
    path = ROOT / (args.round + '-manifest.json')
    if path.exists():
        assert json.loads(path.read_text()) == manifest, 'Immutable manifest mismatch; choose a new round name'
    else:
        campaign.save(path, manifest)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for f in concurrent.futures.as_completed([pool.submit(run, t) for t in tasks]):
            f.result()
    analyze.main()


if __name__ == '__main__':
    main()
