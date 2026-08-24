#!/usr/bin/env python3
"""生成 237期本地对照页 (本地-only, 绝不上线): 三策略池 + 内幕高票 + 共识区 + 补位建议
A=主策略(含4位取位, 2026-08-24用户确认采用) / B=旧取位对照 / C=hot纯频对照
注意: 本脚本 pool() 为独立副本, 主策略取位须与 backtest_new.build_union 保持同步 (cold4=True)
补位规则(回测最优): 高票肖, 每期≤1码, 池外漏最大 (规则A, 216-236 17/20 +18.5)
交叉验证结论: 共识区(高票∩≥2池)58%命中=加注区; 分歧区(高票∩0池)≈随机=补位抓运气区;
  三策略共识过滤补位(B规则)已证伪(0触发, 233/235救命全丢) → 补位规则不动
18策略重复率圈肖 (2026-08-25 用户确认50%为主): 统计各肖在系统中重复次数, <50%排除
  口径: 剔12肖全覆盖系统(精选三头/单双/单尾/规律大小/头数中特)后10个有区分度系统
  216-236验证: 60%圈 15/17=88% 均6.9肖(圈外=231猪/236猴) → 236期猴5/10差1票, 杀含4位救回的11号无解
  50%圈 17/17=100% 均9.5肖 零漏网 → 用户确认改50% (圈肖仅作先取肖参考/排除层, 不进主池)
每期开奖后运行: python3 gen_cross_page.py (自动更新到最新期)
"""
import sys
sys.path.insert(0, '/Users/xiejinyu')
import macau_model_4d as m4
import backtest_full as bf
from backtest_new import build_union

REDS  = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUES = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
def wave(n): return 'red' if n in REDS else ('blue' if n in BLUES else 'green')
WAVE_C = {'red':'#dc2626','blue':'#2563eb','green':'#059669'}

draws = m4.load()
k = len(draws)
ISSUE = int(draws[-1]['i'][-3:]) + 1
LAST_ISSUE = int(draws[-1]['i'][-3:])
per = bf.parse_file('/Users/xiejinyu/macau-mark6/咕噜圆预测资料全集.txt')
idx = {int(d['i'][-3:]): i for i, d in enumerate(draws)}
def zc(n): return m4.ZODIAC[n]

def pool(ti, cold4=False, hotkey='freqleak'):
    ttD = draws[:ti]; tlt = len(ttD)
    sc={}; sl={}
    for i,d in enumerate(ttD):
        s=d['s']; sc[s]=sc.get(s,0)+1; sl[s]=i
    msv = sorted(tlt-1-sl.get(n,tlt) for n in range(1,50))
    _lo,_hi = msv[12], msv[36]
    omC=[]
    for n in range(1,50):
        mm=tlt-1-sl.get(n,tlt)
        if sc.get(n,0)>=25 and _lo<=mm<=_hi: omC.append([n,sc.get(n,0),mm])
    omC.sort(key=lambda x:-(x[1]*x[2]) if hotkey=='freqleak' else -x[1])
    coldC=sorted([[n,tlt-1-sl.get(n,tlt)] for n in range(1,50)],key=lambda x:-x[1])
    repC=[]
    for n in range(1,50):
        rm=tlt-1-sl.get(n,tlt)
        if 2<=rm<=10 and sc.get(n,0)>=30: repC.append([n,sc.get(n,0)])
    repC.sort(key=lambda x:-x[1])
    warmC=[]
    for n in range(1,50):
        rm2=tlt-1-sl.get(n,tlt)
        if sc.get(n,0)>=25 and sc.get(n,0)<=32 and 20<=rm2<=50: warmC.append([n,sc.get(n,0),rm2])
    warmC.sort(key=lambda x:-(x[1]*x[2]) if hotkey=='freqleak' else -x[1])
    uni=[]; used=set()
    def addL(lst,idxs):
        for q in idxs:
            if q-1<len(lst):
                nn=lst[q-1][0]
                if nn not in used: used.add(nn); uni.append(nn)
    addL(omC[:12],[1,2,3,7,8,9,10])
    if cold4:
        addL(coldC[:12],[1,2,3,4,6,8,10,12] if ti%2==0 else [1,2,3,4,6,10,11,12])
    else:
        addL(coldC[:12],[1,2,3,6,8,10,11,12] if ti%2==0 else [1,2,3,6,10,11,12])
    addL(repC[:5],[1,2,3,4,5])
    for x in omC:
        if len(uni)>=20: break
        if x[0] not in used: used.add(x[0]); uni.append(x[0])
    for x in warmC:
        if x[0] not in used: uni.append(x[0])
        if len(uni)>=21: break
    return uni[:21]

