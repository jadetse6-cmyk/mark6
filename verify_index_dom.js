// DOM-stub runner for index.html inline script — distinguishes "runtime JS error"
// (page blank in browser) from "page is fine, issue is elsewhere (cache/device)".
const fs = require('fs');
const vm = require('vm');

// 🔴 取源改用 mtime 守卫。原版无条件读 /tmp/js1.js —— 那个文件只有 tools_add_draw.py 在
//    调用本脚本【之前】才会刷新(它 122 行现抽、123 行现写),所以管线内是新鲜的;
//    但【单独手工跑】时 js1.js 往往是几天前甚至上一版页面的残留,本脚本会一字不差地
//    打印上次的结果,看起来"验收通过",实则验的是已经不存在的页面(记忆里记过这个坑)。
//    规则与 tools_add_draw.py 逐字一致 = 最长 <script> 块,保证两条路抽到同一份字节。
const INDEX = '/Users/xiejinyu/macau-mark6/index.html';
let src, srcFrom;
try {
  const st = fs.statSync('/tmp/js1.js');
  if (st.mtimeMs >= fs.statSync(INDEX).mtimeMs) { src = fs.readFileSync('/tmp/js1.js', 'utf8'); srcFrom = '/tmp/js1.js'; }
} catch (e) { /* js1.js 不存在 */ }
if (!src) {
  const disk = fs.readFileSync(INDEX, 'utf8');
  src = disk.match(/<script>([\s\S]*?)<\/script>/g).map(s => s.slice(8, -9)).reduce((a, b) => (a.length >= b.length ? a : b));
  srcFrom = 'index.html (现抽: /tmp/js1.js 缺失或比 index.html 旧)';
}
console.log('脚本源: ' + srcFrom);

const filledCount = new Map(); // id -> chars written via innerHTML/textContent
function makeEl(id) {
  const t = { id, innerHTML: '', textContent: '', style: {}, _touched: false };
  return new Proxy(t, {
    get(o, p) {
      if (p in o) return o[p];
      if (p === 'classList') return o.classList || (o.classList = { add() {}, remove() {}, contains() { return false; }, toggle() {} });
      if (p === 'getContext') return () => ({ canvas: null });
      if (p === 'appendChild' || p === 'addEventListener' || p === 'setAttribute' || p === 'removeChild' || p === 'insertBefore') return () => {};
      return undefined;
    },
    set(o, p, v) {
      if (p === 'innerHTML' || p === 'textContent') {
        o._touched = true;
        const prev = filledCount.get(id) || 0;
        filledCount.set(id, prev + String(v).length);
      }
      o[p] = v;
      return true;
    }
  });
}

const els = {};
const documentStub = {
  getElementById: (id) => els[id] || (els[id] = makeEl(id)),
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: () => makeEl('dyn'),
  documentElement: { style: {} },
  body: makeEl('body'),
  head: makeEl('head'),
  title: '',
  cookie: '',
};

class Chart {
  constructor() { Chart.instances.push(arguments.length); }
}
Chart.instances = [];
Chart.register = () => {};
Chart.defaults = {};

const sandbox = {
  window: new Proxy({ Chart, addEventListener() {}, localStorage: { getItem: () => null, setItem() {}, removeItem() {} } }, { get(o, p) { if (p in o) return o[p]; return undefined; } }),
  document: documentStub,
  Chart,
  console: { log() {}, warn() {}, error() {}, info() {} },
  navigator: {},
  location: { href: 'https://jadetse6-cmyk.github.io/mark6/' },
  setTimeout, clearTimeout, setInterval, clearInterval,
};
vm.createContext(sandbox);

try {
  vm.runInContext(src, sandbox, { filename: 'inline.js' });
  console.log('EVAL_OK');
} catch (e) {
  console.log('EVAL_THREW: ' + (e && e.message));
  console.log((e && e.stack ? e.stack.split('\n').slice(0, 8).join('\n') : String(e)));
}

const KEY = ['subtitle','curIssue','nextIssue','sanxiaoBalls','sanxiaoLabel','sanxiaoDetail',
  'trendV6','trendT10','trendOM','trendCold','zodiacGrid','posGrid',
  // ⚠️ 2026-10-02 用户删掉并集卡/核心9码两张球卡 ⇒ ovSpecUnion/ovSpecCore/unionLabel/coreLabel
  //    四个元素【已不存在】。故意不从这行删掉, 而是留在下面单列: 留在清单里它们会打印
  //    NEVER-TOUCHED, 那读起来像"页面坏了"; 彻底移除又会让它们悄悄复活时无人察觉。
  'ovSpecOM','ovSpecComp','ovSpecCold','ovSpec3Union',
  'ovBTTable','flatTable','specTableComp','specTableOM','specTableCold',
  'lx2','lx3','lx4','lx2rate','lx3rate','lx4rate','lianxiaoLabel',
  'btDetail','btSpecPeriod','btFlatDist'];
console.log('--- key elements ---');
for (const k of KEY) {
  const el = els[k];
  if (!el) { console.log(k + ' => NEVER-TOUCHED'); continue; }
  const s = (el.innerHTML || el.textContent || '').replace(/\s+/g, ' ').trim();
  console.log(k + ' => ' + (s.length ? 'len ' + s.length + ': ' + s.slice(0, 110) : '(empty)'));
}
// 反向断言: 上面四个已删元素若又被创建出来, 那是有人误加回来了 —— 明确报出来,
// 别让它以 NEVER-TOUCHED / 空元素的形式混过去。
const DELETED = ['ovSpecUnion', 'ovSpecCore', 'unionLabel', 'coreLabel'];
const revived = DELETED.filter(k => els[k]);
console.log('--- 已删元素(2026-10-02) ---');
console.log(revived.length ? '  🔴 又出现了: ' + revived.join(', ') + ' —— 用户已拍板删除, 是有人误加回来'
                          : '  ✅ ' + DELETED.join('/') + ' 均未复活');

const total = [...filledCount.values()].reduce((a, b) => a + b, 0);
console.log('--- summary ---');
console.log('elements created: ' + Object.keys(els).length);
console.log('chars written to innerHTML/textContent: ' + total);
console.log('charts instantiated: ' + Chart.instances.length);
