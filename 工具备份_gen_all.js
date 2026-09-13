// 生成 咕噜圆预测资料全集.txt:咕噜圆全部 + 文孙爱打飞机全部(所有类别),不删任何行,完全相同才去重
const fs = require('fs');

// 类别总表(长度降序匹配;含装饰变体经 DECOR 归一化后匹配)
const CATS = ['三个半头数', '特码输尽光', '顶级一肖', '三行中特', '绝杀三肖', '天地中特', '文武中特', '笔墨纸砚',
  '左右二肖', '二国中特', '琴棋书画', '东南西北', '头数中特', '精选三头', '规律大小', '内幕四肖', '汉奸', '杀三尾',
  '平特一尾', '平特⑧码', '平特六码', '平特一肖', '绝杀一头', '绝杀二头', '绝杀半波', '绝杀半头', '绝杀一段', '绝杀一合',
  '四头必中', '大小中特', '吉美凶丑', '单双中特', '必中单双', '最稳单双', '三半单双', '免费4尾', '强杀一肖', '龙哥六肖',
  '霸气七尾', '六肖中特', '五尾中特', '头数单双', '精杀四肖', '八尾中特', '一波中特', '内幕五肖', '四肖中特', '四季中特',
  '绝世家野', '四段必中', '七尾中特', '肉菜草肖', '单笔双笔', '风雨雷电', '尾大尾小', '单头双头', '五肖中特', '文肖武肖',
  '男女中特', '家野中特', '右左中特', '双波中特', '必杀三尾', '公式家野', '发财四头', '家禽野兽', '中特②头', '稳三半头',
  '三半波色', '左右中特', '天肖地肖', '二头中特', '七肖中特', '财富家野', '至尊四肖', '前后中特', '尾数大小', '归依四肖',
  '大神三头', '合单合双', '三段中奖', '精准天地', '三字平特', '神算四尾', '七合中特', '招财六肖', '段数中特', '四段特码',
  '必中⑩码', '玄机24码', '24码财富', '24码必中', '20码中特', '12码中特', '内幕八码', '内幕16码', '五肖五码', '必解⑧合',
  '绝版七尾', '九肖中特', '平⑥必中', '家禽', '野兽', '单尾', '双尾', '五肖', '四肖', '三肖', '六肖', '二肖', '一肖',
  '红肖', '绿肖', '蓝肖', '单双', '男女', '七肖', '九肖',
  // 羊羊咩咩 + 圈数字类别
  '绝杀①头', '绝杀⑤尾', '中特②头', '黑白六肖', '六肖六码', '绝杀七码', '绝杀三尾', '绝杀半单双', '笔墨纸砚肖', '五行中特',
  // 其他补充(必中波色/两波中特/绝杀一行/杀一行/两头中特/必开)
  '必中波色', '两波中特', '绝杀一行', '杀一行', '两头中特', '必开', '绝杀一肖', '精杀一肖', '稳杀十码', '杀两合',
  // 08-27 新增
  '精选双波', '五不中', '极限尾数', '单笔双笔'];

const DEF_RE = /(文臣|武将|笔肖|墨肖|纸肖|砚肖|左肖|右肖|吴国|蜀国|魏国|琴肖|棋肖|书肖|画肖|东肖|南肖|西肖|北肖|天肖|地肖|家禽|野兽|汉奸|红肖|绿肖|蓝肖|前肖|后肖|五行|单笔|双笔)/;
// 期号开头:第?XXX期 或 XXX+空格(239 极限尾数)
const isPred = l => /^第?\d{3}(期|期?[\s:：])/.test(l);
const isDef = l => DEF_RE.test(l) && !isPred(l);
const isAux = l => !isPred(l) && !isDef(l) && !/^\s*$/.test(l);

// 装饰符号:不影响内容,统一去掉用于类别识别(输出时 normBrackets 再统一括号)
// 注意:圈数字①②③ 保留(是中特②头、绝杀①头、必中⑩码 等类别名的一部分)
const DECOR = /[★☯△▽☀←→々*↑↓❀☁〖〗◇＊×╳✿☾☽«»≮≯]/gu;

// 行首别名 → 标准类别(羊羊咩咩/文孙同类不同名的系列)
const ALIAS = [
  ['天地生肖', '天地中特'], ['文武生肖', '文武中特'], ['文肖武肖', '文武中特'],
  ['肥瘦生肖', '肥瘦生肖'], ['有无生肖', '有无生肖'], ['阴阳生肖', '阴阳生肖'],
  ['四季生肖', '四季生肖'], ['肉草菜肖', '肉草菜肖'], ['肉菜肖', '肉草菜肖'], ['肉草肖', '肉草菜肖'], ['草肉肖', '肉草菜肖'], ['草菜肖', '肉草菜肖'],
  ['本期买', '本期买'], ['三头中特', '三头中特'], ['澳合数', '合数'], ['黑白六肖', '黑白六肖'], ['六肖六码', '六肖六码'],
];

