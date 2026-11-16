#!/usr/bin/env python3
"""Package both complete validations plus all development-result registries."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    previous=repo.parent/'guard-collective-20261116'
    final=repo/'experiments/results/annual2026_tail_final_audit'
    data=json.loads((final/'report-analysis.json').read_text())
    assert data['runs']==280
    effect=next(x for x in data['effects'] if x['case']=='AliStorage2019-L80' and x['group']=='all' and x['metric']=='p99_fct_us' and x['baseline']=='homa')
    assert effect['mean']>10 and effect['seeds']==list(range(4101,4111))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    bundle=final/'guard-commits.bundle'
    subprocess.run(['git','bundle','create',str(bundle),'20ebfe2f53fe9c1645ddf0d3b72325ef96f95a7f..HEAD'],cwd=repo,check=True)
    verified=subprocess.check_output(['git','bundle','verify',str(bundle)],cwd=repo,stderr=subprocess.STDOUT,text=True)
    source=final/'guard-source.tar.gz'
    with source.open('wb') as out:
        archive=subprocess.Popen(['git','archive','--format=tar','HEAD'],cwd=repo,stdout=subprocess.PIPE)
        compression=subprocess.run(['gzip','-9'],stdin=archive.stdout,stdout=out,check=True)
        archive.stdout.close();assert archive.wait()==0
    files={};registry=[]
    def add(path,name):
        path=Path(path)
        if path.is_file():
            assert name not in files,(name,path)
            files[name]=path
    for label,base in [('frozen_v1',previous),('frozen_v2',repo)]:
        for name in ['primary','sensitivity','regression']:
            root=base/'experiments/results'/('annual2026_tail_final_'+name)
            rs=json.loads((root/'results.json').read_text())
            assert len(rs)==(200 if name=='regression' else 40) and all(r['status']=='completed' for r in rs)
            for f in root.rglob('*'):
                if f.is_file():add(f,label+'/campaigns/'+root.name+'/'+str(f.relative_to(root)))
            for r in rs:
                out=Path(r['output_dir'])
                for fname,digest in r['output_hashes'].items():
                    f=out/fname;assert hashlib.sha256(f.read_bytes()).hexdigest()==digest
                    add(f,label+'/raw/'+out.name+'/'+fname)
        audit=base/'experiments/results/annual2026_tail_final_audit'
        for f in audit.glob('*'):
            if f.suffix in ['.json','.csv','.png','.pdf']:add(f,label+'/analysis/'+f.name)
        for fname in ['annual2026_tail_final_freeze.json','annual2026_tail_final_variants.json','annual2026_tail_protocol.md']:
            add(base/'experiments'/fname,label+'/protocol/'+fname)
        for campaign in sorted((base/'experiments/results').glob('annual2026_*')):
            if campaign.name.startswith('annual2026_tail_final_') or not (campaign/'results.json').exists():continue
            rows=json.loads((campaign/'results.json').read_text())
            if not isinstance(rows,list):continue
            stem='development/'+base.name+'/'+campaign.name
            for name in ['plan.json','results.json']:
                add(campaign/name,stem+'/'+name)
            for f in campaign.glob('runs/*/driver.log'):add(f,stem+'/runs/'+f.parent.name+'/'+f.name)
            for r in rows:
                registry.append({'repository':str(base),'campaign':campaign.name,'key':r.get('key'),'case':r.get('case'),'seed':r.get('seed'),'arm':r.get('arm'),'status':r.get('status'),'error':r.get('error'),'git':r.get('git'),'raw_output_on_node67':r.get('output_dir'),'input_sha256':r.get('input_sha256'),'tails':r.get('tails'),'metrics':r.get('metrics')})
    add(bundle,'code/guard-commits.bundle');add(source,'code/guard-source.tar.gz')
    logs=subprocess.check_output(['git','log','--format=%h %ad %s','--date=iso-strict','20ebfe2f53fe9c1645ddf0d3b72325ef96f95a7f..HEAD'],cwd=repo,text=True)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    readme=f'''GUARD 整体 P99 优化证据包

最终代码提交：{revision}
控制实现提交：4c93075；配置冻结提交：07a619d。
最终独立验证：AliStorage2019，80% 主机注入负载，种子 4101—4110。
相对 Homa 的整体 P99 配对降幅均值：{effect['mean']:.6f}%。
种子间 95% t 区间：[{effect['ci95_low']:.6f}%, {effect['ci95_high']:.6f}%]。
采用全部消息大小；按启动时间排除前 5 ms；所有输入流均完成。
流量按公开经验 CDF 生成泊松到达，不是生产逐包轨迹回放。

frozen_v2 保存最终 280 次验证的全部输入、运行记录、输出文件及审计数据。
frozen_v1 保存前版本的完整 280 次验证，包括 All-to-Allv 和并发任务的退化。
development 保存所有可识别开发矩阵的配置、全部指标、失败记录及驱动日志。
开发尝试的原始输出仍完整保留在 node67；每条 registry 记录给出了路径。
本压缩包不重复收录全部开发尝试的原始逐流输出；两轮正式验证原始数据均在包内。
科学图表保留 PNG/PDF；未包含 Word 排版检查的中间页图。

最终负载敏感性为 50%/70%，各 5 个独立种子；基础及集合通信 10 个场景各 5 个。
GUARD/HPCC/DCQCN/Homa 共享物理资源、输入和路由。Homa 保留原生实现与输入导出的优先级配置。
1 MiB All-to-All 仍未领先，不能将高负载 P99 收益推广到所有消息大小或通信模式。
数据仅来自 ns-3 网络仿真，不包含 GPU 运算或物理原型测试。

复现与审计
1. 解压 code/guard-source.tar.gz，源码包含全部运行器、CDF 和审计脚本。
2. ns-3 构建使用 Python 2.7：python2 waf configure --build-profile=optimized --disable-python --disable-tests；python2 waf build -j 6。
   实验驱动使用 Python 3。各 campaign 的 plan.json、run manifest 和 driver.log 保存精确配置与命令。
3. 正式运行期间不要重新构建；运行器核对可执行文件与动态库哈希，使用 --no_build 1。
4. 离线审计（从解压的源码目录运行）：
   python3 experiments/annual2026_final_audit.py --campaign-base /绝对路径/frozen_v2/campaigns --freeze /绝对路径/frozen_v2/protocol/annual2026_tail_final_freeze.json --raw-root /绝对路径/frozen_v2/raw --out /绝对路径/audit-recomputed
   将 frozen_v2 改为 frozen_v1 可核对前一版本。
5. Git bundle 包含基线 20ebfe2 至最终提交的增量历史；原始 guard 仓库已含前置提交。
   git -C /home/gengjiayao/ict/guard bundle verify /绝对路径/guard-commits.bundle
   完整源码快照可独立阅读和构建，不要求先导入 bundle。

公开数据来源
https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/AliStorage2019.txt
https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/WebSearch_distribution.txt

SHA256SUMS.json 给出包内数据文件校验值；Git 历史和所有负面开发记录均保留。
'''
    manifest=[];temp=a.out.with_suffix('.partial')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for name,path in sorted(files.items()):
            content=path.read_bytes();manifest.append({'path':name,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
            z.writestr(name,content,compress_type=zipfile.ZIP_STORED if name.endswith(('.gz','.bundle')) else zipfile.ZIP_DEFLATED)
        z.writestr('README.txt',readme);z.writestr('code/git-log.txt',logs);z.writestr('code/bundle-verification.txt',verified)
        z.writestr('development/registry.json',json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
        z.writestr('SHA256SUMS.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None
    temp.replace(a.out)
    digest=hashlib.sha256(a.out.read_bytes()).hexdigest()
    print(json.dumps({'archive':str(a.out),'bytes':a.out.stat().st_size,'sha256':digest,'files':len(files),'development_runs':len(registry)},ensure_ascii=False))

if __name__=='__main__':main()
