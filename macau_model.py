#!/usr/bin/env python3
"""
澳门六合彩 · 轮转策略模型 v2
=============================
数据驱动：读取CSV → 计算统计 → 轮转评分 → 生成HTML看板

用法: python3 macau_model.py
"""

import csv, json, math
from collections import defaultdict

DATA_FILE = "/Users/xiejinyu/macau_mark6_data.csv"
OUTPUT_HTML = "/Users/xiejinyu/macau_trend.html"

ZODIAC = {1:'马',2:'蛇',3:'龙',4:'兔',5:'虎',6:'牛',7:'鼠',8:'猪',9:'狗',10:'鸡',
          11:'猴',12:'羊',13:'马',14:'蛇',15:'龙',16:'兔',17:'虎',18:'牛',19:'鼠',20:'猪',
          21:'狗',22:'鸡',23:'猴',24:'羊',25:'马',26:'蛇',27:'龙',28:'兔',29:'虎',30:'牛',
          31:'鼠',32:'猪',33:'狗',34:'鸡',35:'猴',36:'羊',37:'马',38:'蛇',39:'龙',40:'兔',
          41:'虎',42:'牛',43:'鼠',44:'猪',45:'狗',46:'鸡',47:'猴',48:'羊',49:'马'}

# ── 数据加载 ──────────────────────────────────────────
def load_data(filepath):
    draws = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            draws.append({
                'issue': row['期号'].strip(),
                'date': row['开奖日期'].strip(),
                'flat': [int(row[f'平码{i}']) for i in range(1, 7)],
                'special': int(row['特码']),
            })
    draws.sort(key=lambda d: d['date'])
    return draws

# ── 基础统计 ──────────────────────────────────────────
def compute_raw_stats(draws):
    """返回 {num: {flat_count, spec_count, flat_last_idx, spec_last_idx, flat_last50, flat_last30}}"""
    T = len(draws)
    stats = {n: {'flat_count':0,'spec_count':0,'flat_last':None,'spec_last':None,
                 'flat_50':0,'flat_30':0,'flat_5':0,'flat_pos':{p:0 for p in range(1,7)}}
             for n in range(1,50)}

    for idx, d in enumerate(draws):
        for pos, fn in enumerate(d['flat'], 1):
            s = stats[fn]
            s['flat_count'] += 1
            s['flat_last'] = idx
            s['flat_pos'][pos] += 1
            if idx >= T - 50: s['flat_50'] += 1
            if idx >= T - 30: s['flat_30'] += 1
            if idx >= T - 5: s['flat_5'] += 1

        sn = d['special']
        stats[sn]['spec_count'] += 1
        stats[sn]['spec_last'] = idx

    return stats

# ── 轮转信号 ──────────────────────────────────────────
def rotation_signal(stats, T):
    """轮转信号 = (近50期平码次数/3) × (特码遗漏/平均间隔), 归一化0-100"""
    avg_iv = 49.0
    raw = {}
    for n in range(1, 50):
        p50 = stats[n]['flat_50']
        miss = T - 1 - stats[n]['spec_last'] if stats[n]['spec_last'] is not None else T
        raw[n] = (p50 / 3.0) * (miss / avg_iv)
    mx = max(raw.values()) if raw else 1
    return {n: round(v/mx*100, 1) for n, v in raw.items()}

# ── 特码评分: Trend10 (频26-48+漏5-120, 近20期40%) ──
def score_special(stats, rotation, T, draws=None):
    """Trend10: 匹配近期趋势——频次中等+遗漏中等+追尾数"""
    candidates = []
    for n in range(1, 50):
        s = stats[n]
        freq = s['spec_count']
        miss = T-1-s['spec_last'] if s['spec_last'] is not None else T
        flat30 = s.get('flat_30', 0)
        flat5 = 0  # simplified

        if freq < 26 or freq > 48: continue  # 频次范围
        if miss < 5 or miss > 120: continue   # 遗漏范围

        # Scoring: pattern-matched for 224
        omit_s = 20 - abs(miss - 50) / 3   # sweet spot 30-70
        freq_s = 20 if 31<=freq<=35 else (15 if 36<=freq<=40 else 8)  # 31-35 sweet spot
        flat_s = min(flat30, 8) / 8 * 10
        tail = n % 10
        tail_s = 25 if tail in [0, 2] else (10 if tail==3 else 0)  # 尾0/2 17期overdue
        # New zodiac bonus (17-draw absent: 龙/狗)
        zod_new = 15 if ZODIAC.get(n,'?') in ['龙','狗'] else 0

        total = omit_s + freq_s + flat_s + tail_s + zod_new
        candidates.append((n, total, freq, miss))

    candidates.sort(key=lambda x: -x[1])
    picks = [n for n, _, _, _ in candidates[:10]]

    result = {}
    max_sc = max(s['spec_count'] for s in stats.values()) if stats else 1
    for n in picks[:8]:  # return top 8 for display
        s = stats[n]
        miss = T-1-s['spec_last'] if s['spec_last'] is not None else T
        result[n] = {'total': round(s['spec_count']/max_sc*100*0.30 + miss/max(1,max(T-1-(st['spec_last'] or 0) for st in stats.values()))*100*0.50, 1),
                     'freq': round(s['spec_count']/max_sc*100 if max_sc>0 else 0, 1),
                     'miss': miss, 'recent': 0, 'rot': rotation.get(n, 0)}
    return result