const inferCat = line => {
  const pre = line.replace(/^第?(\d{3})期?[\s:：]?\s*/, '');
  const cleaned = pre.replace(DECOR, '').replace(/^（[一-龥]{2,8}）/u, m => m.slice(1, -1));
  // 特殊格式优先:尾拖尾(★一尾→拖28尾)
  const t = cleaned.match(/^[一二三四五]尾→拖\d{2}尾/);
  if (t) return '尾拖尾';
  // 旧格式:第XXX期 天肖天肖天肖 / 地肖地肖地肖 → 天地中特
  if (/^([天地]肖)\1\1/.test(cleaned)) return '天地中特';
  for (const [kw, cat] of [...ALIAS].sort((a, b) => b[0].length - a[0].length))
    if (cleaned.startsWith(kw)) return cat;
  for (const c of [...CATS].sort((a, b) => b.length - a.length))
    if (cleaned.startsWith(c) || cleaned.includes(c)) return c;
  if (/^单\([一-龥]{3,4}\)双\([一-龥]{3,4}\)/.test(cleaned)) return '单双';
  if (/^男\([一-龥]{3,4}\)女\([一-龥]{3,4}\)/.test(cleaned)) return '男女';
  if (/单【/.test(cleaned) && /双【/.test(cleaned)) return '单双';
  if (/【大数】|《大数》|【小数】|《小数》/.test(cleaned)) return '大小中特';
  const m = cleaned.match(/【([^】]+)】/);
  if (m) {
    if (/^[大小][单双][大小][单双][大小][单双]$/.test(m[1])) return '大小单双';
    if (/肖|头|尾|大|小|单|双/.test(m[1])) return m[1];
  }
  return '其他';
};
// 开奖部分:[特]开[:：]? 后跟 生肖+两位数字(龙39) 或 ?00 或 纯数字(00)
const RES_RE = /([特]?开[:：]?\s*)([一-龥]{1,2}\d{2}|[?？]\d{0,2}|\d{1,2})(准|错|中|对|发)?/;
const parseLine = (line, src) => {
  const m = line.match(/^第?(\d{3})/);
  if (!m) return null;
  const resM = line.match(RES_RE);
  return { issue: '2026' + m[1], cat: inferCat(line), pred: line, res: resM ? resM[2] : '', src };
};

// 读取某源:返回 { records:[{issue,cat,pred,res,aux:[]}], defs:[定义表行] }
const readSrc = lines => {
  const recs = [];
  const defs = [];
  let cur = null;
  for (let raw of lines) {
    const l = raw.replace(/^[\s　]+|[\s　]+$/g, '');
    if (!l) continue;
    if (isPred(l)) {
      const p = parseLine(l);
      if (p) { cur = { ...p, aux: [] }; recs.push(cur); }
    } else if (isDef(l)) {
      defs.push(l);
      cur = null;
    } else if (isAux(l) && cur) {
      cur.aux.push(l); // 附属行跟随所属预测(必中/主买、【四肖列表】)
    } else {
      cur = null;
    }
  }
  return { recs, defs };
};

