// NN 数据生成器 —— 给 nn_signal_test.py 供数。 跑法: node nn/gen_nn_data.js
//
// 产出 nn/nn_data.json = { meta, n, draws, cards }
//   draws = 页面 DRAWS 原样(期号 i / 特码 s / 六个平码 f)
//   cards = { 期索引 ti: [号码...] } —— 逐期调【页面真实 buildUnionTrend(ti)】重建
//
// 🔴 为什么要这个文件(2026-10-03):
//    原来 nn_signal_test.py 读写死的 /tmp/mk6_data.json, 那文件是【手工快照】——
//    全项目(含归档)没有任何脚本能生成它, 而且放 /tmp 会被系统清掉。结果: 文件没了,
//    NN 的 CLI 直接跑不了, 还查不出是谁删的(没人删, 是 /tmp 自己清的)。
//    数据从此放项目里 + 由本脚本可复现地生成。
//
// 🔴 三条纪律(与 track_dump.js 同源, 别破):
//   1. 绝不重实现 buildUnionTrend / rotKeep / buildLanes —— 那就是第二份迟早漂移的副本。
//      全程在 vm 里跑 index.html 的【真实内联脚本】, 只读它算出来的结果。
//   2. 零前视必须【实测】, 不能靠读代码相信。生成前抽若干 ti, 把 DRAWS 截断到 ti 重算一遍,
//      与全量重算逐位比对 —— 不等就停。(代码上 buildLanes 是 DRAWS.slice(0,ti)、
//      rotKeep 窗口是 [ti-W, ti-1], 看着是干净的; 但"看着干净"不是证据。)
//   3. 取不到就【硬失败】, 绝不 `|| []` 兜底 —— 静默生成一张空卡比不生成更糟。
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const crypto = require('crypto');

const HTML = '/Users/xiejinyu/macau-mark6/index.html';
const OUT = path.join(__dirname, 'nn_data.json');

const src = fs.readFileSync(HTML, 'utf8');
const i = src.indexOf('<script>', src.indexOf('<script src=')) + 8;
const body = src.slice(i, src.lastIndexOf('</script>'));
const md5 = crypto.createHash('md5').update(src, 'utf8').digest('hex');

// ── 页面加载桩(照抄 track_dump.js: DOM 全代理掉, 页面脚本跑得动就行) ──────────
const els = {};
const mk = (id) => new Proxy({ id, innerHTML: '', textContent: '', style: {} }, {
  get(o, p) {
    if (p in o) return o[p];
    if (p === 'classList') return { add() {}, remove() {}, contains: () => false, toggle() {} };
    if (p === 'getContext') return () => ({ canvas: null });
    return () => {};
  },
  set(o, p, v) { o[p] = v; return true; }
});
const Chart = function () {}; Chart.register = () => {}; Chart.defaults = {};
const sb = {
  window: new Proxy({ Chart, addEventListener() {}, localStorage: { getItem: () => null, setItem() {}, removeItem() {} } },
    { get: (o, p) => (p in o ? o[p] : undefined) }),
  document: {
    getElementById: id => els[id] || (els[id] = mk(id)),
    querySelectorAll: () => [], querySelector: () => null, createElement: () => mk('dyn'),
    documentElement: { style: {} }, body: mk('body'), head: mk('head'), title: '', cookie: ''
  },
  Chart, console: { log() {}, warn() {}, error() {}, info() {} },
  navigator: {}, location: { href: 'x' }, setTimeout, clearTimeout, setInterval, clearInterval
};
vm.createContext(sb);
vm.runInContext(body, sb, { filename: 'inline.js' });

// ── 取数 ─────────────────────────────────────────────────────────────────────
const D = sb.DRAWS;
if (!Array.isArray(D) || !D.length) { console.error('🔴 页面 DRAWS 取不到, 停'); process.exit(2); }
if (typeof sb.buildUnionTrend !== 'function') {
  console.error('🔴 页面里没有 buildUnionTrend —— 卡面函数被改名/删了, 停'); process.exit(2);
}
const T = D.length;
const FULL_DRAWS = D.slice();
const FULL_T = sb.T;

const t0 = Date.now();
sb.buildUnionTrend(1);                       // 预热: 逼 trendHist 建一次全量缓存
const warmMs = Date.now() - t0;
console.error(`  页面加载完成: ${T} 期, trendHist 预热 ${warmMs}ms`);

