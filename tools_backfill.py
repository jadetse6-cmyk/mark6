#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回填核对: 抽出某一期在全集里的所有自标行, 与真实开奖比对。

用法: python3 tools_backfill.py [期号]      # 默认最新一期(CSV末行)

只做"标注 vs 真值"的一致性核对, **不做命中判定** —— 命中要看系统语义
(绝杀/汉奸=投其余、羊羊的半波单双与阴阳肖定义与标准相反), 交由人工判读。
红线路标 [[mark6-source-fraud-test]]: 真结果必须带肖字; 占位符有 ？00/￥00/發00/空。
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict

PROJ = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(PROJ, '咕噜圆预测资料全集.txt')
PLACE = re.compile(r'开\s*[:：]\s*(?:[？?￥$發发]\s*0*0|)\s*(准|错|中)?\s*$')
LABEL = re.compile(r'开\s*[:：]\s*([鼠牛虎兔龙蛇马羊猴鸡狗猪龍馬雞豬])\s*'
                   r'(0?[1-9]|[1-4][0-9])\s*(准|错|中)')


def truth(issue):
    with open(os.path.join(PROJ, 'macau_mark6_data.csv'), encoding='utf-8-sig') as f:
        for r in csv.reader(f):
            if r and r[0] == str(issue):
                # 列序: 期号,日期,平1-6(2-7),特码(8),波色1-7(9-15),生肖1-7(16-22)
                return int(r[8]), r[22].replace('豬', '猪').replace('雞', '鸡').replace('龍', '龙'), r[15]
    return None


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        with open(os.path.join(PROJ, 'macau_mark6_data.csv'), encoding='utf-8-sig') as f:
            arg = [r for r in csv.reader(f) if r and r[0].isdigit()][-1][0]
    full = arg if len(arg) == 7 else '2026' + arg.zfill(3)      # 全集用3位期号
    issue = full[-3:]                                           # 如 '255'
    num, zod, wave = truth(full)
    print(f'══ {full} 期 回填核对 | 真值 特{num:02d} {zod} {wave}波 ══\n')

    person = '?'
    by_sys = defaultdict(list)
    for ln in open(TXT, encoding='utf-8'):
        m = re.match(r'◆◆◆\s*(\S+?)\s*◆◆◆', ln)
        if m:
            person = m.group(1)
        if f'{issue}期' not in ln or '开' not in ln:
            continue
        body = ln.strip()
        sysname = re.match(rf'{issue}期[:：]?([^【(（]*)(.*)', body)
        key = (person, (sysname.group(1).strip() or '-')[:14])
        if PLACE.search(body):
            by_sys[key].append(('占位', body))
            continue
        m2 = LABEL.search(body)
        if m2:
            z, n, mark = m2.group(1), int(m2.group(2)), m2.group(3)
            same = (n == num)
            tag = f'{"✅一致" if same else "⚠️不符"} 标{mark}'
            by_sys[key].append((tag, body))
        else:
            by_sys[key].append(('其他', body))

    tally = Counter()
    for (p, s), rows in sorted(by_sys.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        print(f'▌{p} · {s}  ({len(rows)}条)')
        for tag, body in rows:
            tally[tag.split()[0]] += 1
            print(f'   [{tag}] {body[:95]}')
        print()
    print('统计:', dict(tally))


if __name__ == '__main__':
    main()