A = pool(k, cold4=True); B = pool(k); C = pool(k, hotkey='freq')  # A=主策略(含4位) B=旧取位对照
sA, sB, sC = set(A), set(B), set(C)
tri = [n for n in A if n in sB and n in sC]       # 三池共识
pair = sorted({n for n in A if n in sB} | {n for n in A if n in sC} | {n for n in B if n in sC})

# 内幕高票 (当期资料有则算, 无则提示等待)
hi = []; zs = {}
if ISSUE in per:
    w = bf.weights_until(per, draws, ISSUE)
    zs = bf.weighted_vote(per, ISSUE, w, model=A)
    hi = sorted([z for z in zs if zs[z] >= 7.5], key=lambda z: -zs[z])
    allM = sA | sB | sC
    hi_in2 = sorted([n for n in pair if zc(n) in hi])          # 共识区: 高票肖∩≥2池
    hi_in1 = sorted([n for n in allM if zc(n) in hi])          # 高票肖∩≥1池
    miss = {}
    sl = {}
    for i, d in enumerate(draws[:k]): sl[d['s']] = i
    miss = {n: k-1-sl.get(n, k) for n in range(1, 50)}
    # 补位建议 (规则A: 高票肖, 池外漏最大, 每期≤1码)
    fills = []
    for z in hi:
        in_pool = any(zc(n) == z for n in A)
        if in_pool and zs[z] >= 8: continue
        cand = sorted([n for n in range(1, 50) if zc(n) == z], key=lambda n: -miss[n])
        pick = next((n for n in cand if n not in A), None)
        if pick is not None: fills.append((z, pick, zs[z]))
        break
else:
    hi_in2 = hi_in1 = fills = []

def ball(n, size=30, extra=''):
    c = WAVE_C[wave(n)]
    return (f'<span title="{n:02d}" style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
            f'border-radius:50%;background:{c};color:#fff;font-weight:700;font-size:{size*0.4}px;'
            f'text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.4);{extra}">{n:02d}</span>')
def zball(z, size=30):
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
            f'border-radius:50%;background:#7c3aed;color:#fff;font-weight:700;font-size:{size*0.42}px;'
            f'text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.4)">{z}</span>')

