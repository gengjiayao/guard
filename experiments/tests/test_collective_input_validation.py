#!/usr/bin/env python3
"""Exercise the actual simulator's dependency parser; never rewrite a run."""
from pathlib import Path
import argparse,json,os,subprocess,tempfile

REPO=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();source=args.config.resolve();original=source.read_text()
    original_parent=source.parent
    tests={
        'cycle':('3\n0 1 1\n1 1 0\n2 0\n','cycle in collective dependencies'),
        'self':('3\n0 1 0\n1 0\n2 0\n','invalid dependency edge'),
        'out_of_range':('3\n0 1 3\n1 0\n2 0\n','invalid dependency edge'),
        'duplicate':('3\n0 2 1 1\n1 0\n2 0\n','invalid dependency edge'),
        'extra':('3\n0 0\n1 0\n2 0\n3 0\n','extra dependency records')}
    result=[]
    with tempfile.TemporaryDirectory(prefix='guard-dag-reject-') as tmp:
        root=Path(tmp)
        flow=root/'flows.txt';flow.write_text('3\n0 8 3 1000 2.001\n8 9 3 1000 2.001\n9 10 3 1000 2.001\n')
        for name,(data,expected) in tests.items():
            out=root/name;out.mkdir();dep=out/'input.deps';dep.write_text(data)
            config=original.replace(str(original_parent),str(out)).replace(str(original_parent.relative_to(REPO)),str(out))
            rows=[]
            for line in config.splitlines():
                if line.startswith('FLOW_FILE '):line='FLOW_FILE '+str(flow)
                if line.startswith('FLOW_DEPENDENCY_FILE '):line='FLOW_DEPENDENCY_FILE '+str(dep)
                rows.append(line)
            target=out/'config.txt';target.write_text('\n'.join(rows)+'\n')
            env={**os.environ,'LD_LIBRARY_PATH':str(REPO/'build')}
            proc=subprocess.run([str(REPO/'build/scratch/network-load-balance'),str(target)],cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
            assert proc.returncode!=0 and expected in proc.stdout,(name,proc.returncode,proc.stdout[-2000:])
            result.append({'case':name,'status':'PASS','expected_error':expected})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