// ── 自检: 零前视(截断 DRAWS 重算, 必须逐位一致) ───────────────────────────────
// 截断后要同时重置 T 与 _TH(trendHist 的唯一缓存), 否则算的是旧缓存。
const withTruncated = (ti, fn) => {
  sb.DRAWS = FULL_DRAWS.slice(0, ti);
  sb.T = ti;
  sb._TH = null;
  try { return fn(); } finally {
    sb.DRAWS = FULL_DRAWS; sb.T = FULL_T; sb._TH = null;
  }
};
const eqArr = (a, b) => a.length === b.length && a.every((x, k) => x === b[k]);
const SAMPLES = [150, 600, 1000, 1300, 1600, T - 1].filter(x => x > 1 && x <= T);
const checked = [];
for (const ti of SAMPLES) {
  const full = sb.buildUnionTrend(ti);
  const trunc = withTruncated(ti, () => sb.buildUnionTrend(ti));
  if (!eqArr(full, trunc)) {
    console.error(`🔴 前视污染: ti=${ti} 全量算出 ${JSON.stringify(full)}\n`
      + `              截断到 ${ti} 期算出 ${JSON.stringify(trunc)}\n`
      + `   —— 卡面用到了 ti 之后的数据, 这份数据不能给 NN 用, 停。`);
    process.exit(2);
  }
  checked.push(ti);
}
console.error(`  ✅ 零前视自检通过 (${checked.length} 个抽样: ${checked.join(', ')})`);

// ── 生成全部卡面 ─────────────────────────────────────────────────────────────
// ti = 期索引(0-based), buildUnionTrend(ti) 预测的是 DRAWS[ti]。最末条 DRAWS[T-1] 已开奖,
// 所以 ti 取 [1, T-1] —— ti=T 是"待预测"那期, 没有真值, NN 的折区间(FOLDS)也只到 T-1。
// 空数组是【合法】的: 现行 rotKeep 在近 W 期三条车道 lift 全 ≤0 时就该空卡, 照存不跳过。
const cards = {};
let empties = 0, minK = Infinity, maxK = 0, sumK = 0;
for (let ti = 1; ti <= T - 1; ti++) {
  const card = sb.buildUnionTrend(ti);
  if (!Array.isArray(card)) {
    console.error(`🔴 buildUnionTrend(${ti}) 返回的不是数组(拿到 ${typeof card}), 停`); process.exit(2);
  }
  for (const n of card) {
    if (!Number.isInteger(n) || n < 1 || n > 49) {
      console.error(`🔴 ti=${ti} 的卡面里有非法号码 ${n}, 停`); process.exit(2);
    }
  }
  if (card.length === 0) empties++;
  else { minK = Math.min(minK, card.length); maxK = Math.max(maxK, card.length); sumK += card.length; }
  cards[ti] = card;
}
const nonEmpty = T - 1 - empties;

const out = {
  meta: {
    generated_at: new Date().toISOString(),
    generator: 'nn/gen_nn_data.js',
    index_html: HTML,
    index_md5: md5,
    drawn_issues: T,
    last_drawn: String(D[T - 1].i),
    cards_range: [1, T - 1],
    cards_stats: {
      empty: empties, empty_pct: +(100 * empties / (T - 1)).toFixed(2),
      min: minK === Infinity ? 0 : minK, max: maxK,
      mean: nonEmpty ? +(sumK / nonEmpty).toFixed(2) : 0
    },
    lookahead_check: { ok: true, truncated_rerun_samples: checked }
  },
  n: T,
  draws: D.map(r => ({ i: String(r.i), s: r.s, f: r.f })),
  cards
};
fs.writeFileSync(OUT, JSON.stringify(out));
console.error(`  ✅ 写出 ${OUT}`);
console.error(`     开奖 ${T} 期 (末条 ${out.meta.last_drawn})  卡面 ${T - 1} 张: `
  + `空卡 ${empties} (${out.meta.cards_stats.empty_pct}%)  非空均 ${out.meta.cards_stats.mean} 码 `
  + `(min ${minK} / max ${maxK})`);
console.error(`     index.html md5 ${md5}`);
