# -*- coding: utf-8 -*-
# key_word 搜索补全: 主列表可能隐藏/降权料主帖, 只有搜索接口可见。
#
# 2026-09-12 改: 旧版"第1页无精确用户名匹配即停"会静默失效 —— 搜索按时间倒序,
# 主列表约每分钟30帖, 料主发言只要超过1分钟就被挤到第2页之后, 旧版直接判"无新增"。
# 现改为按【时间窗口】扫: 一直翻到某页最新帖早于 --since 为止, 且只收 time>=since 的帖,
# 这样既不会漏掉被挤到深处的料主帖, 也不会把远古历史帖灌进库改变历史条文。
import subprocess, json, time, sys, datetime

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
BASE = 'https://com1.4e24pfudeip-8.com/com/record.html'
BJ = datetime.timezone(datetime.timedelta(hours=8))


def bj(t):
    return datetime.datetime.fromtimestamp(t, BJ).strftime('%m-%d %H:%M')


name = sys.argv[1]
# --since YYYY-MM-DD[THH:MM] 北京时; 默认 2026-09-11 00:00
since_s = sys.argv[2] if len(sys.argv) > 2 else '2026-09-11'
try:
    d = datetime.datetime.fromisoformat(since_s)
except ValueError:
    sys.exit(f'❌ --since 格式不对: {since_s}')
if d.tzinfo is None:
    d = d.replace(tzinfo=BJ)
SINCE = d.timestamp()
MAXP = 60

have = set()
for l in open('comments.jsonl', encoding='utf-8'):
    try:
        have.add(json.loads(l).get('id'))
    except Exception:
        pass
print(f'[{name}] 库已知 {len(have)} 条; 窗口 >= {bj(SINCE)} 北京', flush=True)


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


new_total = 0
blank = 0
seen_pages = 0     # 有料主帖出现过的页数
p = 1
while p <= MAXP:
    j = fetch(p)
    if not j:
        blank += 1
        if blank >= 5:
            print(f'[{name}] 5次抓取失败, 停', flush=True)
            break
        time.sleep(1)
        continue
    data = j.get('data') or []
    if not data:
        print(f'[{name}] page{p} 空, 到底', flush=True)
        break
    top_t = data[0].get('time', 0)
    if top_t < SINCE:
        print(f'[{name}] page{p} 页首@{bj(top_t)} 已早于窗口, 收尾停', flush=True)
        break
    got = [d for d in data if d.get('username') == name]
    if got:
        seen_pages += 1
    fresh = [d for d in got if d.get('id') not in have and d.get('time', 0) >= SINCE]
    if fresh:
        with open('comments.jsonl', 'a', encoding='utf-8') as f:
            for d in fresh:
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
                have.add(d.get('id'))
        new_total += len(fresh)
    if got:
        print(f'[{name}] page{p} 命中{len(got)} 新增{len(fresh)} 累计{new_total} 页首@{bj(top_t)}', flush=True)
    p += 1
    time.sleep(0.3)

print(f'[{name}] 完成: 新增 {new_total} 条 (扫了 {p-1} 页, 其中 {seen_pages} 页有该料主)', flush=True)