// 源1:site67 咕噜圆本人评论(全量提取)
const chatKw = /^(中了么|目前还稳|资料已更完|今天没看|都发了|晚些|看错了|又发了一遍|发了，忘记了|我每天都在|今天发的|今天四肖|五肖六肖|666|稳住|^好$|以前看论坛|^是$|不发了|九点|看不懂|幸好|灵儿|欧阳|找不到|在哪|找了好|你套|我13分|码王|昨天都|今天前|今天后|跟你说了|看到昨天|你搜|你信吗)/;
// 预测判定:期号(239期 或 "239 ")+ 预测特征(开/准/错/中/对/发/出/括号/肖码头尾波词)
// 没有"开"字的行(五不中…准、平特六码…中N个、239 极限尾数)不能丢
const isChat = c => {
  const body = c.content.replace(/<br\s*\/?>/g, ' ').replace(/<img[^>]*>/g, '');
  if (chatKw.test(body)) return true;
  if (!/\d{3}\s*期|\d{3}\s+/.test(body)) return true; // 无期号 → 聊天
  if (/开|准|错|中|对|发|出|【|〖|肖|码|尾|头|波/.test(body)) return false; // 预测特征
  return true;
};
const fmtBody = c => c.content.replace(/<br\s*\/?>/g, '\n').replace(/<img[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();

// 源2~4:粘贴资料(四份)
const pasteFiles = ['paste_raw.txt', 'paste2.txt', 'paste3.txt', 'paste4.txt'];
const rec1 = [], rec2 = [], defs = [];
// 源1:评论(咕噜圆全部;定义行入定义表)
{
  const gyl = [];
  for (const line of fs.readFileSync('/tmp/guluyuan_js/comments.jsonl', 'utf8').trim().split('\n')) {
    try { const c = JSON.parse(line); if (c.username === '咕噜圆') gyl.push(c); } catch (e) {}
  }
  gyl.sort((a, b) => a.time - b.time);
  for (const c of gyl) {
    if (isChat(c)) continue;
    const src = readSrc(fmtBody(c).split('\n'));
    rec1.push(...src.recs);
    defs.push(...src.defs);
  }
}
// 源2~4:粘贴资料
for (const f of pasteFiles) {
  try {
    const src = readSrc(fs.readFileSync('/tmp/guluyuan_js/' + f, 'utf8').split('\n'));
    rec2.push(...src.recs);
    defs.push(...src.defs);
  } catch (e) { console.log('跳过缺失文件: ' + f); }
}
// 源5/6:羊羊咩咩 全部预测评论(所有类别,已排除聊天) — 文孙爱打飞机 2026-08-28 用户判定骗子, 已排除
{
  const wsun = [];
  for (const line of fs.readFileSync('/tmp/guluyuan_js/comments.jsonl', 'utf8').trim().split('\n')) {
    try {
      const c = JSON.parse(line);
      if (c.username === '羊羊咩咩' && !isChat(c)) wsun.push(c);
    } catch (e) {}
  }
  wsun.sort((a, b) => a.time - b.time);
  for (const c of wsun) {
    const src = readSrc(fmtBody(c).split('\n'));
    for (const r of src.recs) r.src = c.username;
    rec2.push(...src.recs);
  }
}
const defsU = [...new Set(defs)];
// 五行对应号码(三行中特判定用号码五行,用户提供)
defsU.push('五行号码: 金=04,05,12,13,26,27,34,35,42,43 | 木=08,09,16,17,24,25,38,39,46,47 | 水=01,14,15,22,23,30,31,44,45 | 火=02,03,10,11,18,19,32,33,40,41,48,49 | 土=06,07,20,21,28,29,36,37');

// 合并去重:同 期号|类别|预测(去开奖部分) 视为同一条;结果(开)以后面更新的实际开奖为准
const seen = new Map();
const unique = [];
const isReal = res => res && !/^[?？]/.test(res);
const predKey = p => {
  let s = p.pred;
  s = s.replace(new RegExp(RES_RE.source + '\\s*$'), '$1?');
  s = s.replace(/[特]?开[:：]?[^]*$/, '开:?');
  return s.replace(/\s+/g, ' ').trim();
};
for (const r of [...rec1, ...rec2]) {
  const k = `${r.issue}|${r.cat}|${predKey(r)}`;
  if (seen.has(k)) {
    const i = seen.get(k);
    const old = unique[i];
    const merged = { ...(isReal(r.res) ? r : old), aux: [...new Set([...old.aux, ...r.aux])] };
    unique[i] = merged;
  } else {
    seen.set(k, unique.length);
    unique.push(r);
  }
}

// 不要的类别(用户指定删除):特码输尽光、顶级一肖、三个半头数、杀三尾
// (「其他」不再排除 —— 全是真实数据,保留输出)
const EXCLUDE = new Set(['特码输尽光', '顶级一肖', '三个半头数', '杀三尾']);
// 分组输出
const groups = {};
for (const r of unique) {
  if (EXCLUDE.has(r.cat)) continue;
  if (!groups[r.cat]) groups[r.cat] = [];
  groups[r.cat].push(r);
}
const order = Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length);

// 统一格式:所有括号 →【】;三行中特"行"字间的 , . 、 分隔符去掉;装饰符号去掉
const normBrackets = s => {
  s = s.replace(/([金木水火土]行)[,.、](?=[金木水火土]行)/g, '$1');
  s = s.replace(/『([^』]*)』/g, '【$1】');
  s = s.replace(/╠([^╣]*)╣/g, '【$1】');
  s = s.replace(/〈〈([^〉]*)〉〉/g, '【$1】').replace(/〈([^〉]*)〉/g, '【$1】');
  s = s.replace(/《([^》]*)》/g, '【$1】');
  s = s.replace(/◇([^◇]*)◇/g, '【$1】');
  s = s.replace(/〖([^〗]*)〗/g, '【$1】');
  s = s.replace(/┣([^┫]*)┫/g, '【$1】');
  s = s.replace(/☾([^☽]*)☽/g, '【$1】').replace(/«([^»]*)»/g, '【$1】').replace(/≮([^≯]*)≯/g, '【$1】');
  s = s.replace(/★(三行中特|平特⑧码|一波中特|五尾中特)★/g, '$1');
  s = s.replace(/[☯☁❀☀△▽々←→*↑↓╳✿〓☞☜]/g, '');
  s = s.replace(/〖([^〗]*)〗/g, '【$1】');
  s = s.replace(/^（([^）]{2,8})）/u, '$1');
  s = s.replace(/（吉美凶丑）/g, '吉美凶丑');
  return s;
};

// 模型内幕分层(用户正在使用的内幕,必须单独分开):生肖层正向/反向 + 号码层
// 生肖层(12肖参与,<10肖有效):正向10系统 + 反向2系统(枪毙/杀 → 投其余9肖)
// 号码层:6系统(精选三头投2-4头 / 单双投单尾+双尾 / 单尾 / 头数中特必中 / 规律大小 / 三行中特五行→号码)
const LAYER_CATS = {
  '内幕·生肖层·正向': ['琴棋书画', '二国中特', '文武中特', '笔墨纸砚', '五肖', '天地中特', '家禽', '左右二肖', '东南西北', '红肖'],
  '内幕·生肖层·反向': ['汉奸', '绝杀三肖'],
  '内幕·号码层': ['精选三头', '单双', '单尾', '头数中特', '规律大小', '三行中特'],
};
const layerOf = cat => {
  for (const [layer, cats] of Object.entries(LAYER_CATS))
    if (cats.includes(cat)) return layer;
  return '非内幕';
};

const out = [];
out.push('══════════════════════════════════════════════════════════');
out.push('  咕噜圆 / 羊羊咩咩 预测资料全集(按人分开,内幕单独分区块; 文孙爱打飞机 2026-08-28 已排除: 骗子)');
out.push('  来源: site67 评论 + 早前粘贴资料(网站已删)');
out.push(`  统计日期: 2026-08-27 | 共 ${unique.length} 条 | 不删任何行(原样保留)`);
out.push('  内幕(正在使用,单独分开): 生肖层=正向10系统(琴棋书画/二国/文武/笔墨纸砚/五肖/天地/家禽/左右/东南西北/红肖) + 反向2系统(汉奸/绝杀三肖→投其余9肖) | 号码层=6系统(精选三头/单双/单尾/头数/规律大小/三行中特) | 其余类别=非内幕');
out.push('══════════════════════════════════════════════════════════');
out.push('');
// 按人分开:咕噜圆(含粘贴资料) / 羊羊咩咩 (文孙 2026-08-28 已排除)
const byPerson = {};
for (const r of unique) {
  if (EXCLUDE.has(r.cat)) continue;
  const p = r.src || '咕噜圆';
  if (!byPerson[p]) byPerson[p] = [];
  byPerson[p].push(r);
}
const PERSON_ORDER = ['咕噜圆', '羊羊咩咩'];
for (const person of PERSON_ORDER) {
  const recs = byPerson[person];
  if (!recs || !recs.length) continue;
  out.push(`◆◆◆ ${person} ◆◆◆`);
  out.push('');
  // 层内:先按用户定义的类别顺序,其余按条数降序
  const layerOrder = ['内幕·生肖层·正向', '内幕·生肖层·反向', '内幕·号码层', '非内幕'];
  for (const layer of layerOrder) {
    const layerRecs = recs.filter(r => layerOf(r.cat) === layer);
    if (!layerRecs.length) continue;
    out.push(`── ${layer} ──`);
    const byCat = {};
    for (const r of layerRecs) (byCat[r.cat] = byCat[r.cat] || []).push(r);
    const catOrder = Object.keys(byCat).sort((a, b) => {
      const ia = LAYER_CATS[layer] ? LAYER_CATS[layer].indexOf(a) : -1;
      const ib = LAYER_CATS[layer] ? LAYER_CATS[layer].indexOf(b) : -1;
      if (ia >= 0 && ib >= 0) return ia - ib;
      if (ia >= 0) return -1;
      if (ib >= 0) return 1;
      return byCat[b].length - byCat[a].length || a.localeCompare(b);
    });
    for (const cat of catOrder) {
      const list = byCat[cat].sort((a, b) => a.issue.localeCompare(b.issue) || a.pred.localeCompare(b.pred));
      out.push(`  ─ ${cat}(${list.length}条) ─`);
      for (const r of list) {
        out.push(`    ${normBrackets(r.pred)}`);
        for (const a of r.aux) out.push(`      ${normBrackets(a)}`);
      }
      out.push('');
    }
  }
}
out.push('── 生肖/分类定义表 ──');
for (const d of defsU) out.push(`  ${d}`);
out.push('');
fs.writeFileSync('/Users/xiejinyu/macau-mark6/咕噜圆预测资料全集.txt', out.join('\n'), 'utf8');
console.log(`已生成: 咕噜圆预测资料全集.txt (${unique.length} 条,${order.length} 类)`);
console.log('类别分布: ' + order.map(c => `${c} ${groups[c].length}`).join(', '));
console.log('定义表行: ' + defs.length + ' 条');