rows_html = ''
for iss in range(216, LAST_ISSUE + 1):
    if iss not in idx or iss not in per: continue
    t = idx[iss]; s = draws[t]['s']
    PA_t = pool(t, cold4=True)
    w2 = bf.weights_until(per, draws, iss)
    zs2 = bf.weighted_vote(per, iss, w2, model=PA_t)
    hi2 = [z for z in zs2 if zs2[z] >= 7.5]
    if not hi2:
        rows_html += f'<tr class="miss"><td>{iss}期</td><td><span class="b" style="background:{WAVE_C[wave(s)]}">{s:02d}</span></td><td>无信号</td><td>{"✅" if s in PA_t else "❌"}</td><td>-</td><td>-</td></tr>'
        continue
    allM2 = set(PA_t) | set(pool(t)) | set(pool(t, hotkey='freq'))
    in2 = [n for n in range(1, 50) if zc(n) in hi2 and n in allM2]
    out = [n for n in range(1, 50) if zc(n) in hi2 and n not in allM2]
    # 出特码候选 = 共识区: 高票肖 ∩ ≥2个模型池的码
    pair2 = sorted({n for n in PA_t if n in set(pool(t))} | {n for n in PA_t if n in set(pool(t, hotkey="freq"))} | {n for n in pool(t) if n in set(pool(t, hotkey="freq"))})
    zg = [n for n in pair2 if zc(n) in hi2]
    hits = []
    sl = {}
    for i, d in enumerate(draws[:t]): sl[d['s']] = i
    PA = pool(t, cold4=True)
    for z in hi2:
        in_pool = any(zc(n) == z for n in PA)
        if in_pool and zs2[z] >= 8: continue
        cand = sorted([n for n in range(1, 50) if zc(n) == z], key=lambda n: -(t-1-sl.get(n, t)))
        p = next((n for n in cand if n not in PA), None)
        if p is not None: hits.append((z, p, zs2[z]))
        break
    s_hit = s in allM2
    fill_str = ''.join(f"{p:02d}" for _, p, _ in hits) or '-'
    hit_fill = any(p == s for _, p, _ in hits)
    zg_str = ' '.join(f'{n:02d}' for n in zg) if zg else '-'
    zg_hit = s in zg
    rows_html += (f'<tr class="{"hit" if s_hit else "miss"}"><td>{iss}期</td>'
                  f'<td><span class="b" style="background:{WAVE_C[wave(s)]}">{s:02d}</span></td>'
                  f'<td>{" ".join(hi2)}</td>'
                  f'<td>{"✅" if s_hit else "❌"} {"" if not hit_fill else "<b class=ok>补位🎯</b>"}</td>'
                  f'<td>{fill_str}</td>'
                  f'<td class="{"zg" if zg_hit else "zg-miss"}">{zg_str}{" 🎯" if zg_hit else ""}</td></tr>')

# 命中跟踪统计
hitsA = hitsB = hitsC = 0
for iss in range(216, LAST_ISSUE + 1):
    if iss not in idx or iss not in per: continue
    t = idx[iss]; s = draws[t]['s']
    hitsA += s in pool(t, cold4=True); hitsB += s in pool(t); hitsC += s in pool(t, hotkey='freq')

# ── 18策略重复率圈肖 (2026-08-25 用户确认50%为主): 各肖在系统中重复次数, <50%排除 ──
# 口径: 剔除≥10肖全覆盖系统(精选三头/单双/单尾/规律大小/头数中特=12肖全覆盖, 无区分度)
# 216-236验证: 60%圈 15/17=88% 均6.9肖(圈外231猪/236猴) → 236期猴5/10差1票, 杀含4位救回的11号无解
#   50%圈 17/17=100% 均9.5肖 零漏网 → 用户确认改50% (圈肖仅作先取肖参考/排除层, 不进主池)
from collections import Counter as _C
ZS12 = '鼠牛虎兔龙蛇马羊猴鸡狗猪'
def circle(iss, p):
    Px = {nm: vz for nm, vz in per[iss]['sys'].items() if len(vz) < 10}
    Nx = len(Px)
    if Nx == 0: return None
    cnt = _C()
    for vz in Px.values(): cnt.update(vz)
    return {z for z in ZS12 if cnt.get(z, 0) / Nx >= p}

c50 = circle(ISSUE, 0.5) if ISSUE in per else None
c60 = circle(ISSUE, 0.6) if ISSUE in per else None
c10 = {nm: vz for nm, vz in per[ISSUE]['sys'].items() if len(vz) < 10} if ISSUE in per else {}
rep_html = ''
if c10:
    NX = len(c10); cnt = _C()
    for vz in c10.values(): cnt.update(vz)
    for z in ZS12:
        cc = cnt.get(z, 0); r = cc / NX; on = r >= 0.5
        rep_html += (f'<div style="display:inline-flex;align-items:center;margin:3px 10px 0 0;width:136px">'
                     f'<span style="width:22px">{z}</span><span style="width:34px;font-size:.65rem;color:{"#34d399" if on else "#64748b"}">{cc}/{NX}</span>'
                     f'<div style="flex:1;height:8px;background:#0d1526;border-radius:4px;overflow:hidden">'
                     f'<div style="width:{r*100:.0f}%;height:100%;background:{"#34d399" if on else "#475569"}"></div></div></div>')
