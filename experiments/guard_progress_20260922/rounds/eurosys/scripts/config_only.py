"""Run the unmodified driver until its simulator invocation; retain its config."""
import os
import runpy
import subprocess
import sys
from pathlib import Path

repo = Path('/home/gengjiayao/ict/guard')
real_run = subprocess.run
def intercept(argv, *args, **kwargs):
    if isinstance(argv, list) and argv[0] == './waf':
        print('CONFIG_READY=' + argv[2].split(' ', 1)[1], flush=True)
        raise SystemExit(0)
    return real_run(argv, *args, **kwargs)
subprocess.run = intercept
os.chdir(repo)
sys.path.insert(0, str(repo))
sys.argv[0] = str(repo / 'run.py')
runpy.run_path(str(repo / 'run.py'), run_name='__main__')
