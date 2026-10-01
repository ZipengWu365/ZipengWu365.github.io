import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Editable labels for the research overview. Links to individual works live in research.html.
const languages = {
  en: {
    title: 'A research map of temporal representation',
    subtitle: 'One shared research core, connected directions, and a growing body of work.',
    left: 'ENCODE & TRANSFORM', right: 'COMPARE & INFER', core: 'SHARED RESEARCH CORE',
    central: ['Temporal', 'Representation'], alias: 'Time-Series Representation',
    question: 'How can we capture temporal structure?',
    foundation: ['Decomposition · structure extraction', 'DeTime / TSDecompose-Benchmark'],
    nodes: [
      ['Symbolic representation', 'Discrete temporal structure', 'Temporal / language-action tokens'],
      ['Compression', 'Compact time-series representations', 'Retaining task-relevant information'],
      ['Frequency conversion', 'Transforming temporal representations', 'Frequency-based transformations'],
      ['Similarity measurement', 'Comparing temporal structure', 'EchoTime · similarity and retrieval'],
      ['Forecasting', 'Using temporal structure to predict', 'Retrieval / multi-output prediction'],
      ['Classification', 'Using temporal structure to distinguish', 'Current work · time-series classification']
    ],
    footer: 'A common lens across time series, spatiotemporal data, and action / model trajectories.',
    note: 'Connections denote research relationships; individual works may span several directions.'
  },
  zh: {
    title: '时间序列表示 · 研究地图',
    subtitle: '以表示为共同核心，连接研究方向，逐步纳入每一项工作。',
    left: '表达与变换', right: '比较与推断', core: '共同研究核心',
    central: ['时间序列', '表示'], alias: 'Temporal / Time-Series Representation',
    question: '如何提取与表达时间结构？',
    foundation: ['分解 · 结构提取', 'DeTime / TSDecompose-Benchmark'],
    nodes: [
      ['符号化表示', '用离散符号表达时间结构', '时间序列 / 语言—动作 tokenization'],
      ['压缩', '构建更紧凑的时间序列表示', '保留与任务相关的信息'],
      ['频率转换', '时间序列表示的变换', '与频率相关的表示变换'],
      ['相似性衡量', '比较时间模式与结构', 'EchoTime · 相似性与检索'],
      ['预测', '利用时间结构推断未来', '检索增强预测 / 多输出预测'],
      ['分类', '利用时间结构区分类别', '当前工作 · 时间序列分类']
    ],
    footer: '共同视角：时间序列、时空数据，以及动作序列与模型轨迹。',
    note: '连线表示研究关联；一项工作可以同时连接多个方向。'
  }
};
const esc = s => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;');
function draw(lang, mobile = false) {
  const d = languages[lang];
  const width = mobile ? 480 : 1440, height = mobile ? 1810 : 950;
  const texts = [];
  const t = (x, y, text, size = 22, fill = '#526377', weight = 400, anchor = 'start') =>
    `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" font-weight="${weight}" text-anchor="${anchor}">${esc(text)}</text>`;
  const line = (path, color = '#b7c7d0') => `<path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>`;
  function node(x, y, index, w = 380) {
    const [title, sub, work] = d.nodes[index];
    const c = index < 3 ? '#14776f' : '#a16024';
    return `<g><rect x="${x}" y="${y}" width="${w}" height="156" rx="12" fill="${index < 3 ? '#eff7f5' : '#fcf5ec'}"/>
      <rect x="${x}" y="${y + 24}" width="4" height="40" rx="2" fill="${c}"/>
      ${t(x + 24, y + 42, title, 28, '#17324d', 600)}
      ${t(x + 24, y + 79, sub, 19)}
      ${t(x + 24, y + 123, work, 18, c, 500)}</g>`;
  }
  function center(x, y, w, h) {
    const cx = x + w / 2;
    return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="18" fill="#17324d"/>
      ${t(cx, y + 37, d.core, 18, '#b8d7e6', 500, 'middle')}
      ${t(cx, y + 92, d.central[0], 38, '#ffffff', 600, 'middle')}
      ${t(cx, y + 140, d.central[1], 38, '#ffffff', 600, 'middle')}
      ${t(cx, y + 180, d.alias, 19, '#e0edf4', 400, 'middle')}
      ${t(cx, y + 225, d.question, 20, '#ffffff', 400, 'middle')}
      ${line(`M ${x + 28} ${y + 251} H ${x + w - 28}`, '#486077')}
      ${t(cx, y + 287, d.foundation[0], 20, '#ffffff', 500, 'middle')}
      ${t(cx, y + 321, d.foundation[1], 18, '#b8d7e6', 400, 'middle')}
      </g>`;
  }
  if (mobile) {
    texts.push(t(24, 46, lang === 'zh' ? d.title : 'Temporal representation', 29, '#17324d', 600));
    texts.push(center(24, 80, 432, 350));
    texts.push(line('M 240 430 V 475'));
    texts.push(t(24, 474, d.left, 21, '#14776f', 600));
    for (let i = 0; i < 3; i++) texts.push(node(24, 500 + i * 175, i, 432));
    texts.push(t(24, 1059, d.right, 21, '#a16024', 600));
    for (let i = 0; i < 3; i++) texts.push(node(24, 1085 + i * 175, i + 3, 432));
    texts.push(t(24, 1658, lang === 'zh' ? '各方向共享表示核心；一项工作可跨多个方向。' : 'All directions connect to the shared core.', 19));
    texts.push(t(24, 1700, lang === 'zh' ? '时间序列 · 时空数据 · 动作与模型轨迹' : 'Time series · spatiotemporal data', 19));
    texts.push(t(24, 1732, lang === 'zh' ? 'Zipeng Wu · Research overview' : 'Action histories · model trajectories', 19));
  } else {
    texts.push(t(48, 65, 'ZIPENG WU / RESEARCH OVERVIEW', 19, '#14776f', 600));
    texts.push(t(48, 120, d.title, 39, '#17324d', 600));
    texts.push(t(48, 164, d.subtitle, 23));
    texts.push(t(48, 231, d.left, 20, '#14776f', 600));
    texts.push(t(1012, 231, d.right, 20, '#a16024', 600));
    texts.push(line('M 428 342 H 467 V 537 H 515 M 428 537 H 515 M 428 732 H 467 V 537'));
    texts.push(line('M 925 537 H 973 V 342 H 1012 M 925 537 H 1012 M 973 537 V 732 H 1012'));
    for (let i = 0; i < 3; i++) {
      texts.push(node(48, 264 + i * 195, i));
      texts.push(node(1012, 264 + i * 195, i + 3));
    }
    texts.push(center(515, 361, 410, 350));
    texts.push(t(720, 860, d.footer, 23, '#17324d', 500, 'middle'));
    texts.push(t(720, 905, d.note, 20, '#526377', 400, 'middle'));
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc" lang="${lang}">
<title id="title">${esc(d.title)}</title><desc id="desc">${esc(d.nodes.map(n => n.join(': ')).join('. '))}. ${esc(d.note)}</desc>
<rect width="${width}" height="${height}" fill="#ffffff"/>
<g font-family="Segoe UI, Microsoft YaHei, Arial, sans-serif">${texts.join('\n')}</g></svg>\n`;
}
const output = fileURLToPath(new URL('../assets/img/', import.meta.url));
mkdirSync(output, { recursive: true });
for (const lang of Object.keys(languages)) {
  for (const mobile of [false, true]) {
    writeFileSync(`${output}/research-map-${lang}${mobile ? '-mobile' : ''}.svg`, draw(lang, mobile));
  }
}
