#!/usr/bin/env python3
"""Colliding concurrent drivers must preserve prior results and stay isolated."""
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run import reserve_run_directory

with tempfile.TemporaryDirectory() as temp:
    parent=Path(temp)
    existing=parent/'0';existing.mkdir();(existing/'marker').write_text('keep')
    with ThreadPoolExecutor(max_workers=16) as pool:
        results=list(pool.map(lambda _: reserve_run_directory(temp,'0'),range(200)))
    assert len({r[0] for r in results})==200
    assert len({r[1] for r in results})==200
    assert all(Path(path).is_dir() and Path(path).name==stem for stem,path in results)
    assert (existing/'marker').read_text()=='keep'
    bad=parent/'file';bad.write_text('keep')
    try:
        reserve_run_directory(str(bad),'0')
        raise AssertionError('unrelated filesystem error was swallowed')
    except NotADirectoryError:
        pass
print('PASS 200 colliding directory reservations preserve existing outputs')
