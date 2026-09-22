"""Move unstarted frozen tasks to spare workers without duplicate simulations.

The original scheduler is briefly stopped while reservations are installed.
Already-running simulators continue. Its run_one skips reserved result records;
the assisting workers replace those explicit pending records with real results.
No inputs, parameters, binary, or outcomes are changed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import inspect
import json
import os
from pathlib import Path
import signal
import sys
import time

import confirm


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scheduler-pid',type=int,required=True)
    p.add_argument('--seeds',type=int,nargs='+',required=True)
    p.add_argument('--arms',nargs='+',required=True)
    p.add_argument('--workers',type=int,default=6)
    p.add_argument('--label',required=True)
    a=p.parse_args()
    root=confirm.ROOT
    manifest=json.loads((root/'confirmation-manifest.json').read_text())
    for name,expected in manifest['hashes'].items():
        assert confirm.campaign.sha(confirm.REPO/name)==expected,name
    command=Path(f'/proc/{a.scheduler_pid}/cmdline').read_bytes().split(b'\0')
    assert any(b'guard_balanced_20260921/scripts/confirm.py' in arg for arg in command)
    assert b'run' in command
    intended=[t for t in manifest['tasks'] if t['seed'] in a.seeds and t['arm'] in a.arms
              and t['study'] in ['ali30','ali50','allreduce_dp2']]
    owned=[]
    os.kill(a.scheduler_pid,signal.SIGSTOP)
    try:
        # SIGSTOP is asynchronous: confirm the process and its threads stopped.
        deadline=time.monotonic()+5
        while True:
            state=next(x for x in Path(f'/proc/{a.scheduler_pid}/status').read_text().splitlines() if x.startswith('State:'))
            if '\tT ' in state or '\tt ' in state:
                break
            assert time.monotonic()<deadline,'scheduler did not stop'
            time.sleep(.01)
        for task in intended:
            d=root/'runs'/task['key']
            if d.exists():
                continue  # Running, finished or previously reserved: never duplicate.
            d.mkdir()
            record=dict(task,status='delegated_pending',delegation=a.label)
            confirm.campaign.save(d/'result.json',record)
            owned.append(task)
        confirm.campaign.save(root/(a.label+'-delegation.json'),
                              dict(scheduler_pid=a.scheduler_pid,command=[x.decode() for x in command if x],
                                   reason='use spare workers for unstarted frozen cells',tasks=owned))
    finally:
        os.kill(a.scheduler_pid,signal.SIGCONT)
    # Use the exact campaign execution body, bypassing only its existence cache.
    source=inspect.getsource(confirm.campaign.run_one)
    cache="    if (d/'result.json').exists(): return json.loads((d/'result.json').read_text())\n"
    assert source.count(cache)==1
    source=source.replace(cache,'')
    namespace=dict(confirm.campaign.__dict__)
    exec(compile(source,__file__,'exec'),namespace)
    run_owned=namespace['run_one']
    print('Reserved',len(owned),'frozen tasks for',a.workers,'workers',flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(run_owned,t) for t in owned]):
            result=f.result()
            assert result['status']=='completed',result['key']
    print('All assisted tasks completed',flush=True)


if __name__=='__main__':
    main()
