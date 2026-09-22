"""Snapshot completed raw outputs for the self-contained evidence repository."""
import gzip,json,tarfile
from pathlib import Path
from campaign import ROOT,sha,save
out=ROOT/'raw';out.mkdir(exist_ok=True)
index={}
for path in sorted((ROOT/'runs').glob('*/result.json')):
 r=json.loads(path.read_text())
 if r['status']!='completed':continue
 target=out/(r['key']+'.tar.gz')
 if not target.exists():
  tmp=target.with_suffix('.tmp')
  with tmp.open('wb') as fh,gzip.GzipFile(filename='',mode='wb',fileobj=fh,mtime=0,compresslevel=6) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
   for p in sorted(Path(r['output_dir']).iterdir()):
    if not p.is_file():continue
    info=tar.gettarinfo(str(p),arcname=p.name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
    with p.open('rb') as src:tar.addfile(info,src)
  tmp.replace(target)
 index[r['key']]={'path':str(target.relative_to(ROOT)),'sha256':sha(target),'config_sha256':r['config_sha256'],'flow_sha256':r['flow_sha256']}
save(ROOT/'raw_index.json',index)
print('Archived',len(index),'completed runs')
