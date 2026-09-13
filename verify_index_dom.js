// DOM-stub runner for index.html inline script — distinguishes "runtime JS error"
// (page blank in browser) from "page is fine, issue is elsewhere (cache/device)".
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('/tmp/js1.js', 'utf8');

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
  'ovSpecOM','ovBTTable','flatTable','specTableComp','specTableOM','specTableCold',
  'lx2','lx3','lx4','lx2rate','lx3rate','lx4rate','lianxiaoLabel',
  'btDetail','btSpecPeriod','btFlatDist'];
console.log('--- key elements ---');
for (const k of KEY) {
  const el = els[k];
  if (!el) { console.log(k + ' => NEVER-TOUCHED'); continue; }
  const s = (el.innerHTML || el.textContent || '').replace(/\s+/g, ' ').trim();
  console.log(k + ' => ' + (s.length ? 'len ' + s.length + ': ' + s.slice(0, 110) : '(empty)'));
}
const total = [...filledCount.values()].reduce((a, b) => a + b, 0);
console.log('--- summary ---');
console.log('elements created: ' + Object.keys(els).length);
console.log('chars written to innerHTML/textContent: ' + total);
console.log('charts instantiated: ' + Chart.instances.length);
