# -*- coding: utf-8 -*-
"""每轮开奖后的"数据齐不齐"体检 + 出卡闸门。

为什么需要它 (2026-09-12 踩坑):
  引擎只要满足最低门槛(生肖≥2系统 / 号码≥3系统)就照常出卡、不报任何错,
  但卡会严重缩水 (255 实测: 号码层 6→4 系统, sx 为空, 整卡 24→10 码)。
  缩水卡和正常卡长得一模一样, 靠肉眼看不出来。
  更糟的是 gen_three_layer 会顺手写下 快照-{ISSUE}期.txt, 而快照守卫是
  "文件不存在才写" —— 一旦用残缺数据写下, 这个残缺状态就被【永久冻结】。

所以: 先体检, 齐了才允许跑引擎。

用法:
  python3 tools_check_round.py            # 只体检, 打印报告
  python3 tools_check_round.py --run      # 体检通过则跑引擎出卡
  python3 tools_check_round.py --pull     # 体检前先抓取增量 + 重建全集
"""
import os
import subprocess
import sys
import datetime

PROJ = '/Users/xiejinyu/macau-mark6'
GJ = '/tmp/guluyuan_js'
BJ = datetime.timezone(datetime.timedelta(hours=8))

# 每轮开奖时间 (北京). 过了这个点再抓取/出卡就会混入开奖后回填 = 前视污染。
DRAW = {
    255: datetime.datetime(2026, 9, 12, 21, 32, tzinfo=BJ),
    256: datetime.datetime(2026, 9, 13, 21, 32, tzinfo=BJ),
}

# 齐备标准 (对齐 254 的完整态)
MIN_ZW_SEATS = 3      # 生肖层白名单席位: 二国中特 / 左右二肖 / 红肖
MIN_NW_SYSTEMS = 6    # 号码层白名单系统数 (254 为 6; 255 缺数据时只有 4)

sys.path.insert(0, PROJ)
import gen_three_layer as g   # noqa: E402  (有 __main__ 守卫, import 不会跑出卡)


def ensure_scripts():
    """fetch/gen 脚本在 /tmp, 会被系统周期性清掉 — 缺了就从项目备份还原。"""
    pairs = [('fetch_safe.py', '工具备份_fetch_safe.py'),
             ('keyword_fill.py', '工具备份_keyword_fill.py'),
             ('gen_all.js', '工具备份_gen_all.js')]
    os.makedirs(GJ, exist_ok=True)
    for live, bak in pairs:
        lp, bp = os.path.join(GJ, live), os.path.join(PROJ, bak)
        if not os.path.exists(lp) and os.path.exists(bp):
            import shutil
            shutil.copy(bp, lp)
            print(f'  [还原] {live} ← {bak}')


def pull():
    """抓增量 + 重建全集。"""
    print(f'\n[{now_bj()}] 抓取增量 ...', flush=True)
    for name, args in [('主列表', ['fetch_safe.py']),
                       ('咕噜圆', ['keyword_fill.py', '咕噜圆']),
                       ('羊羊咩咩', ['keyword_fill.py', '羊羊咩咩'])]:
        r = subprocess.run([sys.executable] + args, cwd=GJ,
                           capture_output=True, text=True)
        tail = [l for l in r.stdout.strip().split('\n') if l][-1:] or ['(无输出)']
        print(f'  {name}: {tail[0]}', flush=True)
    print(f'[{now_bj()}] 重建全集 ...', flush=True)
    r = subprocess.run(['node', 'gen_all.js'], cwd=GJ, capture_output=True, text=True)
    for l in r.stdout.split('\n'):
        if l.startswith('已生成') or l.startswith('定义表行'):
            print('  ' + l, flush=True)


def now_bj():
    return datetime.datetime.now(BJ).strftime('%m-%d %H:%M')


def check(issue):
    """→ (是否齐备, 明细行列表, 引擎结果 dict 或 None)"""
    per = g.parse_zodiac()
    NS = g.parse_number()

    zw = {a: b for a, b in per.get(issue, {}).get('sys', {}).items()
          if a in g.ZW_LIST and 0 < len(b) < 10}
    nw = {a: b for a, b in NS.get(issue, {}).items() if a in g.NW_LIST}
    zl = g.zodiac_layer(per, issue)
    nl = g.number_layer(NS, issue)
    sx = g.sx_union(NS, issue)

    lines = []
    lines.append(f'  生肖层 白名单席位 {len(zw)}/{MIN_ZW_SEATS}: '
                 + (', '.join(sorted(zw)) or '无'))
    miss_zw = [a for a in g.ZW_LIST if a not in zw]
    if miss_zw:
        lines.append(f'      ❌ 缺: {", ".join(miss_zw)}')
    lines.append(f'  号码层 白名单系统 {len(nw)}/{MIN_NW_SYSTEMS}: '
                 + (', '.join(sorted(nw)) or '无'))
    miss_nw = [a for a in g.NW_LIST if a not in nw]
    if miss_nw:
        lines.append(f'      ❌ 缺: {", ".join(miss_nw)}')
    lines.append(f'  sx 三行双源交集: {len(sx)} 码'
                 + ('' if sx else '  ❌ 为空 —— 主力通道缺席, 卡必然缩水'))
    if zl is None:
        lines.append('  ❌ 生肖层不足(需≥2系统)')
    if nl is None:
        lines.append('  ❌ 号码层不足(需≥3系统)')

    ok = (len(zw) >= MIN_ZW_SEATS and len(nw) >= MIN_NW_SYSTEMS
          and len(sx) > 0 and zl is not None and nl is not None)
    return ok, lines, (per, NS)


def main():
    issue = int(sys.argv[sys.argv.index('--issue') + 1]) if '--issue' in sys.argv else None
    if issue is None:
        import csv
        with open(os.path.join(PROJ, 'macau_mark6_data.csv'), encoding='utf-8-sig') as f:
            last = [r for r in csv.reader(f) if r and len(r[0]) == 7 and r[0].isdigit()][-1]
        issue = int(last[0][-3:]) + 1

    print(f'══ {issue} 期 数据齐备体检 @ {now_bj()} 北京 ══')
    ensure_scripts()

    dl = DRAW.get(issue)
    if dl and datetime.datetime.now(BJ) >= dl:
        print(f'  ⛔ 已过开奖时间 {dl:%m-%d %H:%M}, 停止抓取/出卡 '
              f'(再跑会把开奖后回填混进快照 = 前视污染)')
        return 2

    if '--pull' in sys.argv:
        pull()

    ok, lines, _ = check(issue)
    print('\n'.join(lines))

    snap = f'{g.SNAP_DIR}/快照-{issue}期.txt'
    if os.path.exists(snap):
        print(f'  ℹ️  快照已存在, 不覆盖: {os.path.basename(snap)}')
    if ok:
        print(f'\n  ✅ {issue} 期数据齐备')
        if '--run' in sys.argv:
            print(f'  跑引擎出卡 ...')
            r = subprocess.run([sys.executable, 'gen_three_layer.py'], cwd=PROJ,
                               capture_output=True, text=True)
            for l in r.stdout.split('\n'):
                if l.startswith('★★') or '三层交集' in l and '码' in l:
                    print('  ' + l)
            print(f'  退出码 {r.returncode}; 完整输出见 local-{issue}-three-layer.txt')
        else:
            print('  (加 --run 可出卡)')
        return 0
    else:
        print(f'\n  ⏳ {issue} 期数据未齐 —— 不出卡 (避免写下残缺快照)')
        return 1


if __name__ == '__main__':
    sys.exit(main())
