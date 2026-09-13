# -*- coding: utf-8 -*-
# 子晨哥哥 六肖 前瞻实证回测
import json,re,datetime
from datetime import timezone,timedelta
rows=[json.loads(l) for l in open('zichen_dump.jsonl',encoding='utf-8') if l.strip()]
TZ=timezone(timedelta(hours=8))
ANIM='鼠牛虎兔龙蛇马羊猴鸡狗猪'
def open_epoch(d): return datetime.datetime.strptime(d,'%Y-%m-%d').replace(hour=21,minute=32,tzinfo=TZ).timestamp()
def bj(ts): return datetime.datetime.fromtimestamp(ts+8*3600).strftime('%m-%d %H:%M')
iss={}
for line in open('/Users/xiejinyu/macau-mark6/macau_mark6_data.csv',encoding='utf-8'):
    f=line.strip().split(',')
    if len(f)>=23 and f[-1] in ANIM:
        try: iss[int(f[0][-3:])]={'code':int(f[8]),'zod':f[-1],'dt':f[1]}
        except: pass
SEG=re.compile(r'(?=(?:2[2-5][0-9])期)')
BR=re.compile(r'[【】\[\]＜<>《》]')
recs=[]; seen=set()
for r in rows:
    if '六肖' not in r.get('content',''): continue
    c=r.get('content','').replace('<br>','\n').replace('<BR>','\n')
    c=re.sub(r'<[^>]+>','',c); c=re.sub(r'\s+','',c)
    if '香港' in c[:6]: continue
    for seg in SEG.split(c):
        m=re.match(r'(\d{3})期',seg)
        if not m: continue
        n=int(m.group(1))
        if n not in iss: continue
        body=seg[m.end():]
        if '六肖' not in body: continue
        # 取该段所有【】组,找生肖词(>=5个单字肖)
        got=None
        for grp in re.findall(r'[【【\[]([^】】\]]+)[】】\]]',body):
            g=re.sub(r'[.、，,;；:：\-]','',grp)
            if len(g)>=5 and all(ch in ANIM for ch in g):
                got=''.join(ch for ch in g if ch in ANIM); break
        if not got: continue
        key=(n,got)
        if key in seen: continue
        seen.add(key)
        if r['time']>=open_epoch(iss[n]['dt']): continue  # 前瞻过滤
        recs.append((n,bj(r['time']),got,iss[n]['zod'],iss[n]['zod'] in got))
print(f'前瞻六肖条文(去重): {len(recs)} 条')
print(f'命中: {sum(1 for x in recs if x[4])} | 总体: {sum(1 for x in recs if x[4])}/{len(recs)} = {sum(1 for x in recs if x[4])/len(recs)*100:.0f}%  (基线 50%)')
from collections import defaultdict
per=defaultdict(list)
for n,t,g,z,h in recs: per[n].append(h)
print('\n按期:')
for n in sorted(per):
    hs=per[n]
    print(f'{n}期 中{sum(hs)}/{len(hs)}', '  ←全错' if not any(hs) else '')
for n,t,g,z,h in recs:
    print(f'  {n}期 {t} 【{g}】 开{z}:', '中' if h else '错')
