# -*- coding: utf-8 -*-
# 子晨哥哥实证回测: 只统计"条文期=发帖当期且发帖<该期21:32开奖"的数字池类条文
import json,re,datetime
from datetime import timezone,timedelta

rows=[json.loads(l) for l in open('zichen_dump.jsonl',encoding='utf-8') if l.strip()]
TZ=timezone(timedelta(hours=8))
def open_epoch(datestr):
    return datetime.datetime.strptime(datestr,'%Y-%m-%d').replace(hour=21,minute=32,tzinfo=TZ).timestamp()
def bj(ts): return datetime.datetime.fromtimestamp(ts+8*3600).strftime('%m-%d %H:%M')

iss={}
for line in open('/Users/xiejinyu/macau-mark6/macau_mark6_data.csv',encoding='utf-8'):
    f=line.strip().split(',')
    if len(f)>=9:
        try: iss[int(f[0][-3:])]={'code':int(f[8]),'dt':f[1]}
        except: pass
KW=['经典24码','精选24码','金牌24码','银牌24码','铜牌24码','爆特24码','金牌⑧码','银牌⑧码','铜牌⑧码','24码','爆特','⑧码','绝杀','码']
def kind_of(seg):
    head=seg[:80]
    for k in KW:
        if k in head: return k
    return None
SEG=re.compile(r'(?=(?:24[0-9]|25[0-9])期)')
NUMS=re.compile(r'(?<!\d)((?:\d{2}){6,})(?!\d)')
recs=[]; dup=set()
for r in rows:
    c=r.get('content','').replace('<br>','\n').replace('<BR>','\n')
    c=re.sub(r'<[^>]+>','',c)
    c=re.sub(r'\s+','',c)
    if not c: continue
    for seg in SEG.split(c):
        m=re.match(r'(\d{3})期',seg)
        if not m: continue
        n=int(m.group(1))
        if n not in iss: continue
        seg=seg[m.end():]
        kind=kind_of(seg)
        if kind is None: continue
        is_kill='绝杀' in kind
        seg_plain=seg.replace('.','')
        digs=[]
        for mm in NUMS.finditer(seg_plain):
            s=mm.group(1)
            if len(s)>=12: digs.append(s)
        if not digs: continue
        # 发帖时刻 < 该期开奖 才算前瞻
        if r['time']>=open_epoch(iss[n]['dt']): continue
        preds=digs
        for ds in preds:
            pool=set(int(ds[i:i+2]) for i in range(0,len(ds),2))
            if len(pool)<6: continue
            key=(n,kind,ds)
            if key in dup: continue
            dup.add(key)
            code=iss[n]['code']
            hit=(code not in pool) if is_kill else (code in pool)
            recs.append((n,bj(r['time']),kind,len(pool),hit))
print('前瞻码池条文(去重)总条数:',len(recs))
# 分类统计
from collections import defaultdict
by=defaultdict(lambda:[0,0])
per=defaultdict(lambda:[0,0])
for n,t,k,ps,hit in recs:
    by[k][0]+=1; by[k][1]+=hit
    per[n][0]+=1; per[n][1]+=hit
print('\n按类(条数/中/率 vs 基线):')
for k,(c,h) in sorted(by.items(),key=lambda x:-x[1][0]):
    base='?'
    if '24码' in k and '⑧' not in k: base='49.0%'
    elif '⑧' in k or k=='爆特': base='16.3%'
    elif '绝杀' in k: base='79.6%'
    print(f'{k}: {h}/{c} = {h/c*100:.1f}%  (基线 {base})')
tot=sum(v[0] for v in by.values()); th=sum(v[1] for v in by.values())
print(f'\n全部合计: {th}/{tot} = {th/tot*100:.1f}%')
print('\n按开奖期(当期有>=1条条文):')
for n in sorted(per):
    c,h=per[n]
    print(f'{n}期: 中{h}/{c}', '  全对冲保底✓' if h>=1 and c>=2 else '')
allc=sum(1 for n in per if per[n][1]>=1); alln=len(per)
print(f'\n有发条文的期数 {alln}, 其中至少中1条的期数 {allc} = {allc/alln*100:.0f}%(双发对冲保底率)')
