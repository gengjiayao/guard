"""Check behavioral invariants using complete network runs, not mocked formulas."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(key):
    return json.loads((ROOT/'runs'/key/'metrics.json').read_text())


def main():
    previous = read('ring-s301-default')
    fixed = read('ring-s301-scope_adaptive_gate_budget4_k1')
    assert previous['completion_identity_sha256'] == fixed['completion_identity_sha256']
    assert previous['metrics']['drops'] > 0 and previous['metrics']['hpcc_changes'] == 0
    assert fixed['metrics']['drops'] == 0 and fixed['metrics']['hpcc_changes'] > 0
    assert fixed['stats']['guard_tail_gate_qualified_flows'] == 480

    before = read('allreduce_dp2-s301-queue_adaptive_gate_budget4_k1')
    after = read('allreduce_dp2-s301-scope_adaptive_gate_budget4_k1')
    assert before['completion_identity_sha256'] == after['completion_identity_sha256']
    assert before['stats']['guard_concurrency_limited_allocations'] > 0
    assert after['stats']['guard_concurrency_limited_allocations'] == 0
    assert after['metrics']['fct_mean_us'] < before['metrics']['fct_mean_us']
    incast = read('receiver2-s301-scope_adaptive_gate_budget4_k1')
    assert incast['stats']['guard_concurrency_limited_allocations'] > 0

    data = json.loads((ROOT/'holdout/analysis.json').read_text())
    assert not data['failures'], data['failures']
    guards = [r for r in data['runs'] if r['arm'] == 'guard']
    ring = [r for r in guards if r['study'] == 'ring']
    assert sorted(r['seed'] for r in ring) == [401,402,403,404,405]
    for r in ring:
        assert r['valid'] and r['metrics']['completion_fraction'] == 1
        assert r['metrics']['drops'] == 0 and r['metrics']['hpcc_changes'] > 0
    for r in guards:
        assert r['valid'] and r['metrics']['completion_fraction'] == 1
    result = dict(status='passed', checks=[
        'Matched ring input/completions; old zero feedback and loss reproduced',
        'Candidate ring has active feedback and zero loss across five fresh seeds',
        'Sender-scope correction removes redundant DP2 concurrency limiting',
        'The same correction retains concurrency limiting for actual incast',
        'All analyzed candidate flows complete and pass identity validation'],
        guard_runs_checked=len(guards),
        limitation='These checks establish mechanism behavior and completion integrity, not universal performance superiority.')
    (ROOT/'mechanism-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
