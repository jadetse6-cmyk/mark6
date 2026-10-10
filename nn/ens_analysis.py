#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合方式体检 —— 只用【已存下的成员分数】离线比较几种把 8 个成员合成一张卡的方式。

    python3 nn/ens_analysis.py [npz 路径]     # 默认 /tmp/nn8_20261005.npz

背景: 10-04/10-05 两次 8 种子跑分里, "集成"(概率平均) 在 top21 上比"成员均值"差
~10 个命中(311.0 vs 320.9), top14 上也差 ~3 个。集成比自己的成员还差在直觉上反常,
但 734 期的噪声本来就大 —— 这个脚本回答的就是"它到底是系统性的, 还是噪声"。

🔴 纪律:
  - 本脚本只读已存分数, 不训练、不碰 nn_signal_test.py 的登记口径。
  - "成员均值" = 8 个成员各自 top-K 命中率的平均(报表里就是这行), 不是一张卡;
    它是"不组合"的基准。任何组合方式要赢就该赢过它。
  - 事后在同一评估窗上挑赢家 = 选择效应。凡是这里选出来的东西, 只能先记成
    "描述性改进", 真证据要靠前瞻(记账)累积 —— 与 rotKeep 换代同一条规矩。
"""
import sys
import numpy as np

KS = (10, 14, 15, 20, 21, 22)
FOLDS = [(1000, 1100), (1100, 1200), (1200, 1300), (1300, 1400),
         (1400, 1500), (1500, 1600), (1600, 1734)]     # 与 nn_signal_test.py 一致
LO = FOLDS[0][0]

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/nn8_20261005.npz'
z = np.load(path)
M, E, tgt = z['members'], z['ens'], z['tgt']        # (S,T,49), (T,49), (T,) 号码 1..49
y = tgt - 1
S, T, _ = M.shape
assert T == FOLDS[-1][1] - LO, f'期数 {T} 与 FOLDS 区间 {FOLDS[-1][1]-LO} 对不上, 停'
print(f'成员 {S} 个 · 样本外 {T} 期 · 目标 {tgt[0]}..{tgt[-1]}  (npz: {path})')


def hit_period(scores, K):
    """→ (T,) bool: 该期 top-K 是否命中"""
    order = np.argsort(-scores, axis=1)
    return (order[:, :K] == y[:, None]).any(axis=1)


def line(name, hit, K):
    p = K / 49.0
    h, exp = int(hit.sum()), T * p
    zz = (h - exp) / np.sqrt(T * p * (1 - p))
    print(f'  {name:<14} {h:>4}/{T}   提升 {(h-exp)/exp*100:+6.1f}%   z={zz:+5.2f}')
    return h


# ── 各成员自己的命中率(基准) ──
mh = {K: np.stack([hit_period(M[s], K) for s in range(S)]) for K in KS}   # (S,T) bool

# ── 候选组合器 ──
# 1) prob-mean: npz 里存好的(softmax 概率平均) = 登记口径
# 2) rank-mean (Borda): 每个成员内部排名, 名次取平均 —— 对置信度标定完全不敏感
rank = np.stack([np.argsort(np.argsort(-M[s], axis=1), axis=1) for s in range(S)])  # 0=该成员眼里的最好
rank_mean = rank.mean(axis=0).astype(np.float64)
# 3) median-rank: 名次的中位数, 比均值更抗单个成员发疯
rank_med = np.median(rank, axis=0)


def vote_scores(K):
    """每个号被几个成员投进各自 top-K → 票数; 平票时用 rank_mean 破(K 相关组合器)"""
    v = np.zeros((T, 49), dtype=np.float64)
    for s in range(S):
        order = np.argsort(-M[s], axis=1)
        np.add.at(v, (np.arange(T)[:, None], order[:, :K]), 1.0)
    return v * 100.0 - rank_mean      # 票数为主, 名次破平


def line_mean(name, hm, K):
    """成员均值行: 命中数是【分数】(如 217.4) —— 8 个成员各自命中的平均, 不是一张卡。
    🔴 别拿它去 argsort(那是把"命中率"当打分用, 纯粹胡来)。"""
    p = K / 49.0
    h, exp = hm.sum() / S, T * p
    print(f'  {name:<14} {h:>6.1f}/{T}   提升 {(h-exp)/exp*100:+6.1f}%')


print('\n=== 各 K 对比 (提升 = 相对 期数×K/49) ===')
print(f'  [成员均值 = {S} 个成员各自命中的平均, 不是一张卡]')
for K in KS:
    print(f'── K={K} ──')
    line_mean('成员均值', mh[K], K)
    line('prob-mean', hit_period(E, K), K)
    line('rank-mean', hit_period(rank_mean, K), K)
    line('median-rank', hit_period(rank_med, K), K)
    line(f'投票(top{K})', hit_period(vote_scores(K), K), K)

# ── 集成 vs 成员均值: 配对差 + bootstrap ──
print('\n=== prob-mean 集成 − 成员均值: 配对差分解 ===')
rng = np.random.default_rng(20261005)
for K in (14, 21):
    base = mh[K].mean(axis=0) - K / 49.0              # 每期: 成员均值超额
    pe = hit_period(E, K).astype(float) - K / 49.0
    d = pe - base
    # 期级 bootstrap
    B = 2000
    idx = rng.integers(0, T, size=(B, T))
    dm = d[idx].mean(axis=1) * T                      # 换算成"命中数差"
    lo, hi = np.percentile(dm, [2.5, 97.5])
    pos = (dm > 0).mean()
    print(f'  K={K}: Δ命中 = {d.sum():+.1f}  (bootstrap 95% 区间 {lo:+.1f} .. {hi:+.1f}, '
          f'P(Δ>0)={pos:.2f})')
    seg = []
    for (a0, b0) in FOLDS:
        seg.append(d[a0 - LO:b0 - LO].sum())
    print(f'        分折 Δ: ' + '  '.join(f'{v:+.0f}' for v in seg)
          + f'   ({sum(v > 0 for v in seg)}/{len(seg)} 折为正)')
    h1, h2 = d[:T // 2].sum(), d[T // 2:].sum()
    print(f'        对半劈 Δ: 前 {h1:+.1f} / 后 {h2:+.1f}')

# ── 投票组合的稳定性: 分折 / 对半劈 / 配对 bootstrap ──
print('\n=== 投票组合 vs 基准 的稳定性 (配对差分解) ===')
for K in (14, 21):
    hv = hit_period(vote_scores(K), K).astype(float)
    hp = hit_period(E, K).astype(float)
    base = mh[K].mean(axis=0)                       # 每期成员均值命中率 (0..1)
    for name, cmp_ in (('投票 − prob-mean', hv - hp),
                       ('投票 − 成员均值', hv - base)):
        d = cmp_
        idx = rng.integers(0, T, size=(2000, T))
        dm = d[idx].mean(axis=1) * T
        lo, hi = np.percentile(dm, [2.5, 97.5])
        seg = [d[a0 - LO:b0 - LO].sum() for (a0, b0) in FOLDS]
        h1, h2 = d[:T // 2].sum(), d[T // 2:].sum()
        print(f'  K={K} {name}: Δ={d.sum():+.1f}  (95% {lo:+.1f}..{hi:+.1f}, P(Δ>0)={np.mean(dm>0):.2f})')
        print(f'        分折 ' + ' '.join(f'{v:+.0f}' for v in seg)
              + f'  ({sum(v > 0 for v in seg)}/{len(seg)} 正)   对半劈 {h1:+.1f} / {h2:+.1f}')

# ── 平票破法敏感性 + 与 prob-mean 卡面的重合度 ──
print('\n=== 投票组合的两个脆弱点 ===')
for K in (14, 21):
    v = np.zeros((T, 49))
    for s in range(S):
        order = np.argsort(-M[s], axis=1)
        np.add.at(v, (np.arange(T)[:, None], order[:, :K]), 1.0)
    h_rank = hit_period(v * 100.0 - rank_mean, K).sum()
    h_prob = hit_period(v * 100.0 + E, K).sum()
    o_v, o_p = np.argsort(-(v * 100.0 - rank_mean), axis=1)[:, :K], np.argsort(-E, axis=1)[:, :K]
    ov = np.mean([len(set(a) & set(b)) for a, b in zip(o_v, o_p)])
    print(f'  K={K}: 平票按名次破 {h_rank} vs 按概率破 {h_prob}   '
          f'(投票卡 ∩ prob卡 平均 {ov:.1f}/{K} 码)')

# ── 单成员拖累检查: 去掉一个成员后的 prob-mean ──
print('\n=== 去掉单个成员后 prob-mean 的命中 (K=21) ===')
full = hit_period(E, 21).sum()
print(f'  全 8 成员 {full}')
for s in range(S):
    sub = np.mean([np.exp((M[i] - M[i].max(1, keepdims=True))) /
                   np.exp((M[i] - M[i].max(1, keepdims=True))).sum(1, keepdims=True)
                   for i in range(S) if i != s], axis=0)
    h = hit_period(sub, 21).sum()
    print(f'  去成员{s}: {h}  (Δ {h-full:+d})')
