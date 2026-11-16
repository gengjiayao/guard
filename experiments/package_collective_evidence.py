#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,zipfile,time

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'experiments/results'
DEST=ROOT/'annual2026_collective_delivery';DEST.mkdir(exist_ok=True)
CAMPAIGNS=['annual2026_dag_smoke','annual2026_dag_smoke_v2','annual2026_baseline_dev','annual2026_cc_dev1','annual2026_cc_duplex_dev','annual2026_cc_final_dev','annual2026_cc_check_dev','annual2026_cc_tail_dev','annual2026_final_heldout','annual2026_original_regression']
BASE='20ebfe2f53fe9c1645ddf0d3b72325ef96f95a7f'

def run(args):return subprocess.check_output(args,cwd=REPO)

def main():
    final=json.loads((ROOT/'annual2026_final_heldout/results.json').read_text());assert len(final)==200 and all(r['status']=='completed' for r in final)
    regression=json.loads((ROOT/'annual2026_original_regression/results.json').read_text());assert len(regression)==10 and all(r['status']=='completed' for r in regression)
    runtime=json.loads((ROOT/'annual2026_final_heldout/runtime_manifest.json').read_text())
    for name,record in runtime['files'].items():
        p=REPO/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256']
        assert p.stat().st_mtime_ns==record['mtime_ns']
    runtime['verified_after_all_runs_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    (DEST/'runtime-verification.json').write_text(json.dumps(runtime,indent=2)+'\n')
    (DEST/'commits.txt').write_bytes(run(['git','log','--reverse','--format=fuller',BASE+'..HEAD']))
    (DEST/'changes.patch').write_bytes(run(['git','diff','--binary',BASE,'HEAD']))
    bundle=DEST/'guard-collective-20261116.bundle'
    subprocess.run(['git','bundle','create',str(bundle),BASE+'..codex/guard-collective-20261116'],cwd=REPO,check=True)
    subprocess.run(['git','bundle','verify',str(bundle)],cwd=REPO,check=True)
    (DEST/'source-revision.txt').write_bytes(run(['git','rev-parse','HEAD']))
    counts={};raw=set();entries=[]
    for c in CAMPAIGNS:
        folder=ROOT/c;records=json.loads((folder/'results.json').read_text()) if (folder/'results.json').exists() else []
        counts[c]={'runs':len(records),'completed':sum(r['status']=='completed' for r in records),'failed':sum(r['status']=='failed' for r in records)}
        for r in records:
            if r.get('output_dir'):raw.add(Path(r['output_dir']))
        for p in folder.rglob('*'):
            if p.is_file():entries.append((p,'campaigns/'+c+'/'+str(p.relative_to(folder))))
    for folder in sorted(raw):
        for p in folder.rglob('*'):
            if p.is_file():entries.append((p,'raw/'+folder.name+'/'+str(p.relative_to(folder))))
    for p in (ROOT/'annual2026_final_analysis').rglob('*'):
        if p.is_file():entries.append((p,'analysis/'+str(p.relative_to(ROOT/'annual2026_final_analysis'))))
    for name in ['experiments/ANNUAL2026_VALIDATION.md','experiments/annual2026_collectives.py','experiments/analyze_collectives.py','experiments/plot_collectives.py','experiments/annual2026_final_variants.json','experiments/annual2026_regression_variants.json','experiments/tests/test_annual2026_collectives.py','experiments/tests/test_collective_input_validation.py','tests/guard_collective_control.cc','tests/flow_id_tag.cc','config/leaf_spine_16_100G_OS2.txt']:
        entries.append((REPO/name,'source/'+name))
    for p in (REPO/'experiments').glob('dev-variants-*.json'):entries.append((p,'source/experiments/'+p.name))
    (DEST/'campaign-index.json').write_text(json.dumps(counts,indent=2)+'\n')
    (DEST/'README.txt').write_text('''GUARD 2026 集合通信与拥塞控制实验归档

final_heldout 为冻结后的正式对照：10组负载配置、4个算法、5个种子，共200次。
original_regression 为另外10次原参数回归，仅用于检查汇聚优化；不列入报告主图。
其他目录为开发过程，包含不理想的参数与失败记录，不是正式对照结果。

analysis/ 中保存所有10组正式结果、配对降幅及置信区间、图表和核验统计。
campaigns/ 中保存输入、依赖图、配置计划、逐次运行记录和驱动日志。
raw/ 中保存原始输出；可按记录中的 output_dir 最后一级目录名定位。
记录中的绝对路径来自 node67，离线核验时使用 analyze_collectives.py 的 --raw-root 参数。
GUARD_关闭主动释放 没有作为本次对照算法。

运行说明见 source/experiments/ANNUAL2026_VALIDATION.md。
该方案在 ns-3 中实现，集合通信依赖真实完成事件；不包含 GPU 计算时间或物理原型实测。
优化参数由 annual2026_final_variants.json 统一启用，所有场景使用同一配置。

changes.patch 和 Git bundle 保存提交历史。bundle 为增量包，依赖基线：
20ebfe2f53fe9c1645ddf0d3b72325ef96f95a7f
可在拥有该基线的仓库中执行 git fetch <bundle路径> codex/guard-collective-20261116。
不要将增量 bundle 当作完整 ns-3 源码仓库。

MANIFEST.sha256 列出归档内文件的哈希。
''')
    for p in DEST.iterdir():
        if p.is_file() and p.suffix!='.zip':entries.append((p,p.name))
    archive=DEST/'GUARD_2026_collective_validation.zip';manifest=[]
    assert len({name for _,name in entries})==len(entries)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name in entries:
            data=p.read_bytes();z.writestr(name,data);manifest.append(hashlib.sha256(data).hexdigest()+'  '+name)
        z.writestr('MANIFEST.sha256','\n'.join(sorted(manifest))+'\n')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(entries)+1,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'campaigns':counts},indent=2))

if __name__=='__main__':main()
