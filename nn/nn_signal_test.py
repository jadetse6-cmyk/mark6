#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""神经网络信号检验 —— 用 PyTorch 判【特码历史里到底有没有可学的结构】。

    python3 nn_signal_test.py                # 正常训练 + 测试
    python3 nn_signal_test.py --shuffle      # 对照: 打乱训练标签, 应该恰好回到随机
    python3 nn_signal_test.py --arch attn    # 换成 49 号之间有交互的注意力模型
    python3 nn_signal_test.py --seeds 8      # 多随机种子取平均

━━ 这个脚本回答什么 ━━
不是"能不能训出一个预测模型"(那当然能, 在训练集上能刷到 100%)。它回答的是:
**在【没见过的未来期】上, 神经网络能不能超过逐期随机基线, 以及能不能超过现有的
buildUnion 卡。** 前段训练 / 中段早停 / 末段只在最后测一次。

━━ 三条纪律 ━━
1. 🔴 零前视: ti 期的特征只用 draws[0..ti-1]。切分表在下面, 别改成全量。
2. 🔴 测试段只看一次。想调超参就调验证段, 调完不许回头再动测试段的结论 ——
   否则那个数字就是拟合出来的, 跟不看测试段没区别。
3. 🔴 `--shuffle` 对照必须跑。它把训练标签打乱(特征不变), 学不到任何真东西。
   若它也刷出提升 ⇒ 管线有泄漏, 整份结果作废。这是本脚本唯一自带的防静默出错闸门。