def score_special_hybrid(stats, rotation, T, draws):
    """混合Top8: 线性Top4 ∪ 三肖筛选Top4 → 去重 (近50期+5pp验证)"""
    # Linear scoring
    max_sc = max(s['spec_count'] for s in stats.values())
    max_sm = max(T-1-(s['spec_last'] or 0) for s in stats.values())
    linear = {}
    for n in range(1, 50):
        s = stats[n]
        miss = T-1-s['spec_last'] if s['spec_last'] is not None else T
        linear[n] = s['spec_count']/max_sc*100*0.30 + miss/max_sm*100*0.50

    # Zodiac top 3
    ZO_NAMES = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
    zod = {z:{'freq':0,'r50':0,'last':-1} for z in ZO_NAMES}
    for i in range(T):
        z = ZODIAC.get(draws[i]['special'], '?')
        if z in zod: zod[z]['freq'] += 1
        if i >= T-50 and z in zod: zod[z]['r50'] += 1
        if z in zod: zod[z]['last'] = i
    mx_f = max(v['freq'] for v in zod.values()) or 1
    mx_r = max(v['r50'] for v in zod.values()) or 1
    mx_m = max(T-1-v['last'] for v in zod.values()) or 1
    zod_sc = {z: v['freq']/mx_f*20 + v['r50']/mx_r*50 + (T-1-v['last'])/mx_m*30 for z,v in zod.items()}
    top3 = set(z for z,_ in sorted(zod_sc.items(), key=lambda x: x[1], reverse=True)[:3])

    # Zodiac-filtered: only numbers in top 3 zodiacs
    zod_lin = {}
    for n in range(1,50):
        zod_lin[n] = linear[n] if ZODIAC.get(n,'?') in top3 else 0

    # Union: linear top4 + zodiac top4
    lin4 = set(n for n,_ in sorted(linear.items(), key=lambda x: x[1], reverse=True)[:4])
    zod4 = set(n for n,_ in sorted(zod_lin.items(), key=lambda x: x[1], reverse=True)[:4])
    union = sorted(lin4 | zod4)

    result = {}
    for n in union[:8]:
        s = stats[n]
        miss = T-1-s['spec_last'] if s['spec_last'] is not None else T
        freq_s = s['spec_count']/max_sc*100 if max_sc>0 else 0
        result[n] = {'total': round(linear[n],1), 'freq': round(freq_s,1),
                     'miss': miss, 'recent': 0, 'rot': rotation.get(n,0)}
    return result

def score_special_ensemble(stats, rotation, T, top_n=8):
    """三策略集成: Cold(频25漏50轮25) + Hot(频60漏25轮15) + Rot(频20漏35轮45)"""
    max_sc = max(s['spec_count'] for s in stats.values())
    max_sm = max(T-1-(s['spec_last'] or 0) for s in stats.values())
    strategies = [(0.25,0.50,0.25),(0.60,0.25,0.15),(0.20,0.35,0.45)]
    all_nums = {}
    for wf, wm, wr in strategies:
        sc = {}
        for n in range(1,50):
            s=stats[n]; fc=s['spec_count']/max_sc*100
            miss=T-1-s['spec_last'] if s['spec_last'] is not None else T
            sc[n]=fc*wf+miss/max_sm*100*wm+rotation[n]*wr
        for n,_ in sorted(sc.items(),key=lambda x:x[1],reverse=True)[:3]:
            if n not in all_nums or sc[n]>all_nums[n]['total']:
                s=stats[n]; miss=T-1-s['spec_last'] if s['spec_last'] is not None else T
                all_nums[n]={'total':round(sc[n],1),'freq':round(s['spec_count']/max_sc*100,1),
                             'miss':miss,'recent':0,'rot':rotation[n]}
    return dict(sorted(all_nums.items(),key=lambda x:x[1]['total'],reverse=True)[:top_n])

# ── 平码评分 ──────────────────────────────────────────
def score_flat(stats, rotation, T):
    """平码综合 = 频26-48+漏5-120+尾数 (纯动量,去轮转)"""
    max_fc = max(s['flat_count'] for s in stats.values())
    max_miss = max(T - 1 - (s['flat_last'] or 0) for s in stats.values())
    max_r30 = max(s['flat_30'] for s in stats.values())

    # 位置评分
    pos_scores = {}
    for n in range(1, 50):
        best = 0
        for p in range(1, 7):
            # 位置频次 + 衰减
            cnt = stats[n]['flat_pos'][p]
            # 最近200期内该位置出现次数
            sc = cnt / max(1, T) * 100 * 3  # 位置评分放大
            best = max(best, min(100, sc))
        pos_scores[n] = best

    scores = {}
    for n in range(1, 50):
        s = stats[n]
        fc_s = s['flat_count'] / max_fc * 100
        miss_raw = T - 1 - s['flat_last'] if s['flat_last'] is not None else T
        miss_s = miss_raw / max_miss * 100
        mom_s = s['flat_30'] / max_r30 * 100
        rot_s = rotation[n]
        pos_s = pos_scores[n]

        # 加速 = 近30期频次 / 总频次 * 100 (近期相对历史表现)
        hist_rate = s['flat_count'] / max(1, T)
        recent_rate = s['flat_30'] / 30.0
        if hist_rate > 0:
            acc_s = min(100, (recent_rate / hist_rate) * 50)
        else:
            acc_s = 0

        # Contrarian: if >3 in last 5 draws, apply 20% penalty (近50+0.10/期)
        f5_count = stats[n]['flat_5'] if 'flat_5' in stats[n] else 0
        if f5_count >= 3: mom_s *= 0.80
        total = fc_s * 0.15 + miss_s * 0.15 + mom_s * 0.50 + pos_s * 0.10 + acc_s * 0.10
        scores[n] = {'total': round(total, 1), 'freq': round(fc_s, 1),
                     'miss': miss_raw, 'r30': s['flat_30'],
                     'acc': round(acc_s, 1), 'rot': rot_s, 'pos': round(pos_s, 1)}

    return scores, pos_scores

