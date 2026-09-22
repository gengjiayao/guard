"""Watch running shards, use spare workers, then validate complete evidence."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'guard_optimization_20260921'


def records(root):
    values=[json.loads(p.read_text()) for p in (root/'holdout/runs').glob('*/result.json')]
    return sum(x['status']=='completed' for x in values),[
        x['key'] for x in values if x['status'] not in ['completed','delegated_pending']]


def main():
    children={}
    assisted=set()
    finished=set()
    errors=[]
    def launch(name,command):
        log=(ROOT/(name+'.log')).open('w')
        children[name]=(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT),log)
    while True:
        for name,(process,log) in list(children.items()):
            code=process.poll()
            if code is not None:
                log.close()
                finished.add(name)
                del children[name]
                if code:
                    errors.append(dict(job=name,returncode=code,log=str(ROOT/(name+'.log'))))
        new,badnew=records(ROOT)
        old,badold=records(OLD)
        pc=subprocess.run(['pgrep','-x','network-load-ba'],text=True,stdout=subprocess.PIPE)
        active=len(pc.stdout.splitlines())
        available=max(0,23-active)
        # Later frozen seeds can be reserved safely while the original scheduler
        # is briefly stopped; all existing run directories are excluded.
        if available>=4:
            for seed in [505,504,503]:
                name=f'assist-b-{seed}'
                if name in assisted:
                    continue
                pattern='^python3 work/guard_balanced_20260921/scripts/confirm.py run --studies ali30 ali50 allreduce_dp2 --arms hpcc dcqcn timely --workers 6$'
                pid=subprocess.run(['pgrep','-f',pattern],text=True,stdout=subprocess.PIPE)
                ids=pid.stdout.splitlines()
                if len(ids)!=1:
                    break
                assisted.add(name)
                launch(name,[sys.executable,str(ROOT/'scripts/assist_queue.py'),
                             '--scheduler-pid',ids[0],'--seeds',str(seed),
                             '--arms','hpcc','dcqcn','timely',
                             '--workers',str(min(6,available)),'--label',name])
                break
        if old==454 and not badold and 'close-prior' not in children and 'close-prior' not in finished:
            launch('close-prior',[sys.executable,str(ROOT/'scripts/close_previous.py')])
        if new==494 and not badnew and 'close-current' not in children and 'close-current' not in finished:
            launch('close-current',[sys.executable,str(ROOT/'scripts/close_current.py')])
        state=dict(new_complete=new,new_expected=494,prior_complete=old,prior_expected=454,
                   active_simulators=active,jobs=list(children),finished=sorted(finished),
                   failed_records=badnew+badold,errors=errors,
                   utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        (ROOT/'live-status.json').write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps(state),flush=True)
        if errors or badnew or badold:
            print('ATTENTION: inspect recorded error; existing simulators continue.',flush=True)
            return 1
        if {'close-prior','close-current'}<=finished and not children:
            print('ALL MATRICES AND VALIDATION COMPLETE',flush=True)
            return 0
        time.sleep(45)


if __name__=='__main__':
    raise SystemExit(main())
