# -*- coding: utf-8 -*-
# 针对性编辑检测: 用 key_word 搜索拉某料主最近 N 页, 与库内同 id 内容比对。
# 主列表扫描( check_edits.py )要翻几百页才够到料主发帖时段; 这个几页就够。
import subprocess, json, time, sys

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
BASE = 'https://com1.4e24pfudeip-8.com/com/record.html'
name = sys.argv[1]
PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 12


def fetch(p):
    args = ['curl', '-sk', '--compressed', '--max-time', '20', '-A', UA,
            '-H', 'Referer: https://www.3355y.com/',
            '--data-urlencode', 'callback=jQueryCb', '--data-urlencode', 'orderby=0',
            '--data-urlencode', 'id=67', '--data-urlencode', f'page={p}',
            '--data-urlencode', f'key_word={name}', '--data-urlencode', 'key_msg_word=',
            '--data-urlencode', 'classid=0', '--data-urlencode', 'id2=', BASE]
    r = subprocess.run(args, capture_output=True, text=True)
    s = r.stdout
    if '(' not in s:
        return None
    try:
        return json.loads(s[s.index('(') + 1:s.rindex(')')])
    except Exception:
        return None


def body(d):
    return (d.get('content') or '') + '\x00' + (d.get('msg') or '')


fresh = {}
for p in range(1, PAGES + 1):
    j = fetch(p)
    if not j:
        print(f'page{p} 抓取失败')
        continue
    data = j.get('data') or []
    if not data:
        break
    got = [d for d in data if d.get('username') == name]
    for d in got:
        fresh[d.get('id')] = d
    if got:
        t = max(d.get('time', 0) for d in got)
        print(f'page{p} {len(got)}条({name}) 最新@{time.strftime("%m-%d %H:%M", time.localtime(t + 8 * 3600))}', flush=True)
    time.sleep(0.25)

print(f'\n[{name}] 抓到 {len(fresh)} 条最新帖, 与库内同 id 比对...', flush=True)
changed, same, notinlib = [], 0, 0
for ln in open('comments.jsonl', encoding='utf-8'):
    try:
        c = json.loads(ln)
    except Exception:
        continue
    i = c.get('id')
    if i in fresh:
        if body(c) != body(fresh[i]):
            changed.append((c, fresh[i]))
        else:
            same += 1

print(f'[{name}] 同 id 内容一致: {same}')
print(f'[{name}] 同 id 内容已变(被编辑): {len(changed)}')
for old, new in changed:
    ob = body(old).replace('\x00', ' | ')
    nb = body(new).replace('\x00', ' | ')
    print(f"  --- id={old.get('id')} 期={old.get('expect')}")
    print(f"     旧: {ob[:160]}")
    print(f"     新: {nb[:160]}")