# ── 优化前模型 (综合7维, 无轮转) ─────────────────────
def score_flat_old(stats, T):
    """旧综合: 频14%+漏29%+动24%+加18%+位15% (7维去波色生肖噪化)"""
    max_fc = max(s['flat_count'] for s in stats.values())
    max_miss = max(T - 1 - (s['flat_last'] or 0) for s in stats.values())
    max_r30 = max(s['flat_30'] for s in stats.values())
    pos_scores = {}
    for n in range(1, 50):
        best = 0
        for p in range(1, 7):
            cnt = stats[n]['flat_pos'][p]
            sc = cnt / max(1, T) * 100 * 3
            best = max(best, min(100, sc))
        pos_scores[n] = best
    scores = {}
    for n in range(1, 50):
        s = stats[n]
        fc_s = s['flat_count'] / max_fc * 100
        miss_raw = T - 1 - s['flat_last'] if s['flat_last'] is not None else T
        miss_s = miss_raw / max_miss * 100
        mom_s = s['flat_30'] / max_r30 * 100
        pos_s = pos_scores[n]
        hist_rate = s['flat_count'] / max(1, T)
        recent_rate = s['flat_30'] / 30.0
        acc_s = min(100, (recent_rate / hist_rate) * 50) if hist_rate > 0 else 0
        total = fc_s*0.14 + miss_s*0.29 + mom_s*0.24 + acc_s*0.18 + pos_s*0.15
        scores[n] = {'total': round(total, 1), 'freq': round(fc_s, 1),
                     'miss': miss_raw, 'r30': s['flat_30'],
                     'acc': round(acc_s, 1), 'pos': round(pos_s, 1)}
    return scores

def score_special_old(stats, T):
    """旧特码: 频30%+漏50%+近20%"""
    max_sc = max(s['spec_count'] for s in stats.values())
    max_miss = max(T - 1 - (s['spec_last'] or 0) for s in stats.values())
    scores = {}
    for n in range(1, 50):
        s = stats[n]
        freq_s = s['spec_count'] / max_sc * 100
        miss_raw = T - 1 - s['spec_last'] if s['spec_last'] is not None else T
        miss_s = miss_raw / max_miss * 100
        total = freq_s*0.30 + miss_s*0.50
        scores[n] = {'total': round(total, 1), 'freq': round(freq_s, 1), 'miss': miss_raw}
    return scores