━━ 怎么读结果 ━━
看 "提升" 和 "z", 不看命中数。卡面大小不同的模型比命中数是没意义的
(21 码卡当然比 8 码卡中得多)。z 是相对【逐期随机期望 sum(K/49)】的标准化偏差。
"""

import json
import os
import hashlib
import argparse
import numpy as np
import torch
import torch.nn as nn

# 🔴 2026-10-03: 数据从写死的 /tmp/mk6_data.json 改成【本目录】的 nn_data.json。
#    原来那份是手工快照 + 放 /tmp, 没有任何脚本能重建 —— 系统清掉 /tmp 之后 NN 直接跑不了,
#    还查不出是谁删的(没人删)。现在由 nn/gen_nn_data.js 可复现地生成(走页面真实
#    buildUnionTrend, 带零前视自检)。
#
#    ⚠️ 这里【只定义路径, 不读文件】—— track_log.py 会 import 本模块, 模块级读文件
#       等于把记账链挂在数据文件上; 数据没了记账也跟着死, 那是不可接受的。
#       存在性检查放在 main() 里。
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(_HERE, 'nn_data.json')
REPO = os.path.dirname(_HERE)
HTML = os.path.join(REPO, 'index.html')

# 🔴 切分表(期号索引 ti, 不是期号)。改这里 = 改实验结论, 别随手动。
#
# 单一切分试过, 不够用: 测试段只 234 期, σ≈7.5 个命中(相对 ±7%), 而我们要找的
# 优势量级是 5% —— 那个窗口分辨不了 0 和 5%。改成【滚动前推】: 每个折都用严格更早的
# 数据训练, 预测接下来的 100 期。折之间首尾相接, 覆盖 1000 期之后全部 734 期。
# 训练量随折增长(900→1634), 与真实使用场景一致(越往后历史越多)。
FOLDS = [(1000, 1100), (1100, 1200), (1200, 1300), (1300, 1400),
         (1400, 1500), (1500, 1600), (1600, 1734)]
VAL_LEN = 100                # 每折切训练末尾 100 期做早停
TRAIN0 = 100                 # 前 100 期留给统计量, 不参与

# 报表口径 top-K。14 = 记账卡 `track_log.NN_TOPK[0]`。
# 🔴 2026-10-05: 这个集合曾在【两处】各写一份 —— 补了报表循环没补 eval_topk 的默认参数,
#    56 次训练全跑完、卡在打印段 KeyError: 14。一处定义, 多处引用。
KS_REPORT = (10, 14, 15, 20, 21, 22)


# ────────────────────────── 特征 ──────────────────────────
def build_features(d):
    """→ X[ti, n, F] 零前视特征, Y[ti] 真实特码。第 ti 期只用 draws[0..ti-1]。"""
    N = d['n']
    draws = d['draws']
    # S[ti, n] = 第 ti 期特码是不是 n;  F[ti, n] = n 是否出现在该期 6 个平码里
    S = np.zeros((N, 50), dtype=np.float32)
    F = np.zeros((N, 50), dtype=np.float32)
    for ti, rec in enumerate(draws):
        S[ti, rec['s']] = 1.0
        for x in rec['f']:
            F[ti, x] = 1.0

    # 累计频次(前缀和): cum[ti] = 前 ti 期的计数 ⇒ cum[ti] 天然零前视
    cumS = np.vstack([np.zeros((1, 50), np.float32), np.cumsum(S, axis=0)])
    cumF = np.vstack([np.zeros((1, 50), np.float32), np.cumsum(F, axis=0)])

    # 遗漏: 到 ti 期为止, 每个号最近一次出现的下标(没有则 -1)
    lastS = np.full((N + 1, 50), -1, dtype=np.int32)
    lastF = np.full((N + 1, 50), -1, dtype=np.int32)
    for ti in range(N):
        lastS[ti + 1] = lastS[ti]
        lastF[ti + 1] = lastF[ti]
        lastS[ti + 1, draws[ti]['s']] = ti
        for x in draws[ti]['f']:
            lastF[ti + 1, x] = ti

    feats = []
    for ti in range(N):
        t = ti                                     # 已见期数 = ti (下标 0..ti-1)
        ts = max(t, 1)
        cols = []
        for W in (30, 50, 100):
            lo = max(0, t - W)
            w = max(t - lo, 1)
            cols.append((cumS[t] - cumS[lo])[1:] / w)
            cols.append((cumF[t] - cumF[lo])[1:] / w)
        rate_s = cumS[t][1:] / ts                  # 特码历史频率
        rate_f = cumF[t][1:] / ts                  # 平码历史频率
        cols.append(rate_s)
        cols.append(rate_f)
        # 近 50 期频率 / 历史频率 = 相对冷热(现有模型的 rotationSignal 就是这个思路)
        cols.append((cumS[t] - cumS[max(0, t - 50)])[1:] / max(t - max(0, t - 50), 1)
                    / (rate_s + 1e-6))
        # 遗漏
        miss_s = np.where(lastS[t][1:] < 0, t, t - 1 - lastS[t][1:]).astype(np.float32)
        miss_f = np.where(lastF[t][1:] < 0, t, t - 1 - lastF[t][1:]).astype(np.float32)
        cols.append(miss_s / 49.0)
        cols.append(miss_f / 49.0)
        # 遗漏的横截面分位(在所有 49 个号里的相对深浅)
        cols.append(np.argsort(np.argsort(miss_s)).astype(np.float32) / 48.0)
        # 号码身份本身 —— 允许它学"哪个号吉利"。纯噪声拟合的口子, 故意留着:
        # 它是一个实践者真会加进去的特征, 而我们要测的就是这种自由度会不会泛化。
        cols.append(np.arange(1, 50, dtype=np.float32) / 49.0)
        feats.append(np.stack(cols, axis=1))
    X = np.stack(feats, axis=0)                    # (N, 49, F)
    return X, S, F


# ────────────────────────── 模型 ──────────────────────────
class Scorer(nn.Module):
    """49 号共享权重的打分器(置换等变) —— 每个号独立过同一个 MLP。"""

    def __init__(self, nf, hidden=64, depth=2, drop=0.2):
        super().__init__()
        layers, prev = [], nf
        for _ in range(depth):
            layers += [nn.Linear(prev, hidden), nn.ReLU(), nn.Dropout(drop)]
            prev = hidden
        layers += [nn.Linear(prev, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):                 # x: (B, 49, F) → (B, 49)
        return self.net(x).squeeze(-1)


class AttnScorer(nn.Module):
    """让 49 个号之间能交互的版本 —— 容量大得多, 更容易记住噪声。

    留它是因为"等变模型不行"不等于"神经网络不行"。要否证就得把大模型也试掉。
    """

    def __init__(self, nf, hidden=64, heads=4, blocks=2, drop=0.2):
        super().__init__()
        self.embed = nn.Linear(nf, hidden)
        layer = nn.TransformerEncoderLayer(hidden, heads, hidden * 2, drop,
                                           batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, blocks)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        return self.head(self.enc(self.embed(x))).squeeze(-1)


# ────────────────────────── 训练与评估 ──────────────────────────
def run(arch, X, y_idx, mu, sd, tr, va, seed, shuffle, epochs=300, bs=64, lr=2e-3,
        aux=None, aux_w=0.5):
    torch.manual_seed(seed)
    np.random.seed(seed)
    nf = X.shape[2]
    model = AttnScorer(nf) if arch == 'attn' else Scorer(nf)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    lossf = nn.CrossEntropyLoss()

    Xn = (X - mu) / sd
    Xtr = torch.tensor(Xn[tr[0]:tr[1]], dtype=torch.float32)
    ytr = torch.tensor(y_idx[tr[0]:tr[1]], dtype=torch.long)
    Xva = torch.tensor(Xn[va[0]:va[1]], dtype=torch.float32)
    yva = torch.tensor(y_idx[va[0]:va[1]], dtype=torch.long)

    # 辅助任务: 同时预测 6 个平码。每期从 1 个标签变 7 个 ⇒ 梯度信号 ×7。
    # 这是本实验里唯一的"大数据"手段 —— 外部数据不存在, 只能把同一期的数据榨干。
    Atr = Ava = None
    if aux is not None:
        Atr = torch.tensor(aux[tr[0]:tr[1]], dtype=torch.long)   # (T, 6) 平码-1
        Ava = torch.tensor(aux[va[0]:va[1]], dtype=torch.long)

    if shuffle:
        # 🔴 对照组: 把训练标签打乱。特征一个字没动, 但"哪一期开哪个号"的对应被切断。
        #    正常的管线在这里必须回到随机水平。若它还有提升 ⇒ 有泄漏。
        #
        # 🔴 验证标签也必须一起打乱。只打乱训练集的话, 早停仍在拿【真标签】挑
        #    "最会预测验证段的那个 epoch" —— 对照组于是偷偷拟合了验证段, 不再是零假设。
        #    (第一版就漏了这个, 跑出 +9.7% 的假提升。)
        g = torch.Generator().manual_seed(12345)
        ytr = ytr[torch.randperm(len(ytr), generator=g)]
        yva = yva[torch.randperm(len(yva), generator=g)]
        if Atr is not None:
            Atr = Atr[torch.randperm(len(Atr), generator=g)]

    def loss_of(logits, y, A):
        l = lossf(logits, y)
        if A is not None:
            l = l + aux_w * lossf(logits.unsqueeze(1).expand(-1, A.shape[1], -1).reshape(-1, 49),
                                  A.reshape(-1))
        return l

    best, best_state, bad = 1e9, None, 0
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr))
        for i in range(0, len(Xtr), bs):
            b = perm[i:i + bs]
            opt.zero_grad()
            loss = loss_of(model(Xtr[b]), ytr[b], None if Atr is None else Atr[b])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            # 早停只看主任务(特码) —— 这才是我们要预测的东西
            vl = lossf(model(Xva), yva).item()
        if vl < best - 1e-5:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= 25:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, Xn, best


def score_window(model, Xn, lo, hi):
    """→ 每期 49 个号的打分 (hi-lo, 49)"""
    with torch.no_grad():
        return model(torch.tensor(Xn[lo:hi], dtype=torch.float32)).numpy()


def softmax(x):
    """按行归一化成分数概率 —— 集成平均用(见 main 里为什么不用 logits)。"""
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)


def eval_topk(scores, s_true, ks=KS_REPORT):
    """→ {K: (命中数, 期数, 逐期随机期望, z)}

    🔴 断言两者长度一致。滚动前推是分段拼起来的, 段边界算错会导致分数与真值错位,
       而错位后的命中率照样是个"正常"的数 —— 不报错, 只是悄悄变成噪声(踩过)。
    """
    assert len(scores) == len(s_true), \
        '分数 %d 行 vs 真值 %d 期 —— 对不齐, 结果无意义' % (len(scores), len(s_true))
    out = {}
    order = np.argsort(-scores, axis=1)            # 分数降序 → 号下标
    for K in ks:
        pick = order[:, :K]                        # (T, K) 取的是 0..48 下标
        hit = (pick == (s_true - 1)[:, None]).any(axis=1)
        p = K / 49.0
        h, n = int(hit.sum()), len(hit)
        exp = n * p
        z = (h - exp) / np.sqrt(n * p * (1 - p))
        out[K] = (h, n, exp, z)
    return out


def eval_cards(cards, lo, hi, s_win):
    """现有 buildUnion 卡在同一批期上的表现(卡面大小逐期不同 → 逐期算基线)。

    🔴 s_win 必须是【已切好的窗口】s_true[lo:hi], 不是全量数组。
       第一版传的是全量 s_true 然后拿 s_true[ti-lo] 取, lo=1000 时读到的是第 0..733 期
       —— 1000 期以后的卡面在跟 2022 年的开奖比对。它不报错, 期望值照样对得上
       (卡面取自 cards, 与 s_true 无关), 只有命中数是错的, 于是"提升"看着很漂亮。
       这就是最典型的一类坑: 数字全都像模像样, 但跟真值错位。
    """
    assert len(s_win) == hi - lo, \
        '真值窗口 %d 期 vs 卡面区间 %d 期 —— 对不齐' % (len(s_win), hi - lo)
    h, exp, var, sizes = 0, 0.0, 0.0, []
    for ti in range(lo, hi):
        card = cards[str(ti)]
        k = len(card)
        sizes.append(k)
        ok = s_win[ti - lo] in card
        h += int(ok)
        exp += k / 49.0
        var += (k / 49.0) * (1 - k / 49.0)
    n = hi - lo
    return h, n, exp, (h - exp) / np.sqrt(var), float(np.mean(sizes))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shuffle', action='store_true', help='对照组: 打乱训练标签')
    ap.add_argument('--arch', choices=['mlp', 'attn'], default='mlp')
    ap.add_argument('--seeds', type=int, default=3)
    ap.add_argument('--epochs', type=int, default=300)
    ap.add_argument('--aux', action='store_true', help='辅助任务: 同时预测 6 个平码(样本×7)')
    ap.add_argument('--save', default=None, help='把每个成员的样本外分数存成 .npy')
    a = ap.parse_args()

    # 🔴 数据缺失就【硬失败】—— 绝不静默跑空。这份文件原来在 /tmp, 被系统清掉之后
    #    这里只会抛一个没头没尾的 FileNotFoundError, 看不出该做什么。
    if not os.path.exists(DATA):
        raise SystemExit(
            '🔴 数据文件不存在: %s\n'
            '   生成:  node nn/gen_nn_data.js   (走页面真实 buildUnionTrend, 自带零前视自检)\n'
            '   历史:  这份数据原来是 /tmp 下的手工快照, 全项目没有任何脚本能重建它;\n'
            '          2026-10-03 被系统清掉, NN 的 CLI 就此跑不了。别再手工放 /tmp。' % DATA)

    d = json.load(open(DATA))

    # 数据新不新: nn_data.json 里记着生成时的 index.html md5。对不上 = 页面改过、
    # 或又入库了新一期 ⇒ 结论可能已经过期。只警告不拦 —— 回测本来就允许用旧快照。
    _m = d.get('meta', {})
    _cur = hashlib.md5(open(HTML, 'rb').read()).hexdigest() if os.path.exists(HTML) else None
    print('数据 %s' % DATA)
    print('  生成于 %s   开奖 %s 期 (末条 %s)   index_md5 %s'
          % (_m.get('generated_at', '?'), _m.get('drawn_issues', '?'),
             _m.get('last_drawn', '?'), str(_m.get('index_md5'))[:12]))
    if _cur and _m.get('index_md5') and _cur != _m['index_md5']:
        print('  ⚠️ 与当前 index.html 不一致 (现 %s) —— 页面改过或已入库新一期。'
              % _cur[:12])
        print('     要跑最新数据: node nn/gen_nn_data.js')
    X, S, F = build_features(d)
    s_true = np.array([r['s'] for r in d['draws']])
    y_idx = s_true - 1
    cards = d['cards']
    nf = X.shape[2]
    # 平码标签: 每期 6 个 → (N, 6) 的 0-based 下标
    aux = np.array([[x - 1 for x in r['f']] for r in d['draws']], dtype=np.int64)
    aux = aux if a.aux else None

    lo_all, hi_all = FOLDS[0][0], FOLDS[-1][1]
    n_eval = hi_all - lo_all
    print('特征 %d 维   滚动前推 %d 折   评估区间 ti %d..%d (%d 期全部为样本外)'
          % (nf, len(FOLDS), lo_all, hi_all - 1, n_eval))
    print('架构 %s%s  种子 %d'
          % (a.arch, '  🔴对照组(训练+验证标签均已打乱)' if a.shuffle else '', a.seeds))
    print()

    # 折在外、种子在内: 同一折的 N 个成员在【同一份训练数据】上各自随机初始化训练,
    # 分数在折内平均 → 集成分数。折之间首尾相接拼成整条样本外序列。
    per_seed = [{'sc': []} for _ in range(a.seeds)]
    ens_sc = []
    for (a0, b0) in FOLDS:
        tr = (TRAIN0, a0 - VAL_LEN)
        va = (a0 - VAL_LEN, a0)
        # 标准化统计量【每折各算各的】, 只用该折的训练段 —— 用全量会漏后段信息
        mu = X[tr[0]:tr[1]].reshape(-1, nf).mean(0)
        sd = X[tr[0]:tr[1]].reshape(-1, nf).std(0) + 1e-6
        fold = []
        for seed in range(a.seeds):
            model, Xn, _ = run(a.arch, X, y_idx, mu, sd, tr, va, seed,
                               a.shuffle, epochs=a.epochs, aux=aux)
            s = score_window(model, Xn, a0, b0)
            per_seed[seed]['sc'].append(s)
            fold.append(s)
        # 🔴 集成平均的是【softmax 概率】, 不是 logits。成员的置信度标定各不相同,
        #    平均 logits 会被某个"特别自信"的成员带跑; 概率平均对每个成员一视同仁。
        ens_sc.append(np.mean([softmax(s) for s in fold], axis=0))

    tgt = np.concatenate([s_true[x:y] for x, y in FOLDS])
    if a.save:
        # 存下每个成员的逐期分数 —— 事后要查"集成比成员差"到底是噪声还是并列打破的
        # 系统性偏差, 没有这个就只能干猜(刚吃过这个亏)。
        np.savez(a.save,
                 members=np.stack([np.concatenate(p['sc'], axis=0) for p in per_seed]),
                 ens=np.concatenate(ens_sc, axis=0), tgt=tgt)
    acc = {K: [] for K in KS_REPORT}   # 🔴 口径定义在文件头, 别在这再写一份(2026-10-05 漏改崩过)
    for seed in range(a.seeds):
        r = eval_topk(np.concatenate(per_seed[seed]['sc'], axis=0), tgt)
        for K in acc:
            acc[K].append(r[K])
        print('  成员 %d     样本外 top21: %d/%d   提升 %+.1f%%   z=%.2f'
              % (seed, r[21][0], r[21][1],
                 (r[21][0] - r[21][2]) / r[21][2] * 100, r[21][3]))
    r_ens = eval_topk(np.concatenate(ens_sc, axis=0), tgt)

    print()
    print('=== 样本外汇总 (ti %d..%d, %d 期) ===' % (lo_all, hi_all - 1, n_eval))
    h, n, exp, z, avgk = eval_cards(cards, lo_all, hi_all, s_true[lo_all:hi_all])
    print('  %-16s 命中 %4d/%d   随机 %6.1f   提升 %+6.1f%%   z=%5.2f   (卡面 %.1f 码)'
          % ('buildUnion 卡', h, n, exp, (h - exp) / exp * 100, z, avgk))
    for K in sorted(acc):
        hs = [x[0] for x in acc[K]]
        e = acc[K][0][2]
        print('  %-16s 命中 %6.1f/%d   随机 %6.1f   提升 %+6.1f%%   (top%d, %d成员均值)'
              % ('神经网络·成员', np.mean(hs), n, e, (np.mean(hs) - e) / e * 100, K, a.seeds))
    eh, eexp = r_ens[21][0], r_ens[21][2]
    print('  %-16s 命中 %6.1f/%d   随机 %6.1f   提升 %+6.1f%%   z=%5.2f   (top21, %d成员集成)'
          % ('神经网络·集成', eh, n, eexp, (eh - eexp) / eexp * 100,
             r_ens[21][3], a.seeds))

    # 🔴 功效说明: 这个数据集能分辨多大的优势? 不写出来就会把"没测出"误读成"不存在"。
    p = 0.4286
    need = (1.96 + 0.84) ** 2 * p * (1 - p) / (0.05 * p) ** 2
    print()
    print('  功效: 要在 α=0.05/80%% 功效下测出【相对 +5%%】的优势, 需约 %.0f 期;' % need)
    print('        本区间只有 %d 期 ⇒ 真存在 5%% 优势也大概率测不出来(不算"证明没有")。' % n_eval)


if __name__ == '__main__':
    main()