circ50_html = ''.join(zball(z) for z in ZS12 if c50 and z in c50) if c50 else '<span class="none">资料未到</span>'
out50_html = ''.join(z for z in ZS12 if c50 and z not in c50) or '-'
circ60_html = ''.join(zball(z, 24) for z in ZS12 if c60 and z in c60) if c60 else '<span class="none">资料未到</span>'
# 圈肖历史命中 (特码肖是否在圈内) — 50%主口径
c50_n = c50_hit = 0
for iss in range(216, LAST_ISSUE + 1):
    if iss not in per: continue
    c5 = circle(iss, 0.5)
    if c5 is None: continue
    c50_n += 1
    if zc(draws[idx[iss]]['s']) in c5: c50_hit += 1

hi_html = ''.join(f"{zball(z)}<span class=sc>{zs[z]:.1f}</span>" for z in hi) if hi else '<span class="none">237期资料未到, 开奖前补</span>'
cons_html = ''.join(ball(n) for n in hi_in2) if hi_in2 else '<span class="none">本期无</span>'
fill_html = ''.join(ball(n, extra='outline:3px solid #fbbf24') for _, n, _ in fills) if fills else '<span class="none">无(高票全在池且硬分)</span>'
zg_html = ''.join(ball(n, 34, 'outline:3px solid #34d399') for n in hi_in2) if hi_in2 else '<span class="none">237期资料未到 → 出特码区待内幕高票</span>'

# 出特码区历史命中统计 (有内幕信号期)
zg_rows = []
for iss in range(216, LAST_ISSUE + 1):
    if iss not in idx or iss not in per: continue
    t = idx[iss]; s = draws[t]['s']
    PA_t = pool(t, cold4=True); PB_t = pool(t); PC_t = pool(t, hotkey='freq')
    w2 = bf.weights_until(per, draws, iss)
    zs2 = bf.weighted_vote(per, iss, w2, model=PA_t)
    hi2 = [z for z in zs2 if zs2[z] >= 7.5]
    if not hi2: continue
    pair2 = sorted({n for n in PA_t if n in set(PB_t)} | {n for n in PA_t if n in set(PC_t)} | {n for n in PB_t if n in set(PC_t)})
    zg2 = [n for n in pair2 if zc(n) in hi2]
    zg_rows.append((iss, s, zg2, s in zg2))
zg_n = len(zg_rows); zg_hit = sum(1 for r in zg_rows if r[3])
zg_avg = sum(len(r[2]) for r in zg_rows) / zg_n if zg_n else 0
zg_ev = zg_hit / zg_n * 47 - zg_avg if zg_n else 0