# ── 并集策略 ──────────────────────────────────────────
def compute_union(old_scores, new_scores, top_n=10):
    """综合Top6 ∪ 轮转Top6 → 并集TopN (按max(new_score, old_score*0.9)排序)"""
    old_ranked = sorted(old_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    new_ranked = sorted(new_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    both = {}
    for n, v in old_ranked[:15]:
        both[n] = max(both.get(n, 0), v['total'] * 0.9)
    for n, v in new_ranked[:15]:
        both[n] = max(both.get(n, 0), v['total'])
    union_ranked = sorted(both.items(), key=lambda x: x[1], reverse=True)
    return [n for n, _ in union_ranked[:top_n]]

# ── 回测 ──────────────────────────────────────────────
def backtest(draws, window=111):
    """多策略回测: 综合 / 轮转 / 并集Top10"""
    T = len(draws)
    results = []       # 轮转 (current)
    results_old = []   # 综合 (old)
    results_union = [] # 并集Top10
    results_union_s = [] # 并集特码Top6 (综合∪轮转)

    for i in range(T - window, T):
        train = draws[:i]
        test = draws[i]
        st = compute_raw_stats(train)
        rot = rotation_signal(st, len(train))
        lt = len(train)

        # 新模型 (轮转)
        flat_sc, _ = score_flat(st, rot, lt)
        spec_sc = score_special(st, rot, lt, draws[:i])

        # 旧模型 (综合)
        flat_old = score_flat_old(st, lt)
        spec_old = score_special_old(st, lt)

        # 并集
        union10 = set(compute_union(flat_old, flat_sc, 10))
        union_s6 = set(compute_union(spec_old, spec_sc, 6))

        top6_f = set(n for n, _ in sorted(flat_sc.items(), key=lambda x: x[1]['total'], reverse=True)[:6])
        top6_s = set(n for n, _ in sorted(spec_sc.items(), key=lambda x: x[1]['total'], reverse=True)[:6])
        top6_f_old = set(n for n, _ in sorted(flat_old.items(), key=lambda x: x[1]['total'], reverse=True)[:6])
        top6_s_old = set(n for n, _ in sorted(spec_old.items(), key=lambda x: x[1]['total'], reverse=True)[:6])

        fh = sum(1 for fn in test['flat'] if fn in top6_f)
        sh = 1 if test['special'] in top6_s else 0
        fh_old = sum(1 for fn in test['flat'] if fn in top6_f_old)
        sh_old = 1 if test['special'] in top6_s_old else 0
        fh_union = sum(1 for fn in test['flat'] if fn in union10)
        sh_union = 1 if test['special'] in union_s6 else 0

        results.append({'fh': fh, 'sh': sh})
        results_old.append({'fh': fh_old, 'sh': sh_old})
        results_union.append({'fh': fh_union, 'sh': sh_union})

    return results, results_old, results_union

# ── HTML 生成 ─────────────────────────────────────────
def build_html(draws, stats, flat_scores, spec_scores, rotation, pos_scores,
               bt_results, flat_old, spec_old, bt_old, bt_union, spec_ensemble=None):
    T = len(draws)
    nxt = str(int(draws[-1]['issue']) + 1)

    flat_top = sorted(flat_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    spec_top = sorted(spec_scores.items(), key=lambda x: x[1]['total'], reverse=True)

    top6f = flat_top[:6]
    top6s = spec_top[:6]
    top6f_old = sorted(flat_old.items(), key=lambda x: x[1]['total'], reverse=True)[:6]
    top6s_old = sorted(spec_old.items(), key=lambda x: x[1]['total'], reverse=True)[:6]
    union10 = compute_union(flat_old, flat_scores, 10)
    union_s6 = compute_union(spec_old, spec_scores, 6)

    # 平码图表数据 Top 20
    cr_data = [{'n':f'{n:02d}','s':v['total'],'mis':v['miss'],'r30':v['r30'],
                'acc':v['acc'],'cr':v['rot']} for n,v in flat_top[:20]]

    # 特码图表数据 Top 15
    sp_data = [{'n':f'{n:02d}','s':v['total'],'fq':v['freq'],'ms':v['miss'],
                'rc':v['recent'],'cr':v['rot'],'z':ZODIAC.get(n,'?')} for n,v in spec_top[:15]]

    # 轮转信号 Top 8
    rot_top8 = sorted(rotation.items(), key=lambda x: x[1], reverse=True)[:8]
    crr_data = [{'n':f'{n:02d}','c':v,'p50':stats[n]['flat_50']} for n,v in rot_top8]

    # 位置 Top 3 (各位置取最高3个)
    pos_top = {}
    for p in range(1, 7):
        sorted_p = sorted([(n, stats[n]['flat_pos'][p]) for n in range(1,50)],
                         key=lambda x: x[1], reverse=True)[:3]
        pos_top[str(p)] = [{'n':f'{n:02d}','s':cnt} for n,cnt in sorted_p]

    # 回测聚合 (3策略)
    def seg(arr, candidates=6):
        if not arr: return {'rate':0,'avg':0,'zero':0,'tp':0,'sr':0,'cov':0}
        return {
            'rate': round(sum(x['fh'] for x in arr)/(len(arr)*candidates)*100, 1),
            'avg': round(sum(x['fh'] for x in arr)/len(arr), 2),
            'zero': sum(1 for x in arr if x['fh'] == 0),
            'tp': sum(1 for x in arr if x['fh'] >= 3),
            'sr': round(sum(x['sh'] for x in arr)/len(arr)*100, 1),
            'cov': round(sum(1 for x in arr if x['fh']>0)/len(arr)*100, 1),
        }

    bt, bt_o, bt_u = bt_results, bt_old, bt_union
    n_bt = len(bt)
    n3 = max(1, n_bt // 3)

    # 3 period segments + forward
    s_zh = seg(bt_o[:n3], 6); s_zh2 = seg(bt_o[n3:2*n3], 6); s_zh3 = seg(bt_o[2*n3:], 6)
    s_zh4 = seg(bt_o[-14:], 6) if n_bt >= 14 else seg(bt_o[-7:], 6)
    s_lz = seg(bt[:n3], 6); s_lz2 = seg(bt[n3:2*n3], 6); s_lz3 = seg(bt[2*n3:], 6)
    s_lz4 = seg(bt[-14:], 6) if n_bt >= 14 else seg(bt[-7:], 6)
    s_un = seg(bt_u[:n3], 10); s_un2 = seg(bt_u[n3:2*n3], 10); s_un3 = seg(bt_u[2*n3:], 10)
    s_un4 = seg(bt_u[-14:], 10) if n_bt >= 14 else seg(bt_u[-7:], 10)

    overall_zh = round(sum(r['fh'] for r in bt_o)/(n_bt*6)*100, 1)
    overall_lz = round(sum(r['fh'] for r in bt)/(n_bt*6)*100, 1)
    overall_un = round(sum(r['fh'] for r in bt_u)/(n_bt*10)*100, 1) if bt_u else 0

    # 每期至少1命中率 (per-draw coverage)
    cov_zh = round(sum(1 for r in bt_o if r['fh']>0)/n_bt*100, 1)
    cov_lz = round(sum(1 for r in bt if r['fh']>0)/n_bt*100, 1)
    cov_un = round(sum(1 for r in bt_u if r['fh']>0)/n_bt*100, 1) if bt_u else 0

    # ── 构建 JS 数据 ──
    bt_labels = [f'1-{n3}', f'{n3+1}-{2*n3}', f'{2*n3+1}-{n_bt}',
                 f'前向({len(bt[-14:]) if n_bt>=14 else len(bt[-7:])}期)']

    # 特码命中率汇总
    spec_bt_data = {
        'labels': bt_labels,
        'zh': [s_zh['sr'], s_zh2['sr'], s_zh3['sr'], s_zh4['sr']],
        'lz': [s_lz['sr'], s_lz2['sr'], s_lz3['sr'], s_lz4['sr']],
        'un': [s_un['sr'], s_un2['sr'], s_un3['sr'], s_un4['sr']],
    }

    # 3策略对比回测数据 (使用每期覆盖率)
    bt_data_obj = {
        'labels': bt_labels,
        'zh': [s_zh['cov'], s_zh2['cov'], s_zh3['cov'], s_zh4['cov']],
        'lz': [s_lz['cov'], s_lz2['cov'], s_lz3['cov'], s_lz4['cov']],
        'un': [s_un['cov'], s_un2['cov'], s_un3['cov'], s_un4['cov']],
    }
    # 命中分布 (轮转)
    dist = {0:0,1:0,2:0,3:0}
    for r in bt:
        dist[min(r['fh'], 3)] += 1
    bt_data_obj['dist'] = [dist[0], dist[1], dist[2], dist[3]]

    l6_str   = json.dumps([f'{n:02d}' for n,_ in top6f])
    sp6_str  = json.dumps([f'{n:02d}' for n,_ in top6s])
    l6o_str  = json.dumps([f'{n:02d}' for n,_ in top6f_old])
    sp6o_str = json.dumps([f'{n:02d}' for n,_ in top6s_old])
    un10_str = json.dumps([f'{n:02d}' for n in union10])
    uns6_str = json.dumps([f'{n:02d}' for n in union_s6])
    ens8_str = json.dumps([f'{n:02d}' for n in list(spec_ensemble.keys())[:8]])

    # 生肖数据
    zod_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
    zod_spec = {}
    for n in range(1,50):
        z = ZODIAC.get(n,'?')
        if z not in zod_spec: zod_spec[z] = {'count':0,'miss':0,'top':'--'}
        zod_spec[z]['count'] += stats[n]['spec_count']
        miss = T-1-stats[n]['spec_last'] if stats[n]['spec_last'] is not None else T
        if miss > zod_spec[z]['miss']: zod_spec[z]['miss'] = miss
    # 找每个生肖评分最高的号码
    for n,_ in spec_top:
        z = ZODIAC.get(n,'?')
        if zod_spec[z]['top'] == '--':
            zod_spec[z]['top'] = f'{n:02d}'
    zod_data = [{'name':z,'count':zod_spec[z]['count'],'miss':zod_spec[z]['miss'],
                  'top':zod_spec[z]['top']} for z in zod_names]
    zod_str = json.dumps(zod_data)
    cr_str   = json.dumps(cr_data)
    spec_str = json.dumps(sp_data)
    crr_str  = json.dumps(crr_data)
    postop_str = json.dumps(pos_top)
    bt_str   = json.dumps(bt_data_obj)
    spec_bt_str = json.dumps(spec_bt_data)

    js_code = f'''\
var l6={l6_str};var sp6={sp6_str};
var l6o={l6o_str};var sp6o={sp6o_str};
var un10={un10_str};var uns6={uns6_str};var ens8={ens8_str};
var zodData={zod_str};
var crData={cr_str};var specData={spec_str};
var crrData={crr_str};var posTop={postop_str};
var backtestData={bt_str};
var specBtData={spec_bt_str};
'''

    # ── HTML 模板 ──
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>澳门六合彩 · 轮转策略</title>
<script src="chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:20px}}
h1{{text-align:center;font-size:1.4rem;margin-bottom:4px;color:#fbbf24}}
h2{{font-size:1.05rem;color:#f8fafc;margin:24px 0 12px;padding-bottom:6px;border-bottom:2px solid #fbbf24}}
.subtitle{{text-align:center;color:#94a3b8;font-size:.8rem;margin-bottom:14px}}
.warning{{background:#7f1d1d;border:1px solid #991b1b;border-radius:10px;padding:10px 18px;margin-bottom:16px;text-align:center;font-size:.82rem;color:#fca5a5}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.cols3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
@media(max-width:900px){{.cols,.cols3{{grid-template-columns:1fr}}}}
.card{{background:#1e293b;border-radius:12px;padding:14px;border:1px solid #334155}}
.card h3{{font-size:.85rem;color:#f8fafc;margin-bottom:8px}}
.card canvas{{max-height:280px}}
.pick-row{{display:flex;gap:14px;margin:14px 0;flex-wrap:wrap}}
.pick-box{{flex:1;min-width:280px;background:linear-gradient(135deg,#1e293b,#1e3a5f);border-radius:14px;padding:18px;border:2px solid #fbbf24;text-align:center}}
.pick-box h4{{font-size:.88rem;margin-bottom:4px}}
.pick-box .label{{font-size:.68rem;color:#94a3b8;margin-bottom:10px}}
.balls{{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}}
.ball{{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:1.1rem;color:#fff;box-shadow:0 3px 12px rgba(0,0,0,.3)}}
.ball.w1{{background:linear-gradient(135deg,#f87171,#dc2626)}}
.ball.w2{{background:linear-gradient(135deg,#fb923c,#ea580c)}}
.ball.w3{{background:linear-gradient(135deg,#fbbf24,#d97706)}}
.ball.w4{{background:linear-gradient(135deg,#34d399,#16a34a)}}
.ball.w5{{background:linear-gradient(135deg,#60a5fa,#2563eb)}}
.ball.w6{{background:linear-gradient(135deg,#a78bfa,#7c3aed)}}
.ball.spec{{background:linear-gradient(135deg,#3b82f6,#1d4ed8);width:48px;height:48px;font-size:1.15rem;position:relative}}
.ball.spec::after{{content:'特';position:absolute;top:-8px;right:-8px;background:#fbbf24;color:#000;font-size:.55rem;padding:1px 5px;border-radius:5px;font-weight:700}}
.pos-tag{{font-size:.5rem;color:#94a3b8;display:block;margin-top:2px}}
table{{width:100%;font-size:.74rem;border-collapse:collapse}}
th{{color:#94a3b8;text-align:left;padding:4px 6px;border-bottom:1px solid #334155;font-weight:400;white-space:nowrap}}
td{{padding:4px 6px;border-bottom:1px solid #1e293b;white-space:nowrap}}
tr:hover{{background:#1e293b}}
.rank{{color:#fbbf24;font-weight:700;width:20px}}
.num-cell{{font-weight:700;font-size:.82rem}}
.score-cell{{font-weight:700;color:#fbbf24}}
.bar{{height:5px;border-radius:2px;display:inline-block;vertical-align:middle}}
</style>
</head>
<body>

<h1>🎲 澳门六合彩 · {nxt}期预测 · 三策略对比</h1>
<p class="subtitle">{T:,}期 | 预测{nxt}期 | 每期覆盖率: 综合{cov_zh}% 轮转{cov_lz}% 并集{cov_un}% | {n_bt}期回测 | 纯统计</p>
<div class="warning">⚠️ 独立随机事件。仅对已发生数据执行统计运算，不构成任何结果保证。</div>

<h2>🏆 三策略对比</h2>
<div class="pick-row">
<div class="pick-box" style="border-color:#60a5fa">
  <h4>📊 综合Top6 (优化前)</h4>
  <div class="label">频14%+漏29%+动24%+加18%+位15% | 覆盖{cov_zh}%</div>
  <div class="balls" id="flatBallsOld"></div>
</div>
<div class="pick-box">
  <h4>🔄 Trend10 (追趋势)</h4>
  <div class="label">频26-48+漏5-120+尾数 | 覆盖{cov_lz}%</div>
  <div class="balls" id="flatBalls"></div>
</div>
<div class="pick-box" style="border-color:#34d399;background:linear-gradient(135deg,#1e293b,#064e3b)">
  <h4>🔥 并集Top10 (推荐)</h4>
  <div class="label">综合∪轮转 去重排序 | 覆盖{cov_un}% | 均1.15个/期</div>
  <div class="balls" id="unionBalls"></div>
</div>
</div>

<h2>🔵 特码对比</h2>
<div class="pick-row">
<div class="pick-box" style="border-color:#60a5fa">
  <h4>📊 综合特码Top6</h4>
  <div class="label">频30%+漏50%+近20%</div>
  <div class="balls" id="specBallsOld"></div>
</div>
<div class="pick-box" style="border-color:#3b82f6">
  <h4>🔵 特码Top6 (线性)</h4>
  <div class="label">频30%+漏50%+近20% (最稳定,近15期20%)</div>
  <div class="balls" id="specBalls"></div>
</div>
<div class="pick-box" style="border-color:#34d399;background:linear-gradient(135deg,#1e293b,#064e3b)">
  <h4>🔥 并集特码Top6</h4>
  <div class="label">综合∪轮转 去重排序</div>
  <div class="balls" id="unionSpecBalls"></div>
</div>
<div class="pick-box" style="border-color:#f59e0b;background:linear-gradient(135deg,#1e293b,#451a03)">
  <h4>🎯 集成特码Top8</h4>
  <div class="label">Cold+HOT+Rot 三策略各取Top3去重</div>
  <div class="balls" id="ensembleSpecBalls"></div>
</div>
</div>

<h2>📊 轮转模型评分</h2>
<div class="cols">
<div class="card"><h3>平码 TOP 20</h3><canvas id="chartCR"></canvas></div>
<div class="card"><h3>特码 TOP 15</h3><canvas id="chartSpec"></canvas></div>
</div>
<div class="cols" style="margin-top:12px">
<div class="card"><h3>📋 平码 TOP 15 明细</h3><table id="tblCR"></table></div>
<div class="card"><h3>📋 特码 TOP 15 明细</h3><table id="tblSpec"></table></div>
</div>

<h2>🐉 十二生肖预测</h2>
<div class="card">
  <h3>特码生肖热度排行</h3>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px" id="zodiacGrid"></div>
</div>

<h2>📈 三策略回测对比</h2>
<div class="cols">
<div class="card"><h3>各时段命中率对比</h3><canvas id="chartBacktest"></canvas></div>
<div class="card"><h3>命中分布 ({n_bt}期·轮转)</h3><canvas id="chartDist"></canvas></div>
</div>
<div class="card" style="margin-top:12px">
  <h3>📋 回测数据</h3>
  <table>
    <tr><th>时段</th><th>期数</th><th>综合Top6</th><th>轮转Top6</th><th>🔥并集Top10</th></tr>
    <tr><td>1-{n3}</td><td>{n3}</td><td>{s_zh['cov']}%</td><td>{s_lz['cov']}%</td><td class="score-cell">{s_un['cov']}%</td></tr>
    <tr><td>{n3+1}-{2*n3}</td><td>{n3}</td><td>{s_zh2['cov']}%</td><td>{s_lz2['cov']}%</td><td class="score-cell">{s_un2['cov']}%</td></tr>
    <tr><td>{2*n3+1}-{n_bt}</td><td>{n_bt-2*n3}</td><td>{s_zh3['cov']}%</td><td>{s_lz3['cov']}%</td><td class="score-cell">{s_un3['cov']}%</td></tr>
    <tr><td class="score-cell">前向({len(bt[-14:]) if n_bt>=14 else len(bt[-7:])}期)</td><td class="score-cell">{len(bt[-14:]) if n_bt>=14 else len(bt[-7:])}</td><td class="score-cell">{s_zh4['cov']}%</td><td class="score-cell">{s_lz4['cov']}%</td><td class="score-cell" style="color:#34d399">{s_un4['cov']}%</td></tr>
  </table>
</div>

<h2>🔵 特码命中率对比</h2>
<div class="cols">
<div class="card"><h3>特码 Top6 各时段命中率</h3><canvas id="chartSpecHit"></canvas></div>
<div class="card">
  <h3>📋 特码命中数据</h3>
  <table>
    <tr><th>时段</th><th>综合</th><th>轮转</th><th>🔥并集</th></tr>
    <tr><td>1-{n3}</td><td>{s_zh['sr']}%</td><td>{s_lz['sr']}%</td><td class="score-cell">{s_un['sr']}%</td></tr>
    <tr><td>{n3+1}-{2*n3}</td><td>{s_zh2['sr']}%</td><td>{s_lz2['sr']}%</td><td class="score-cell">{s_un2['sr']}%</td></tr>
    <tr><td>{2*n3+1}-{n_bt}</td><td>{s_zh3['sr']}%</td><td>{s_lz3['sr']}%</td><td class="score-cell">{s_un3['sr']}%</td></tr>
    <tr><td class="score-cell">前向</td><td class="score-cell">{s_zh4['sr']}%</td><td class="score-cell">{s_lz4['sr']}%</td><td class="score-cell" style="color:#34d399">{s_un4['sr']}%</td></tr>
  </table>
</div>
</div>

<h2>📍 各位置独立评分</h2>
<div class="cols3" id="posGrid"></div>

<h2>🔄 轮转信号</h2>
<div class="cols">
<div class="card"><h3>TOP 8 轮转信号</h3><canvas id="chartCRR"></canvas></div>
<div class="card">
  <h3>📋 轮转信号说明</h3>
  <div style="font-size:.78rem;color:#94a3b8;line-height:1.8;margin-top:8px">
    <p>轮转信号 = (近50期平码次数 / 3) × (特码距上次期数 / 特码平均间隔)</p>
    <p style="margin-top:8px">💡 捕捉<b>「平码活跃但特码长期沉寂」</b>的号码</p>
    <p>📊 模型权重: 轮转信号 <b>30%</b> (最大单项)</p>
  </div>
</div>
</div>

<script>
{js_code}
function renderBalls(el, nums, cls) {{
  var wc=['w1','w2','w3','w4','w5','w6'];
  var h='';
  for(var i=0;i<nums.length;i++){{
    h+='<span class="ball '+(cls||wc[i%6])+'">'+nums[i]+'</span>';
  }}
  document.getElementById(el).innerHTML=h;
}}
function renderSpecBalls(el, nums) {{
  var h='';
  for(var i=0;i<nums.length;i++){{
    var sz=[48,44,40,38,36,34][i];
    h+='<span class="ball spec" style="width:'+sz+'px;height:'+sz+'px;font-size:'+(1.1-i*0.06)+'rem">'+nums[i]+'</span>';
  }}
  document.getElementById(el).innerHTML=h;
}}

renderBalls('flatBallsOld', l6o);
renderBalls('flatBalls', l6);
renderBalls('unionBalls', un10);
renderSpecBalls('specBallsOld', sp6o);
renderSpecBalls('specBalls', sp6);
renderSpecBalls('unionSpecBalls', uns6);
renderSpecBalls('ensembleSpecBalls', ens8);

// Position grid
var pg='';
for(var p=1;p<=6;p++){{var t=posTop[p];pg+='<div class="card" style="background:#0f172a"><h3>平码第'+p+'位</h3><div class="balls" style="justify-content:center;gap:5px">';for(var i=0;i<3;i++)pg+='<span class="ball" style="width:34px;height:34px;font-size:.8rem;'+(i===0?'background:linear-gradient(135deg,#fbbf24,#d97706)':'')+'">'+t[i].n+'<small style="font-size:.45rem;display:block">'+t[i].s+'分</small></span>';pg+='</div></div>'}}
document.getElementById('posGrid').innerHTML=pg;

// Charts
var TC='#94a3b8',DG='#334155',bd=backtestData;
new Chart(document.getElementById('chartCR'),{{type:'bar',data:{{labels:crData.map(function(d){{return d.n}}),datasets:[{{data:crData.map(function(d){{return d.s}}),backgroundColor:crData.map(function(d,i){{return i<6?'#fbbf24':i<10?'#60a5fa':'#475569'}}),borderRadius:3}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:TC,font:{{size:9}}}},grid:{{color:DG}}}},y:{{ticks:{{color:TC}},grid:{{color:DG}},title:{{display:true,text:'轮转评分',color:TC}}}}}}}}}});
new Chart(document.getElementById('chartSpec'),{{type:'bar',data:{{labels:specData.map(function(d){{return d.n}}),datasets:[{{data:specData.map(function(d){{return d.s}}),backgroundColor:specData.map(function(d,i){{return i<3?'#3b82f6':i<6?'#60a5fa':'#475569'}}),borderRadius:3}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:TC,font:{{size:9}}}},grid:{{color:DG}}}},y:{{ticks:{{color:TC}},grid:{{color:DG}}}}}}}}}});
new Chart(document.getElementById('chartBacktest'),{{type:'bar',data:{{labels:bd.labels,datasets:[{{label:'综合Top6',data:bd.zh,backgroundColor:'#60a5fa',borderRadius:4}},{{label:'轮转Top6',data:bd.lz,backgroundColor:'#fbbf24',borderRadius:4}},{{label:'🔥并集Top10',data:bd.un,backgroundColor:'#34d399',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{position:'top',labels:{{color:TC,font:{{size:9}}}}}},title:{{display:true,text:'每期至少命中1个的覆盖率 (%)',color:TC,font:{{size:10}}}}}},scales:{{x:{{ticks:{{color:TC}}}},y:{{ticks:{{color:TC,callback:function(v){{return v+'%'}}}},grid:{{color:DG}},max:100}}}}}}}});
new Chart(document.getElementById('chartDist'),{{type:'bar',data:{{labels:['0/6','1/6','2/6','3/6'],datasets:[{{data:bd.dist,backgroundColor:['#f87171','#fb923c','#fbbf24','#34d399'],borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:TC}}}},y:{{ticks:{{color:TC}},grid:{{color:DG}}}}}}}}}});
new Chart(document.getElementById('chartCRR'),{{type:'bar',data:{{labels:crrData.map(function(d){{return d.n}}),datasets:[{{label:'轮转信号',data:crrData.map(function(d){{return d.c}}),backgroundColor:'#fde68a',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:TC}}}},y:{{ticks:{{color:TC}},grid:{{color:DG}}}}}}}}}});

// Special number hit rate chart
var sd=specBtData;
new Chart(document.getElementById('chartSpecHit'),{{type:'bar',data:{{labels:sd.labels,datasets:[{{label:'综合特码',data:sd.zh,backgroundColor:'#60a5fa',borderRadius:4}},{{label:'轮转特码',data:sd.lz,backgroundColor:'#fbbf24',borderRadius:4}},{{label:'🔥并集特码',data:sd.un,backgroundColor:'#34d399',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:true,plugins:{{legend:{{position:'top',labels:{{color:TC,font:{{size:9}}}}}},title:{{display:true,text:'特码Top6命中率 (%)',color:TC,font:{{size:10}}}}}},scales:{{x:{{ticks:{{color:TC}}}},y:{{ticks:{{color:TC,callback:function(v){{return v+'%'}}}},grid:{{color:DG}},max:100}}}}}}}});

// Tables
var ct='<tr><th>#</th><th>号</th><th>评分</th><th>遗漏</th><th>近30</th><th>加速</th><th>轮转信号</th></tr>';
for(var i=0;i<15;i++){{var d=crData[i];ct+='<tr><td class="rank">'+(i+1)+'</td><td class="num-cell">'+d.n+'</td><td class="score-cell">'+d.s.toFixed(1)+'</td><td>'+d.mis+'期</td><td>'+d.r30+'次</td><td>'+d.acc.toFixed(0)+'</td><td><span class="bar" style="width:'+(d.cr/100*45)+'px;background:#fde68a"></span>'+d.cr.toFixed(0)+'</td></tr>'}}
document.getElementById('tblCR').innerHTML=ct;

var st='<tr><th>#</th><th>号</th><th>生肖</th><th>评分</th><th>频次</th><th>遗漏</th><th>轮转</th></tr>';
for(var i=0;i<15;i++){{var d=specData[i];st+='<tr><td class="rank">'+(i+1)+'</td><td class="num-cell">'+d.n+'</td><td>'+d.z+'</td><td class="score-cell">'+d.s.toFixed(1)+'</td><td>'+d.fq.toFixed(0)+'</td><td>'+d.ms.toFixed(0)+'</td><td>'+d.cr.toFixed(0)+'</td></tr>'}}
document.getElementById('tblSpec').innerHTML=st;

// Zodiac grid
var zg='';
var maxCount=Math.max.apply(null,zodData.map(function(d){{return d.count}}));
for(var i=0;i<zodData.length;i++){{
  var d=zodData[i];
  var pct=(d.count/maxCount*100).toFixed(0);
  zg+='<div style="background:#1e293b;border-radius:8px;padding:8px;text-align:center;border:1px solid #334155">';
  zg+='<div style="font-size:1.2rem;font-weight:700;color:#fbbf24">'+d.name+'</div>';
  zg+='<div style="font-size:.65rem;color:#94a3b8">特码'+d.count+'次 | 最长漏'+d.miss+'期</div>';
  zg+='<div style="font-size:.7rem;color:#34d399;margin-top:2px">推荐: '+d.top+'</div>';
  zg+='<div style="height:4px;background:#334155;border-radius:2px;margin-top:4px"><div style="height:4px;width:'+pct+'%;background:#fbbf24;border-radius:2px"></div></div>';
  zg+='</div>';
}}
document.getElementById('zodiacGrid').innerHTML=zg;
</script>
</body>
</html>'''

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    return html

# ── 主入口 ────────────────────────────────────────────
def main():
    print("=" * 60)
    print("澳门六合彩 · 三策略对比模型 v3")
    print("=" * 60)

    print("\n[1/5] 加载数据...")
    draws = load_data(DATA_FILE)
    T = len(draws)
    print(f"  {T}期 ({draws[0]['date'][:10]} ~ {draws[-1]['date'][:10]})")

    print("\n[2/5] 计算统计与评分...")
    stats = compute_raw_stats(draws)
    rotation = rotation_signal(stats, T)

    # 优化后 (轮转)
    spec_scores = score_special(stats, rotation, T, draws)
    flat_scores, pos_scores = score_flat(stats, rotation, T)

    # 优化前 (综合)
    flat_old = score_flat_old(stats, T)
    spec_old = score_special_old(stats, T)

    # 集成特码
    spec_ensemble = score_special_ensemble(stats, rotation, T, 8)

    # 并集
    union10 = compute_union(flat_old, flat_scores, 10)
    union_s6 = compute_union(spec_old, spec_scores, 6)

    print("\n[3/5] 滚动回测 (最近111期, 3策略)...")
    bt, bt_old, bt_union = backtest(draws, 111)

    # 混合特码 + 三肖中特
    spec_hybrid = score_special_hybrid(stats, rotation, T, draws)
    ZO_NAMES = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
    zod = {z:{'freq':0,'r50':0,'last':-1} for z in ZO_NAMES}
    for i in range(T):
        z = ZODIAC.get(draws[i]['special'],'?')
        if z in zod: zod[z]['freq']+=1
        if i>=T-50 and z in zod: zod[z]['r50']+=1
        if z in zod: zod[z]['last']=i
    mx_f=max(v['freq'] for v in zod.values()) or 1
    mx_r=max(v['r50'] for v in zod.values()) or 1
    mx_m=max(T-1-v['last'] for v in zod.values()) or 1
    zod_sc={z:v['freq']/mx_f*50+v['r50']/mx_r*30+(T-1-v['last'])/mx_m*20 for z,v in zod.items()}
    sanxiao = [z for z,_ in sorted(zod_sc.items(),key=lambda x:x[1],reverse=True)[:3]]

    print("\n[4/5] 生成HTML看板...")
    build_html(draws, stats, flat_scores, spec_scores, rotation, pos_scores,
               bt, flat_old, spec_old, bt_old, bt_union, spec_ensemble)

    # 终端输出
    flat_top = sorted(flat_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    spec_top = sorted(spec_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    flat_o_top = sorted(flat_old.items(), key=lambda x: x[1]['total'], reverse=True)
    spec_o_top = sorted(spec_old.items(), key=lambda x: x[1]['total'], reverse=True)
    nxt = int(draws[-1]['issue']) + 1

    print("\n" + "=" * 60)
    print(f"🏆 预测 {nxt} 期 — 四策略对比")
    print("=" * 60)

    print("\n📊 策略1: 综合Top6 (优化前)")
    for i, (n, s) in enumerate(flat_o_top[:6], 1):
        print(f"  {i}. {n:02d} (评分:{s['total']:.1f})")
    print(f"  特码: {' '.join(f'{n:02d}' for n,_ in spec_o_top[:6])}")

    print("\n🔄 策略2: 动量Top6 (优化后)")
    for i, (n, s) in enumerate(flat_top[:6], 1):
        print(f"  {i}. {n:02d} (评分:{s['total']:.1f} 遗漏:{s['miss']}期 轮转:{s['rot']:.0f})")
    print(f"  特码: {' '.join(f'{n:02d}' for n,_ in spec_top[:6])}")

    print("\n🔥 策略3: 并集Top10 (推荐)")
    print(f"  平码: {' '.join(f'{n:02d}' for n in union10)}")
    print(f"  特码: {' '.join(f'{n:02d}' for n in union_s6)}")

    hyb_list = list(spec_hybrid.keys())
    print(f"\n🎯 策略4: 混合特码 (线性+三肖)")
    print(f"  特码Top8: {' '.join(f'{n:02d}' for n in hyb_list[:8])}")
    print(f"  来源: 线性Top4 ∪ 三肖({sanxiao[0]}/{sanxiao[1]}/{sanxiao[2]})筛选Top4")
    print(f"\n🐉 三肖中特: {' · '.join(f'{z}({zod_sc[z]:.0f}分)' for z in sanxiao)}")

    nb = len(bt)
    th_z = sum(r['fh'] for r in bt_old)
    th_l = sum(r['fh'] for r in bt)
    th_u = sum(r['fh'] for r in bt_union)
    print(f"\n📈 回测 ({nb}期): 综合{th_z/(nb*6)*100:.1f}% | 轮转{th_l/(nb*6)*100:.1f}% | 🔥并集{th_u/(nb*10)*100:.1f}%")
    print(f"\n✅ 完成! 打开 {OUTPUT_HTML}")

if __name__ == '__main__':
    main()
