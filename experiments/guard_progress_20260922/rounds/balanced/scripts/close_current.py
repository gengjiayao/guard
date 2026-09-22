"""Finalize the complete new cohort without changing the frozen experiment."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
commands=[('confirm.py','analyze'),('report.py',),('audit_figures.py',),
          ('plot.py','--final'),('archive.py',),('final_gate.py',),('make_report.py',)]
for command in commands:
    subprocess.run([sys.executable,str(ROOT/'scripts'/command[0]),*command[1:]],check=True)