html = f'''<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ISSUE}期 本地对照 · 三策略×内幕补位</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b1220;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;padding:16px}}
h1{{font-size:1.15rem;text-align:center;color:#fbbf24;margin-bottom:4px}}
.sub{{text-align:center;font-size:.72rem;color:#94a3b8;margin-bottom:14px}}
.card{{background:#111a2e;border:1px solid #233;border-radius:12px;padding:14px;margin:0 auto 12px;max-width:920px}}
.card h3{{color:#94a3b8;font-size:.85rem;margin-bottom:10px}}
.balls{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}}
.ball{{margin-right:2px}}
.none{{color:#64748b}}
.stat{{display:inline-block;background:#0d1526;border:1px solid #233;border-radius:8px;padding:6px 12px;margin:4px 8px 0 0;font-size:.72rem}}
.stat b{{color:#fbbf24;font-size:1rem}}
.ok{{color:#34d399}}
.warn{{color:#f87171;font-weight:700}}
table{{border-collapse:collapse;width:100%;font-size:.68rem}}
th,td{{border:1px dashed #2d3a52;padding:3px 5px;text-align:center}}
th{{color:#94a3b8;background:#0d1526}}
tr.hit td{{background:#132a22}}
tr.miss td{{color:#4a5a72}}
td.zg{{color:#34d399;font-weight:700}}
td.zg-miss{{color:#4a5a72}}
.b{{display:inline-block;width:24px;height:24px;line-height:24px;border-radius:50%;color:#fff;font-weight:700;font-size:.7rem}}
.sc{{font-size:.6rem;color:#c4b5fd;margin:0 6px 0 2px}}
.lv{{font-size:.68rem;color:#c4b5fd;background:#1e1b4b;border:1px solid #3730a3;border-radius:6px;padding:2px 8px;margin-right:6px}}
.rule{{font-size:.68rem;color:#94a3b8;line-height:1.6;margin-top:8px}}
.pooltag{{font-size:.6rem;color:#fbbf24;font-weight:700;margin-right:6px}}
</style>
</head>
<body>
<h1>🔀 {ISSUE}期 本地对照页 · 三策略 × 内幕补位</h1>
<div class="sub">本地-only · 绝不上线 · 数据至{LAST_ISSUE}期 · 三策略:A=主策略(含4位,已采用) B=旧取位对照 C=hot纯频对照</div>

<div class="card"><h3>🔵 三策略池 (各21码)</h3>
<div class="balls"><span class="pooltag">A主策略</span>{''.join(ball(n,26) for n in A)}</div>
<div class="balls" style="margin-top:10px"><span class="pooltag">B旧取位</span>{''.join(ball(n,26) for n in B)}</div>
<div class="balls" style="margin-top:10px"><span class="pooltag">C纯频</span>{''.join(ball(n,26) for n in C)}</div>
<div class="rule">A∩B∩C 共识 {len(tri)}码: {" ".join(f"{n:02d}" for n in tri) or "-"} · ≥2池 {len(pair)}码<br>
统计(216-{LAST_ISSUE}): A(含4位) {hitsA}次 B(旧取位) {hitsB}次 C(纯频) {hitsC}次 · 2026-08-24 用户确认采用含4位为主策略</div></div>

<div class="card"><h3>🟣 内幕高票 (有效加权分 ≥7.5)</h3>
<div class="balls">{hi_html}</div>
<div class="rule">分数=Σ系统权重×模型一致度 · 硬线8.0 · 来源: 咕噜圆资料 ({ISSUE}期)</div></div>

<div class="card"><h3>🎯 出特码 (高票肖 ∩ ≥2池 共识区) · 历史 {zg_hit}/{zg_n}={zg_hit/zg_n*100:.0f}% 均{zg_avg:.1f}码 期望{zg_ev:+.1f}/期</h3>
<div class="balls">{zg_html}</div>
<div class="rule"><span class="warn">唯一有验证依据的特码来源</span> · 模型21码内部挑特码已证伪(top12命中率低于随机, 红线) · 对照逻辑: 内幕高票肖 ∩ 冷热遗漏模型≥2池共振的码 = 本期特码候选<br>
12期样本 + 2026后验风险 · 命中时特码在区内, 不保证具体码 · 待237期资料到达后本区补全</div></div>

<div class="card"><h3>🟢 共识加注区 (高票肖 ∩ ≥2池) · 交叉验证 7/12=58%</h3>
<div class="balls">{cons_html}</div>
<div class="rule">内幕与模型共振的码, 命中率58%·平均5.2码·期望+22/期(12期样本, 2026后验风险) · 可作加注区, 不替代21码主池</div></div>

<div class="card"><h3>🟠 补位建议 (规则A: 高票肖·池外漏最大·每期≤1码)</h3>
<div class="balls">{fill_html}</div>
<div class="rule">216-236 回测: 补位后 17/20=85% +18.5/期 · 三策略共识过滤补位(B规则)已证伪: 0触发, 233补07/235补32救命全丢<br>
<span class="warn">分歧区(高票∩0池)≈随机整体, 补位是防全灭保险, 非增益来源 · 233/235救命=分歧区运气, 不可复现为优势</span></div></div>

<div class="card"><h3>🧠 18策略重复率圈肖 · 50%圈(用户规则) · 历史特码肖在圈内 {c50_hit}/{c50_n}={c50_hit/c50_n*100:.0f}%</h3>
<div class="balls">50%圈: {circ50_html} <span style="font-size:.68rem;color:#64748b">圈外(排除): {out50_html}</span></div>
<div class="balls" style="margin-top:10px">60%圈(紧参考): {circ60_html}</div>
<div style="margin-top:10px">{rep_html}</div>
<div class="rule">口径: 剔12肖全覆盖系统(精选三头/单双/单尾/规律大小/头数中特)后 {NX if c10 else '-'} 个有区分度系统 · 各肖被多少系统点名, &lt;50%排除(用户规则)<br>
216-236: 50%圈 17/17=100% 均9.5肖 零漏网 · 60%圈 15/17=88%(圈外231猪/236猴) · 高票圈肖对照 9/12=75%<br>
<span class="warn">60%线过不了236</span>: 236期猴5/10差1票, 60%圈排除含4位救回的11号且补位无解(猴5.52分不过线) → 2026-08-25 用户确认改50%<br>
用途: 先取肖参考, 圈外肖减配, 圈内肖加注信心 · 圈肖不进主池(过滤杀尾部救回, 红线)</div></div>

<div class="card"><h3>📋 内幕期对照表 (216-{LAST_ISSUE})</h3>
<div style="overflow-x:auto"><table>
<tr><th>期</th><th>特码</th><th>内幕高票肖</th><th>三池命中</th><th>补位码</th><th>出特码候选</th></tr>{rows_html}
</table></div>
<div class="rule">对照结构: 冷热遗漏模型(21码) ↔ 内幕高票肖 → 出特码=高票肖∩≥2池 · 每期开奖后运行 <b>python3 gen_cross_page.py</b> 自动更新 · 主策略=21码均注, 出特码区可加注, 分歧区不单独买</div></div>
</body>
</html>'''
out = f'/Users/xiejinyu/macau-mark6/local-{ISSUE}-cross.html'
open(out, 'w').write(html)
print('已生成', out)
print(f'A池: {" ".join("%02d"%n for n in A)}')
print(f'B池(含4位): {" ".join("%02d"%n for n in B)}')
print(f'三池共识({len(tri)}码): {" ".join("%02d"%n for n in tri) if tri else "-"}')
print(f'统计(216-{LAST_ISSUE}): A {hitsA} B {hitsB} C {hitsC}')
print(f'出特码区(有内幕期): {zg_hit}/{zg_n}={zg_hit/zg_n*100:.0f}% 均{zg_avg:.1f}码 期望{zg_ev:+.1f}/期')
if hi:
    print(f'内幕高票: {", ".join(f"{z}({zs[z]:.1f})" for z in hi)}')
    print(f'共识加注区({len(hi_in2)}码): {" ".join("%02d"%n for n in hi_in2) if hi_in2 else "-"}')
    print(f'补位建议: {", ".join(f"{z}{n:02d}({sc:.1f})" for z,n,sc in fills) if fills else "无"}')
else:
    print('237期内幕资料未到, 高票/共识/补位区待资料到达后运行本脚本补全')
if c50:
    print(f'圈肖50%({len(c50)}肖): {" ".join(c50)} · 圈外: {" ".join(z for z in ZS12 if z not in c50)}')
    print(f'圈肖60%({len(c60)}肖): {" ".join(c60)}')
print(f'圈肖历史(216-{LAST_ISSUE}): 50%圈 {c50_hit}/{c50_n}={c50_hit/c50_n*100:.0f}%')
