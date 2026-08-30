#!/usr/bin/env python3
"""新方案回测: rot8选位轮转 + 温号3 + (内幕补位无法历史回测, 仅232/233人工验证)
完全复刻 local-rot8.html buildUnion 逻辑 (ti=数组下标, ti%2==0含第8位)
输出: 每期命中明细 + 趋势图HTML
"""
import csv

DATA = "/Users/xiejinyu/macau_mark6_data.csv"

draws = []
with open(DATA, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        i = row['期号'].strip()
        if not i:
            continue
        draws.append({'i': i, 's': int(row['特码'])})
draws.sort(key=lambda d: d['i'])


def build_union(ti, rot=True, warm_n=1):
    """返回 (uni20, warm3) — 与JS buildUnion 完全一致"""
    ttD = draws[:ti]
    tlt = len(ttD)
    sc = {}; sl = {}
    for i, d in enumerate(ttD):
        s = d['s']; sc[s] = sc.get(s, 0) + 1; sl[s] = i
    msv = sorted(tlt - 1 - sl.get(n, tlt) for n in range(1, 50))
    _lo, _hi = msv[12], msv[36]
    omC = []
    for n in range(1, 50):
        mm = tlt - 1 - sl.get(n, tlt)
        if sc.get(n, 0) >= 25 and _lo <= mm <= _hi:
            omC.append([n, sc.get(n, 0), mm])
    # 2026-08-24 排序键优化(2026口径全窗口验证): 热车道按 频×漏 排序(优先"高频中近期更久未出")
    omC.sort(key=lambda x: -(x[1] * x[2]))
    coldC = sorted([[n, tlt - 1 - sl.get(n, tlt)] for n in range(1, 50)], key=lambda x: -x[1])
    repC = []
    for n in range(1, 50):
        rm = tlt - 1 - sl.get(n, tlt)
        if 2 <= rm <= 11 and sc.get(n, 0) >= 30:  # 2026-08-30 重漏10→11: 救238期17(漏11夹缝), 210-242扫描24/33→25/33
            repC.append([n, sc.get(n, 0)])
    repC.sort(key=lambda x: -x[1])
    warmC = []
    for n in range(1, 50):
        rm2 = tlt - 1 - sl.get(n, tlt)
        if sc.get(n, 0) >= 25 and sc.get(n, 0) <= 32 and 20 <= rm2 <= 50:
            warmC.append([n, sc.get(n, 0), rm2])
    # 温号同样按 频×漏 排序 (hot+warm 双频×漏为2026全窗口唯一领先组合)
    warmC.sort(key=lambda x: -(x[1] * x[2]))

    uni = []; used = set()
    def addL(lst, idxs):
        for q in idxs:
            if q - 1 < len(lst):
                nn = lst[q - 1][0]
                if nn not in used:
                    used.add(nn); uni.append(nn)
    addL(omC[:12], [1, 2, 3, 7, 8, 9, 10])
    # 2026-08-24 含4位变体(用户确认采用): 冷车道取位跳过漏榜第4/5位=结构性盲区(236期11号漏116第4位全灭),
    #   含4位(奇偶都8位, 21码总量不变) — 2026口径全窗口+验证段+236期11号救回, 代价2025年/1-30段略深负
    sel = [1, 2, 3, 4, 6, 8, 10, 12] if (rot and ti % 2 == 0) else [1, 2, 3, 4, 6, 10, 11, 12]
    addL(coldC[:12], sel)
    addL(repC[:5], [1, 2, 3, 4, 5])
    for x in omC:
        if len(uni) >= 20:
            break
        if x[0] not in used:
            used.add(x[0]); uni.append(x[0])
    warm = []
    for x in warmC:
        if len(warm) >= 3:
            break
        if x[0] not in used:
            warm.append(x[0])
    return uni, warm[:warm_n]



if __name__ == '__main__':
    start, end = 2026210, 2026233
    rows = []
    for k, d in enumerate(draws):
        if not (start <= int(d['i']) <= end):
            continue
        u20, w3 = build_union(k, rot=True)
        u20_old, w3_old = build_union(k, rot=False)  # 旧V6对照
        rows.append({
            'i': d['i'], 's': d['s'],
            'rot': d['s'] in u20, 'warm': d['s'] in w3,
            'old': d['s'] in u20_old,
            'code': 20 + (1 if d['s'] in w3 else 0),
        })

    n = len(rows)
    hit_old = sum(1 for r in rows if r['old'])
    hit_rot = sum(1 for r in rows if r['rot'])
    hit_new = sum(1 for r in rows if r['rot'] or r['warm'])
    ev_old = hit_old / n * 47 - 20
    ev_rot = hit_rot / n * 47 - 20
    ev_new = hit_new / n * 47 - 21  # 21码 (rot8并集20 + 温号1)

    print(f"回测窗口: {rows[0]['i']} ~ {rows[-1]['i']} 共{n}期")
    print(f"旧V6      20码  命中{hit_old:>2}/{n} {hit_old/n*100:5.1f}%  期望{ev_old:+.1f}/期")
    print(f"rot8      20码  命中{hit_rot:>2}/{n} {hit_rot/n*100:5.1f}%  期望{ev_rot:+.1f}/期")
    print(f"rot8+温号1 21码  命中{hit_new:>2}/{n} {hit_new/n*100:5.1f}%  期望{ev_new:+.1f}/期")
    print(f"\n每期明细 (特码 | 旧V6 | rot8 | 温号 | 结果):")
    for r in rows:
        mark = lambda b: '✅' if b else '❌'
        print(f"  {r['i'][-3:]}期 特码{r['s']:>2} | 旧{mark(r['old'])} rot8{mark(r['rot'])} 温号{mark(r['warm'])} → {'命中' if (r['rot'] or r['warm']) else '未中'}")
