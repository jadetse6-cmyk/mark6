#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正对照 —— 往历史里植入【已知可学】的规则, 看标准管线会不会当场学会。

    python3 nn/learn_curve.py --q 0.1 --seeds 8 \
        --save nn/runs/lc_plant10_20261010.npz --log-curves nn/runs/lc_plant10_curves_20261010.npz

植入规则: 每期以概率 q 把特码换成【当时特码遗漏最深】的号(平手取最小号), 其余期保留原开奖。
- 零前视: 选号只看 draws[0..ti-1]。特征里 miss_s/49 与遗漏横截面分位两列能把"最深遗漏"
  排出来 ⇒ 单调打分即可学会 —— 这是给管线出的一道【必答对】的题。
- q=0 时数据一字不改 ⇒ 应与 nn8_aux_ext_20261007.npz 的对应成员逐位一致(免费自检)。
- 完美学习的理论上限(top14): q=0.5 → +125% / 0.1 → +25% / 0.05 → +12.5% / 0.02 → +5.0%。
  实测从哪一档开始显著, 就是此前所有"不显著"读数的【检测下限收据】。

口径与 nn_signal_test.py 完全一致(同一 build_features / 同一 run() / 同一 ext 14 折 /
aux=平码头 / epochs=300 / 早停 patience=25), 唯一区别 = 训练标签 s 换成植入序列。
不新增任何自由参数; 全程不碰登记路径。
"""
import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import nn_signal_test as T  # noqa: E402
import run_ext_window     # noqa: E402,F401  import 时即把 T.FOLDS 扩成 14 折(自带连续性自检)


def plant_s(draws, q, seed):
    """→ (植入后的 s 数组, 实际换掉的期数, 规则被满足的期数)。

    平手取最小号; ti=0 无历史, 保留原开奖。历史按【植入后】的序列走 ——
    这才是一个"规则真实存在"的世界(特征由植入序列重建)。
    """
    rng = np.random.default_rng(seed)
    last = np.full(50, -1, dtype=np.int64)
    out = np.empty(len(draws), dtype=np.int64)
    n_plant, n_rule = 0, 0
    for ti, rec in enumerate(draws):
        if ti == 0:
            out[ti] = rec['s']
        else:
            miss = np.where(last < 0, ti, ti - 1 - last)
            tgt = int(np.argmax(miss[1:])) + 1        # 1..49
            if rng.random() < q:
                out[ti] = tgt
                n_plant += 1
            else:
                out[ti] = rec['s']
            n_rule += int(out[ti] == tgt)
        last[out[ti]] = ti
    return out, n_plant, n_rule


def oracle_lift(q, K):
    """完美学会该规则时, top-K 命中率相对随机的提升(解析): 假设打分把"最深遗漏"排到最前,
    该号必在前 K 内 ⇒ 命中率 = P(开奖=该号) + P(≠)·(K-1)/48。"""
    p_tgt = q + (1 - q) / 49.0
    p = p_tgt + (1 - p_tgt) * (K - 1) / 48.0
    return p / (K / 49.0) - 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--q', type=float, default=0.1, help='植入概率(0=数据不变, 自检用)')
    ap.add_argument('--seeds', type=int, default=8)
    ap.add_argument('--epochs', type=int, default=300)
    ap.add_argument('--plant-seed', type=int, default=20261010,
                    help='植入抽签的固定随机种子(可复现)')
    ap.add_argument('--save', default=None)
    ap.add_argument('--log-curves', default=None)
    a = ap.parse_args()

    d = json.load(open(T.DATA))
    draws = [dict(r) for r in d['draws']]
    s_plant, n_plant, n_rule = plant_s(draws, a.q, a.plant_seed)
    for r, s in zip(draws, s_plant):
        r['s'] = int(s)
    d2 = {'n': d['n'], 'draws': draws}

    X, _S, _F = T.build_features(d2)
    y_idx = s_plant - 1
    aux = np.array([[x - 1 for x in r['f']] for r in draws], dtype=np.int64)
    nf = X.shape[2]

    lo_all, hi_all = T.FOLDS[0][0], T.FOLDS[-1][1]
    print('正对照: q=%.4g  植入 %d/%d 期  规则被满足 %d 期 (理论 %.0f, 含"原开奖恰好就是它")'
          % (a.q, n_plant, len(draws) - 1, n_rule, a.q * (len(draws) - 1) + (1 - a.q) * (len(draws) - 1) / 49))
    print('特征 %d 维   ext %d 折   评估区间 ti %d..%d (%d 期)'
          % (nf, len(T.FOLDS), lo_all, hi_all - 1, hi_all - lo_all))
    print('理论上限(完美学习): top14 %+.1f%%   top21 %+.1f%%'
          % (oracle_lift(a.q, 14) * 100, oracle_lift(a.q, 21) * 100))
    print()

    per_seed = [{'sc': []} for _ in range(a.seeds)]
    ens_sc = []
    curve_logs = []
    for fi, (a0, b0) in enumerate(T.FOLDS):
        tr = (T.TRAIN0, a0 - T.VAL_LEN)
        va = (a0 - T.VAL_LEN, a0)
        mu = X[tr[0]:tr[1]].reshape(-1, nf).mean(0)
        sd = X[tr[0]:tr[1]].reshape(-1, nf).std(0) + 1e-6
        fold = []
        for seed in range(a.seeds):
            lg = {'curve': [], 'fi': fi, 'seed': seed}
            model, Xn, _ = T.run('mlp', X, y_idx, mu, sd, tr, va, seed,
                                 False, epochs=a.epochs, aux=aux, log=lg)
            curve_logs.append(lg)
            s = T.score_window(model, Xn, a0, b0)
            per_seed[seed]['sc'].append(s)
            fold.append(s)
        ens_sc.append(np.mean([T.softmax(s) for s in fold], axis=0))

    tgt = np.concatenate([s_plant[x:y] for x, y in T.FOLDS])
    if a.save:
        np.savez(a.save,
                 members=np.stack([np.concatenate(p['sc'], axis=0) for p in per_seed]),
                 ens=np.concatenate(ens_sc, axis=0), tgt=tgt)
    if a.log_curves:
        np.savez(a.log_curves, **T.pack_curves(curve_logs, T.FOLDS, a.seeds, a.epochs))
        print('学习曲线已存 %s' % a.log_curves)

    for seed in range(a.seeds):
        r = T.eval_topk(np.concatenate(per_seed[seed]['sc'], axis=0), tgt)
        print('  成员 %d  样本外 top14: %d/%d 提升 %+.1f%% z=%+.2f | top21: %d/%d 提升 %+.1f%% z=%+.2f'
              % (seed, r[14][0], r[14][1], (r[14][0] - r[14][2]) / r[14][2] * 100, r[14][3],
                 r[21][0], r[21][1], (r[21][0] - r[21][2]) / r[21][2] * 100, r[21][3]))
    r_ens = T.eval_topk(np.concatenate(ens_sc, axis=0), tgt)
    print()
    print('=== 集成 (ti %d..%d, %d 期) ===' % (lo_all, hi_all - 1, hi_all - lo_all))
    for K in (14, 21):
        h, n, e, z = r_ens[K]
        print('  top%d: %d/%d  随机 %.1f  提升 %+.1f%%  z=%+.2f'
              % (K, h, n, e, (h - e) / e * 100, z))


if __name__ == '__main__':
    main()
