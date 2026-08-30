#!/usr/bin/env python3
"""网站数据自动更新 (2026-08-31 优化): 一条命令完成 拉数据→入库→改网页→推送

用法: python3 update_site.py [--no-push]
  无新开奖时自动退出; 新开奖则: 两份CSV入库 → index.html DRAWS补条 → git提交推送

数据源: https://macaumarksix.com/api/macaujc2.com (macaujc.com)
"""
import json, subprocess, sys, re, urllib.request

API = 'https://macaumarksix.com/api/macaujc2.com'
CSV1 = '/Users/xiejinyu/macau_mark6_data.csv'
CSV2 = '/Users/xiejinyu/macau-mark6/macau_mark6_data.csv'
IDX = '/Users/xiejinyu/macau-mark6/index.html'
REPO = '/Users/xiejinyu/macau-mark6'

def fetch():
    try:
        req = urllib.request.Request(API, headers={'User-Agent': 'Mozilla/5.0'})
        r = json.load(urllib.request.urlopen(req, timeout=30))
        return r[0] if isinstance(r, list) else r
    except Exception as e:
        print(f'⚠️  接口失败: {e}')
        sys.exit(1)

def main():
    no_push = '--no-push' in sys.argv
    r = fetch()
    exp = r['expect']
    code = [int(x) for x in r['openCode'].split(',')]
    if not (len(code) == 7 and all(1 <= c <= 49 for c in code)):
        print('⚠️  接口数据异常, 中止'); sys.exit(1)
    sp = code[6]
    date = r.get('openTime', '')[:10]
    wave = r['wave'].split(',') if isinstance(r['wave'], str) else r['wave']
    zod = r['zodiac'].split(',') if isinstance(r['zodiac'], str) else r['zodiac']

    # 1. 检查CSV是否已有
    lines1 = open(CSV1, encoding='utf-8-sig').read().rstrip('\n').split('\n')
    if exp in lines1[-1]:
        print(f'✅ 已是最新: {exp} 特码{sp:02d} (CSV与网站无需更新)')
        return
    # 2. 两份CSV入库
    row = ','.join([exp, date] + [f'{x:02d}' for x in code[:6]] + [f'{sp:02d}'] + wave + zod)
    for p in (CSV1, CSV2):
        L = open(p, encoding='utf-8-sig').read().rstrip('\n').split('\n')
        if exp in L[-1]:
            continue
        L.append(row)
        open(p, 'w', encoding='utf-8-sig').write('\n'.join(L) + '\n')
    print(f'✅ CSV入库: {exp} 特码{sp:02d}')

    # 3. index.html DRAWS 补条
    s = open(IDX, encoding='utf-8').read()
    prev = re.findall(r'\{"i": "(\d{7})", "d": "([^"]+)", "f": \[(\d+, \d+, \d+, \d+, \d+, \d+)\], "s": (\d+)\}\]', s)
    if prev and prev[-1][0] == exp:
        print('✅ index.html 已含该期')
    else:
        anchor = re.search(r'(\{"i": "%s".*?\}\];)' % (str(int(exp) - 1)), s)
        if not anchor:
            print('⚠️  index.html 未找到上一期锚点, 需手动补'); sys.exit(1)
        old = anchor.group(1)
        new = old[:-2] + ', {"i": "%s", "d": "%s", "f": [%s], "s": %d}];' % (
            exp, date, ', '.join(str(x) for x in code[:6]), sp)
        s = s.replace(old, new)
        open(IDX, 'w', encoding='utf-8').write(s)
        # 校验JSON
        i = s.find('var DRAWS = ['); j = s.find('];', i)
        arr = json.loads(s[i + len('var DRAWS = '):j + 1])
        print(f'✅ index.html 补入 {exp} (共{len(arr)}期, 末期{arr[-1]["i"]} 特{arr[-1]["s"]:02d})')

    # 4. git 提交推送
    if no_push:
        print('(跳过推送)')
        return
    subprocess.run(['git', '-C', REPO, 'add', 'index.html', 'macau_mark6_data.csv'], check=True)
    msg = f'{exp[-3:]}期开奖入库: 特码{sp:02d}, 首页数据+CSV同步\n\nCo-Authored-By: Claude <noreply@anthropic.com>'
    subprocess.run(['git', '-C', REPO, 'commit', '-q', '-m', msg], check=True)
    subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', 'main'], check=True)
    print(f'✅ 已推送: {exp} 特码{sp:02d}')

if __name__ == '__main__':
    main()
