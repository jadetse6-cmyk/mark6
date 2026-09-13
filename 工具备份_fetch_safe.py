# -*- coding: utf-8 -*-
# 安全增量: 主列表翻页,每页校验最新帖时间为近24h内(防滞后后端灌老帖),遇库中已有id即停
import subprocess,json,time,sys,datetime
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
BASE='https://com1.4e24pfudeip-8.com/com/record.html'
have=set()
for l in open('comments.jsonl',encoding='utf-8'):
    try: have.add(json.loads(l).get('id'))
    except: pass
print(f'库已知 {len(have)} 条', flush=True)
BJ=datetime.timezone(datetime.timedelta(hours=8))
def bj(t): return datetime.datetime.fromtimestamp(t,BJ).strftime('%m-%d %H:%M')
# 护栏: 页首帖早于此时刻 → 后端滞后或已翻到历史, 中止。目标=北京 2026-09-11 00:00
# 显式时区, 不受本机 CEST 影响(旧写法 timestamp()-8*3600 意图不明且会随机器时区漂移)
cut=datetime.datetime(2026,9,11,0,0,tzinfo=BJ).timestamp()
def fetch(p):
    args=['curl','-sk','--compressed','--max-time','20','-A',UA,'-H','Referer: https://www.3355y.com/',
          '--data-urlencode','callback=jQueryCb','--data-urlencode','orderby=0','--data-urlencode','id=67',
          '--data-urlencode',f'page={p}','--data-urlencode','key_word=','--data-urlencode','key_msg_word=',
          '--data-urlencode','classid=0','--data-urlencode','id2=',BASE]
    r=subprocess.run(args,capture_output=True,text=True)
    s=r.stdout
    if '(' not in s: return None
    try: return json.loads(s[s.index('(')+1:s.rindex(')')])
    except: return None
new_total=0; blank=0; p=1
while p<=400:
    j=fetch(p)
    if not j:
        blank+=1
        if blank>=5: print('5次抓取失败,停'); break
        time.sleep(1); continue
    data=j.get('data') or []
    if not data: print(f'page{p} 空, 到底'); break
    top=data[0]
    if top.get('time',0) < cut:   # 护栏: 页首帖早于249开奖后 → 后端滞后/已到历史
        print(f'page{p} 页首@{bj(top.get("time",0))} 过旧,中止(可能滞后后端或已翻完)')
        break
    fresh=[d for d in data if d.get('id') not in have]
    if not fresh:
        print(f'page{p} 全重复, 收尾停'); break
    with open('comments.jsonl','a',encoding='utf-8') as f:
        for d in fresh:
            f.write(json.dumps(d,ensure_ascii=False)+'\n')
            have.add(d.get('id'))
    new_total+=len(fresh)
    print(f'page{p} 新增{len(fresh)} 累计{new_total} 页首@{bj(top.get("time",0))}', flush=True)
    p+=1
    time.sleep(0.25)
print(f'完成: 新增 {new_total} 条')
