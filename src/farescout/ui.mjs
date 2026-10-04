import {ViewState, bestFare, coverageDates, routeKey, scopedEvents, validMessage} from './ui-state.mjs';

const $ = id => document.getElementById(id);
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const state = new ViewState();
let stream = null, refreshTimer = null, pollTimer = null, historyRevision = 0;
let selectedRoute = null, panelTab = 'trace', resultSignature = '', inspectorSignature = '', editorGoal = '';
const stageNames = {research_decision:'决定下一步',checkpoint:'保留成功步骤',result_available:'已有可核对结果',browser_connection:'连接浏览器', social_scan:'读取社区内容', model:'模型处理', social_preview:'搜索社区帖子', social_read:'读取帖子正文', social_read_result:'正文读取结果', date_phase:'日期探索完成', discovery:'开始研究', goal:'理解研究条件', plan:'安排社区查询', community_search:'搜索社区', evidence:'取得社区证据', extract:'筛选航线', expansion_plan:'决定继续查什么', query_expansion:'扩展查询', date_plan:'选择抽查日期', date_exploration:'探索日期价格', date_selected:'选择复验日期', fare:'核对实时票价', coverage:'确认日期覆盖', conflict:'核对不同来源', conclusion:'形成结论', context:'沿用研究上下文', stop:'停止研究', resume:'继续研究', quality:'检查证据质量', candidate:'发现候选航线', source_query:'实际搜索词', source_retry:'重试来源', budget:'到达查询预算', deal:'判断价格机会'};
const statusNames = {running:'研究进行中', complete:'研究完成', partial:'部分完成', blocked:'来源受阻'};
const fields = {origins:'出发机场', region:'目的地区', date_from:'开始日期', date_to:'结束日期', date_mode:'日期方式', trip_type:'行程', stay_days:'停留天数', no_red_eye:'红眼航班'};
const provenance = {explicit:'用户明确要求', inferred:'根据语义理解', default:'系统默认', context:'沿用前文'};
const groups = {community:['community_search','social_scan','social_preview','social_read','social_read_result','evidence','quality','extract','expansion_plan','query_expansion','source_query','source_retry','candidate'], dates:['date_plan','date_exploration','date_selected','coverage','date_phase'], fares:['fare','conflict','deal','conclusion']};
const shortDate = value => value ? `${Number(value.slice(5,7))} 月 ${Number(value.slice(8,10))} 日` : '未选定';
const stamp = value => value ? new Date(value).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) : '时间未知';
const money = value => Number(value).toLocaleString('zh-CN', {maximumFractionDigits:2});
const taxLabel = fare => fare.price_basis === 'total_including_taxes' ? '含税' : '税费未确认';
const fareLabel = fare => `${taxLabel(fare)} · ${fare.request.return_date ? '往返' : '单程'} · 1 成人`;
function sourceLink(text, url) {
  try { if (new URL(url).protocol !== 'https:') return el('span', text); } catch { return el('span', text); }
  const node = el('a', text); node.href = url; node.target = '_blank'; node.rel = 'noopener'; return node;
}
function showError(message = '') { $('error').textContent = message; $('error').hidden = !message; }
async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) { const error = Error(data.error || '请求失败'); error.status = response.status; error.data = data; throw error; }
  return data;
}
function syncControls() {
  $('run').disabled = state.locked;
  $('apply').disabled = state.locked || !state.turn;
  $('new').disabled = state.starting;
  $('resume').disabled = state.locked;
  $('run').firstChild.textContent = state.starting ? '正在开始… ' : state.sid ? '继续研究 ' : '开始研究 ';
  const elsewhere = state.activeSid && state.activeSid !== state.sid;
  $('activeNotice').hidden = !elsewhere;
  $('activeText').textContent = elsewhere ? '另一项研究正在进行。可以先查看历史结果。' : '';
}
async function loadHistory({initial = false} = {}) {
  const revision = ++historyRevision, initialEpoch = state.epoch;
  try {
    const data = await api('/api/sessions');
    if (revision !== historyRevision) return;
    if (!state.starting) state.activeSid = data.active || null;
    $('history').replaceChildren(); $('historyCount').textContent = data.sessions.length;
    for (const item of data.sessions) {
      const button = el('button', undefined, item.id === state.sid ? 'active' : '');
      button.dataset.sessionId = item.id;
      const meta = el('span', undefined, 'histmeta');
      meta.append(el('span', statusNames[item.status] || item.status, item.status), el('span', `${stamp(item.started_at)} · ${item.turns} 轮`));
      button.append(el('span', item.message, 'histtitle'), meta);
      button.onclick = () => openSession(item.id);
      $('history').append(button);
    }
    if (!data.sessions.length) $('history').append(el('p', '研究完成后会保存在这里。', 'muted'));
    syncControls();
    // Open the most recent actual research at startup so results, rather than a
    // blank composer, occupy the first screen. This never runs a new search.
    if (initial && state.epoch === initialEpoch && !state.sid && data.sessions.length) await openSession(data.active || data.sessions[0].id);
  } catch (error) { if (revision === historyRevision) showError(error.message); }
}
function chosenOpportunity() { return state.turn?.opportunities.find(o => routeKey(o) === selectedRoute) || null; }
function resetView() {
  selectedRoute = null; panelTab = 'trace'; resultSignature = ''; inspectorSignature = ''; editorGoal = '';
  $('edit').hidden = true; $('editButton').setAttribute('aria-expanded', 'false');
  $('constraintPanel').open = false; $('statistics').open = false; $('traceFilter').value = 'all';
  $('main').scrollTop = 0; $('trace').scrollTop = 0; $('evidenceView').scrollTop = 0;
  showError(); render();
}
function emptyResults(title, text, symbol = '↗', className = '') {
  const empty = el('div', undefined, 'empty-state ' + className);
  empty.append(el('div', symbol, 'empty-symbol'), el('h2', title), el('p', text));
  if (!className) { const steps = el('div', undefined, 'empty-steps'); steps.append(el('span', '社区发现'), el('span', '→'), el('span', '日期探索'), el('span', '→'), el('span', '实时验价')); empty.append(steps); }
  return empty;
}
function render() {
  const turn = state.turn;
  document.body.classList.toggle('has-research', Boolean(turn));
  syncControls();
  $('report').hidden = !state.reportURL;
  if (state.reportURL) $('report').href = state.reportURL; else $('report').removeAttribute('href');
  $('constraintPanel').hidden = !turn; $('statistics').hidden = !turn;
  $('turn').hidden = !turn || state.session.turns.length < 2;
  $('resultFootnote').hidden = !turn?.opportunities.length;
  const live = turn?.status === 'running' && state.activeSid === state.sid;
  const interrupted = turn?.status === 'running' && !live && !state.starting;
  const recoverable = turn && turn.id === state.session.turns.at(-1)?.id && !live && (interrupted || ['partial','blocked'].includes(turn.status));
  $('recoveryPanel').hidden = !recoverable;
  if (recoverable) {
    const connection = [...turn.events].reverse().find(e => e.stage === 'browser_connection')?.data;
    $('browserStatus').textContent = connection ? `上次检查：${connection.browser_connected ? 'Chrome已连接' : 'Chrome未连接，授权状态未知'} · ${stamp(connection.observed_at)}` : '尚未取得浏览器连接状态，可先检查再恢复';
  }
  $('outcomeNotice').hidden = !turn || (!interrupted && !['partial','blocked'].includes(turn.status));
  $('outcomeNotice').textContent = interrupted ? '这轮研究尚未完成，当前服务没有运行它。可从左侧恢复这轮；继续提问会开启新一轮。' : turn?.stop_reason || '';
  $('status').className = 'status ' + (interrupted ? 'partial' : turn?.status || '');
  $('status').textContent = interrupted ? '研究未完成' : turn ? statusNames[turn.status] || turn.status : state.sid ? '正在载入' : '等待开始';
  $('traceState').className = 'trace-state' + (live ? ' live' : '');
  $('traceState').textContent = turn ? live ? '● 实时' : '历史回放' : '等待开始';
  $('context').textContent = state.sid ? '继续提问会沿用当前研究上下文' : '默认 1 成人 · 经济舱 · 单程';
  if (!turn) {
    $('resultTitle').textContent = state.sid ? '正在载入研究结果…' : '从一个想法，找到值得出发的方向。';
    $('researchQuestion').textContent = '先从社区发现线索，再核对具体日期和票价。';
    $('resultMeta').textContent = '找到什么，为什么值得关注，都放在这里。';
    $('turn').replaceChildren(); $('constraints').replaceChildren(); $('semanticRules').replaceChildren(); $('metrics').replaceChildren();
    $('results').replaceChildren(emptyResults(state.sid ? '正在读取研究记录' : '下一趟，飞哪里？', '给一个出发地和大致时间。飞探会从社区线索里找出你原本不知道该搜索的航线。'));
    renderPanel(); return;
  }
  const opportunities = turn.opportunities || [], verified = opportunities.filter(o => o.fares.length).length;
  $('resultTitle').textContent = verified ? `${verified} 个有报价的出行方向` : opportunities.length ? `${opportunities.length} 条社区线索，等待验价` : live ? '正在寻找值得出发的方向' : '这次还没有可验证的航线机会';
  $('researchQuestion').textContent = turn.user_input;
  $('resultMeta').textContent = `${live ? '本轮研究' : '历史研究'} · ${stamp(turn.finished_at || turn.started_at)}${opportunities.length > verified ? ` · ${opportunities.length - verified} 条线索待验价` : ''}`;
  const currentOptions = [...$('turn').options].map(o => o.value).join();
  if (currentOptions !== state.session.turns.map(t => t.id).join()) $('turn').replaceChildren(...state.session.turns.map((t, i) => { const option = el('option', `第 ${i+1} 轮 · ${t.user_input.slice(0,18)}`); option.value = t.id; return option; }));
  $('turn').value = turn.id;
  renderConstraints(turn.goal);
  renderMetrics(turn);
  const signature = JSON.stringify(opportunities) + turn.status + live;
  if (signature !== resultSignature) {
    resultSignature = signature;
    const results = $('results'); results.replaceChildren();
    if (!opportunities.length) results.append(emptyResults(live ? '正在阅读社区，寻找航线线索…' : '还没有取得可验证结果', live ? '已读内容和实际操作会出现在右侧。有真实票价后，日期和价格会在这里逐条出现。' : '本轮没有拿到足够的证据或报价。右侧保留了研究记录，可以据此继续研究。', turn.status === 'blocked' ? '↗' : '⌁', turn.status === 'blocked' ? 'blocked' : ''));
    for (const [index, opportunity] of opportunities.entries()) results.append(routeCard(opportunity, index));
  }
  if (selectedRoute && !chosenOpportunity()) selectedRoute = null;
  renderPanel();
}
function renderConstraints(goal) {
  $('constraintBrief').textContent = `${goal.origins.join(' / ')} · ${goal.trip_type === 'round_trip' ? '往返' : '单程'}`;
  const descriptions = goal.constraints?.length ? goal.constraints : Object.entries(goal).filter(([key]) => fields[key]).map(([field,value]) => ({field,value,provenance:'context',rule:'历史记录未保存原始语义解释'}));
  $('constraints').replaceChildren(); $('semanticRules').replaceChildren();
  for (const constraint of descriptions) {
    let value = constraint.value;
    const labels = {JP:'日本', flexible:'灵活探索', fixed:'固定日期', one_way:'单程', round_trip:'往返'};
    if (constraint.field === 'no_red_eye') value = value ? '排除 22:00–06:00 / 跨夜' : '允许';
    else if (Array.isArray(value)) value = value.join(' / ');
    else value = labels[value] || String(value ?? '不限');
    const row = el('div', undefined, 'constraint'); row.append(el('span', fields[constraint.field] || constraint.field), el('span', value)); $('constraints').append(row);
    $('semanticRules').append(el('p', `${fields[constraint.field] || constraint.field}：${provenance[constraint.provenance] || '历史条件'}${constraint.raw_text ? `；原文「${constraint.raw_text}」` : ''}${constraint.rule ? `；${constraint.rule}` : ''}`));
  }
  // Live snapshots must not overwrite an in-progress edit.
  const key = `${state.sid}:${state.turn.id}`;
  if ($('edit').hidden && editorGoal !== key) { hydrateEditor(goal); editorGoal = key; }
}
function hydrateEditor(goal) {
  $('dateFrom').value = goal.date_from; $('dateTo').value = goal.date_to;
  $('trip').value = goal.trip_type; $('stay').value = goal.stay_days; $('red').value = String(goal.no_red_eye);
  updateStay();
}
function updateStay() { $('stayLabel').hidden = $('trip').value !== 'round_trip'; $('stay').disabled = $('stayLabel').hidden; }
function renderMetrics(turn) {
  const m = turn.metrics || {};
  const values = [`社区正文：${m.evidence_count ?? turn.evidence_ids.length} 篇`, `归并后的线索：${m.independence_groups ?? '未知'} 组（不等于独立来源）`, `社区查询：${m.community_calls || 0} 次`, `日期探索：${m.date_calls || 0} 次调用`, `最终验价：${m.verification_calls || 0} 次调用`, `复用本轮报价：${m.quote_reuses || 0} 次`, `总耗时：${m.elapsed_seconds != null ? Number(m.elapsed_seconds).toFixed(1) + ' 秒' : '进行中'}`];
  for (const [key,label] of [['first_result_seconds','首条可核对结果'],['third_result_seconds','前三条可核对结果']]) values.push(`${label}：${m[key] != null ? Number(m[key]).toFixed(1) + ' 秒' : '尚未取得'}`);
  if (m.execution_segments > 1) values.push(`恢复/执行 ${m.execution_segments} 段，实际执行累计 ${Number(m.execution_seconds).toFixed(1)} 秒；总耗时包含中间等待`);
  for (const [stage,label] of [['community_search','社区搜索'],['query_expansion','扩展查询'],['date_phase','日期探索与验价'],['model','模型处理']]) if (m[`stage_${stage}_seconds`] != null) values.push(`${label}耗时：${Number(m[`stage_${stage}_seconds`]).toFixed(1)} 秒`);
  $('metrics').replaceChildren(...values.map(value => el('div', value)));
}
function routeCard(opportunity, index) {
  const fare = bestFare(opportunity), candidate = opportunity.candidate;
  const card = el('article', undefined, 'route-card' + (fare ? '' : ' unverified'));
  card.dataset.route = routeKey(opportunity);
  const heading = el('div', undefined, 'route-heading'), name = el('h3');
  name.append(el('span', String(index + 1).padStart(2, '0'), 'route-rank'), document.createTextNode(candidate.destination_name));
  heading.append(name);
  if (opportunity.deal?.label) heading.append(el('span', opportunity.deal.label, 'deal-tag ' + opportunity.deal.level));
  card.append(heading, el('div', `${candidate.origin} → ${candidate.destination}`, 'route-code'));
  const quote = el('div', undefined, 'quote-primary'), amount = el('div'), price = el('div', undefined, 'price' + (fare ? '' : ' pending'));
  if (fare) price.append(el('span', '¥', 'currency'), document.createTextNode(money(fare.amount))); else price.textContent = '待验证';
  amount.append(price, el('div', fare ? fareLabel(fare) : '没有取得当前报价', 'price-basis'));
  const date = el('div', fare ? shortDate(fare.request.outbound_date) : '日期待确认', 'flight-date');
  date.append(el('small', fare ? `${fare.request.outbound_date.slice(0,4)} 年${fare.request.return_date ? ' · ' + shortDate(fare.request.return_date) + '返程' : ' · 出发'}` : '社区线索'));
  quote.append(amount, date); card.append(quote);
  const why = el('p', candidate.why, 'why'); why.title = candidate.why; card.append(why);
  const bottom = el('div', undefined, 'route-bottom'), sources = el('div', undefined, 'source-summary');
  const uniqueSources = new Set(opportunity.fares.map(f => f.source));
  sources.append(el('div', fare ? `${fare.source} · 查询 ${stamp(fare.observed_at)}` : `${candidate.signals.length} 条社区引用`));
  const mixed = new Set(opportunity.fares.map(f => f.price_basis)).size > 1;
  sources.append(el('div', mixed ? `${uniqueSources.size} 个票价源 · 税费口径不同` : uniqueSources.size < 2 && fare ? '仅一个票价源成功' : fare ? `${uniqueSources.size} 个票价源有报价` : '社区晒价未当作当前票价', mixed || (fare && uniqueSources.size < 2) ? 'warning' : ''));
  const action = el('button', '追溯依据 →', 'trace-link'); action.setAttribute('aria-label', `查看${candidate.destination_name}的证据与验价过程`);
  action.onclick = () => selectOpportunity(routeKey(opportunity)); bottom.append(sources, action); card.append(bottom); return card;
}
function selectOpportunity(key) {
  selectedRoute = key; panelTab = 'evidence'; inspectorSignature = ''; $('evidenceView').scrollTop = 0;
  renderPanel();
  if (window.innerWidth <= 930) $('researchPanel').scrollIntoView({behavior:'smooth',block:'start'});
  $('evidenceTab').focus({preventScroll:true});
}
function switchTab(tab) { panelTab = tab; renderPanel(); }
function renderPanel() {
  const opportunity = chosenOpportunity();
  $('routeScope').hidden = !opportunity;
  $('scopeLabel').textContent = opportunity ? `${opportunity.candidate.destination_name} · ${routeKey(opportunity).replace('-', ' → ')}` : '';
  $('traceTab').setAttribute('aria-selected', panelTab === 'trace'); $('evidenceTab').setAttribute('aria-selected', panelTab === 'evidence');
  $('traceTab').tabIndex = panelTab === 'trace' ? 0 : -1; $('evidenceTab').tabIndex = panelTab === 'evidence' ? 0 : -1;
  $('traceView').hidden = panelTab !== 'trace'; $('evidenceView').hidden = panelTab !== 'evidence';
  for (const card of $('results').querySelectorAll('[data-route]')) card.classList.toggle('selected', card.dataset.route === selectedRoute);
  renderTrace(opportunity); renderInspector(opportunity);
}
function renderTrace(opportunity) {
  const trace = $('trace'), previousScroll = trace.scrollTop;
  const opened = new Set([...trace.querySelectorAll('details[open][data-event-id]')].map(node => node.dataset.eventId));
  const focused = document.activeElement?.closest?.('[data-event-id]')?.dataset.eventId;
  const filter = $('traceFilter').value;
  const events = state.turn ? scopedEvents(state.session, state.turn, opportunity).filter(({event}) => filter === 'all' || filter === 'failed' && (event.status === 'failed' || event.stage === 'conflict') || groups[filter]?.includes(event.stage)) : [];
  trace.replaceChildren();
  if (!events.length) trace.append(el('div', state.turn ? '这个范围内还没有研究记录。可以切换阶段或显示全部轨迹。' : '搜索、阅读、扩展查询、日期探索和验价会实时出现在这里。点击航线的「追溯依据」，就能看它的证据和验证过程。', 'trace-empty'));
  for (const {event, inherited, round} of events) {
    const node = el('details', undefined, `event ${event.status} ${event.stage} ${event.phase}`); node.dataset.eventId = event.id; node.open = opened.has(event.id);
    const summary = el('summary'), title = el('div', undefined, 'event-title');
    title.append(el('span', stageNames[event.stage] || event.stage), el('span', new Date(event.time).toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}), 'event-time'));
    summary.append(title, el('div', `${event.source || '飞探'}${event.phase === 'started' ? ' · 开始' : event.status === 'failed' ? ' · 失败' : ''}${event.duration_ms != null ? ' · ' + (event.duration_ms / 1000).toFixed(1) + ' 秒' : ''}${inherited ? ` · 沿用第 ${round} 轮证据` : ''}`, 'event-source'), el('div', event.detail, 'event-detail'));
    node.append(summary);
    for (const id of event.evidence_ids || []) {
      const evidence = state.session.evidence[id];
      if (!evidence) continue;
      const body = el('div', undefined, 'event-body'); body.append(sourceLink(evidence.title || evidence.source, evidence.url), el('div', evidence.body), el('div', `社区内容 · 发布 ${evidence.published_at || '未知'} · 读取 ${stamp(evidence.observed_at)}`, 'evidence-meta')); node.append(body);
    }
    if (Object.keys(event.data || {}).length) { const data = el('details', undefined, 'event-body'); data.append(el('summary', '查看操作数据'), el('pre', JSON.stringify(event.data, null, 2))); node.append(data); }
    trace.append(node);
  }
  if (focused) [...trace.querySelectorAll('[data-event-id]')].find(node => node.dataset.eventId === focused)?.querySelector('summary').focus({preventScroll:true});
  trace.scrollTop = $('followTrace').checked && state.turn?.status === 'running' && !opportunity ? trace.scrollHeight : previousScroll;
  $('traceFooter').textContent = state.turn ? `${events.length} 条真实记录${opportunity ? ' · 仅显示此航线及关联证据' : ' · 点击展开原文与操作数据'}` : '展示真实操作与来源，不展示模型的私有思维过程。';
}
function inspectorSection(number, title) {
  const section = el('section', undefined, 'inspector-section'), heading = el('h3'); heading.append(el('span', number, 'section-number'), document.createTextNode(title)); section.append(heading); return section;
}
function renderInspector(opportunity) {
  const signature = JSON.stringify(opportunity) + state.sid + state.turn?.id;
  if (signature === inspectorSignature) return;
  inspectorSignature = signature; const inspector = $('inspector'); inspector.replaceChildren();
  if (!opportunity) { inspector.append(el('p', '选择一条航线的「追溯依据」，查看社区原文、已查日期、报价来源和仍未确认的部分。', 'trace-empty')); return; }
  const intro = el('div', undefined, 'inspector-intro'); intro.append(el('h3', opportunity.candidate.destination_name), el('p', `${routeKey(opportunity).replace('-', ' → ')} · 社区晒价和查到的票价分别展示`, 'muted')); inspector.append(intro);
  const why = inspectorSection('01', '为什么关注这条航线'); why.append(el('p', opportunity.candidate.why)); if (opportunity.deal?.label) why.append(el('p', opportunity.deal.label)); inspector.append(why);
  const community = inspectorSection('02', '社区里发现了什么');
  const signals = opportunity.candidate.signals || [];
  for (const signal of signals) {
    const evidence = state.session.evidence[signal.evidence_id];
    if (!evidence) { community.append(el('p', '这条引用的原文暂未载入，不能据此确认社区价格。', 'warning')); continue; }
    const item = el('details', undefined, 'evidence-item'), summary = el('summary');
    summary.append(sourceLink(evidence.title || '社区帖子', evidence.url), el('div', signal.excerpt, 'evidence-excerpt'), el('div', `社区晒价：${signal.seen_price_text || '没有可引用的价格'}（不代表当前可买）`, 'community-price'), el('div', `发布 ${evidence.published_at || '未知'} · 读取 ${stamp(evidence.observed_at)}`, 'evidence-meta'));
    item.append(summary, el('div', evidence.body, 'body'));
    for (const comment of evidence.comments || []) item.append(el('div', '评论：' + comment.text, 'body'));
    const flags = evidence.quality?.flags || [];
    item.append(el('div', `证据检查：${flags.length ? flags.join('；') : '暂无命中风险词，仍需验价'}。${evidence.quality?.independence ? '来源独立性：' + evidence.quality.independence : '不同帖子不自动算作独立来源。'}`, 'evidence-meta'));
    community.append(item);
  }
  const groups = new Set(signals.map(signal => {const e = state.session.evidence[signal.evidence_id]; return e?.quality?.independence_group || signal.evidence_id;}));
  community.append(el('p', `${signals.length} 条引用，按现有记录归为 ${groups.size} 组线索。分组不代表已确认彼此独立。`, 'evidence-meta')); inspector.append(community);
  const dates = inspectorSection('03', '实际查了哪些日期'), coverage = opportunity.date_coverage;
  if (!coverage) dates.append(el('p', '尚未完成日期探索。'));
  else {
    dates.append(el('p', `${coverage.date_from} 至 ${coverage.date_to}；复验日期 ${coverage.selected_date || '尚未选定'}。`));
    const chips = el('div', undefined, 'date-list');
    for (const date of coverageDates(coverage)) { const samples = coverage.samples.filter(s => s.date === date && s.stage !== 'range'), ok = samples.some(s => s.status === 'ok'); const chip = el('span', date.slice(5), 'date-chip' + (date === coverage.selected_date ? ' selected' : !ok ? ' failed' : '')); chip.title = samples.map(s => `${s.source}：${s.status === 'ok' ? s.amount != null ? '¥' + s.amount : '取得结果' : '失败'} · ${s.detail || s.stage}`).join('\n'); chips.append(chip); }
    dates.append(chips, el('p', `发出精确请求的日期有 ${coverageDates(coverage).length} 个，其中 ${new Set(coverage.samples.filter(s => s.stage !== 'range' && s.status === 'ok').map(s => s.date)).size} 个取得报价。范围查询返回 ${(coverage.returned_dates || []).length} 个日期，不算逐日验价。`, 'evidence-meta'), el('p', '未查日期保持未知；这里没有声称全月最低。', 'warning'));
    for (const note of coverage.notes || []) dates.append(el('p', note, 'evidence-meta'));
  }
  inspector.append(dates);
  const verification = inspectorSection('04', '票价是怎样验证的');
  // Keep providers, dates and tax bases separate; different conditions are not a price range.
  const quotes = new Map();
  for (const fare of opportunity.fares) { const key = [fare.source,fare.request.outbound_date,fare.request.return_date,fare.price_basis].join('|'); if (!quotes.has(key) || quotes.get(key).amount > fare.amount) quotes.set(key, fare); }
  if (!quotes.size) verification.append(el('p', '尚未取得当前报价。社区晒价没有填入票价。', 'warning'));
  for (const fare of quotes.values()) {
    const item = el('div', undefined, 'verified-quote'), label = el('div', undefined, 'quote-label'); label.append(sourceLink(fare.source, fare.source_url), el('span', '¥' + money(fare.amount), 'quote-amount'));
    item.append(label, el('div', `${fare.request.outbound_date}${fare.request.return_date ? ' → ' + fare.request.return_date : ''} · ${fareLabel(fare)}`, 'evidence-meta'), el('div', '查询时间 ' + stamp(fare.observed_at), 'evidence-meta'));
    for (const segment of fare.segments) item.append(el('div', `${segment.airline} ${segment.flight_number} · ${segment.origin} ${segment.departure} → ${segment.destination} ${segment.arrival}`, 'segment'));
    item.append(el('div', fare.baggage, 'evidence-meta'));
    for (const restriction of fare.restrictions || []) item.append(el('div', restriction, 'evidence-meta'));
    if (fare.price_insights?.typical_price_range) item.append(el('div', `Google 典型价格 ¥${fare.price_insights.typical_price_range.map(money).join('–')} · ${fare.price_insights.comparable ? '满足程序的比较条件' : '条件未对齐，只作参考'}`, 'evidence-meta'));
    verification.append(item);
  }
  for (const text of [...opportunity.comparison, ...opportunity.limitations]) verification.append(el('p', text, 'warning'));
  inspector.append(verification);
  const process = el('button', '查看这条航线的完整研究轨迹 →', 'full-trace-button'); process.onclick = () => { $('traceFilter').value = 'all'; $('followTrace').checked = false; $('trace').scrollTop = 0; switchTab('trace'); $('traceTab').focus({preventScroll:true}); }; inspector.append(process);
}
function disconnect() {
  clearTimeout(refreshTimer); clearTimeout(pollTimer); refreshTimer = null; pollTimer = null;
  stream?.close(); stream = null;
}
async function refresh() {
  if (!state.sid) return;
  const token = state.requestToken();
  try {
    const data = await api(`/api/sessions/${encodeURIComponent(token.sid)}`);
    if (!state.accept(token, data)) return;
    render();
    if (data.error && !data.active && state.turn?.status !== 'complete') showError(data.error);
    if (state.activeSid === state.sid && !stream) connect();
  } catch (error) {
    if (!state.current(token)) return;
    if (error.status === 404 && error.data?.active === token.sid) { refreshTimer = setTimeout(refresh, 350); return; }
    showError(error.message);
  }
}
function connect() {
  const id = state.sid, epoch = state.epoch;
  if (!id) return;
  stream?.close();
  const connection = new EventSource(`/api/sessions/${encodeURIComponent(id)}/events`); stream = connection;
  const current = () => state.sid === id && state.epoch === epoch && stream === connection;
  connection.addEventListener('research', () => {
    if (!current()) return;
    // Throttle, don't debounce: a steady stream must not starve the UI of updates.
    if (!refreshTimer) refreshTimer = setTimeout(() => {refreshTimer = null; refresh();}, 100);
  });
  connection.addEventListener('done', async () => {
    if (!current()) return;
    connection.close(); stream = null; clearTimeout(refreshTimer); refreshTimer = null;
    await refresh();
    if (state.sid === id && state.epoch === epoch) { await loadHistory(); render(); }
  });
  connection.onopen = () => { if (current()) $('traceState').classList.remove('connection-warning'); };
  connection.onerror = () => {
    if (!current()) return;
    $('traceState').textContent = '连接恢复中'; $('traceState').classList.add('connection-warning');
    // Keep EventSource's built-in reconnect and refresh disk snapshots meanwhile.
    clearTimeout(pollTimer); pollTimer = setTimeout(async () => { if (!current()) return; await refresh(); }, 1200);
  };
}
async function openSession(id) {
  if (state.starting) return;
  disconnect(); state.select(id); resetView();
  for (const button of $('history').querySelectorAll('button')) button.classList.toggle('active', button.dataset.sessionId === id);
  await refresh();
}
async function run(message, {resume = false} = {}) {
  if (!resume && !validMessage(message)) { showError('请输入 1～3000 字的研究需求。'); return; }
  if (state.locked) { showError('已有研究正在进行，请等待完成后再提交。'); return; }
  const id = state.sid || 'web-' + Date.now(), epoch = state.epoch;
  state.starting = true; syncControls(); showError();
  try {
    await api(resume ? '/api/resume' : '/api/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:id,message:message.trim()})});
    disconnect(); state.select(id); state.activeSid = id; resetView(); connect();
    await refresh(); await loadHistory();
  } catch (error) {
    if (state.epoch === epoch) showError(error.message);
    await loadHistory();
  } finally { state.starting = false; syncControls(); }
}
$('compose').onsubmit = event => {event.preventDefault(); run($('message').value);};
$('resume').onclick = () => run('', {resume:true});
$('checkBrowser').onclick = async () => {
  const epoch = state.epoch; $('checkBrowser').disabled = true;
  try {
    const data = await api('/api/browser');
    if (state.epoch !== epoch) return;
    const connection = data.connection || {};
    $('browserStatus').textContent = data.error || `${data.ready ? 'Chrome已连接，可以恢复' : 'Chrome未连接；恢复时可能需要手动允许连接'} · ${stamp(connection.observed_at)}${connection.endpoint_changed ? ' · 浏览器endpoint已变化' : ''}${connection.last_disconnect ? ' · 最近记录的传输问题：' + ({session_closed:'会话关闭', transport_command_timeout:'连接命令超时',transport_lost_unknown:'原因未确认'}[connection.last_disconnect.category] || '未知') : ''}`;
  } catch (error) {if (state.epoch === epoch) showError(error.message);}
  finally {$('checkBrowser').disabled = false;}
};
$('new').onclick = () => { if (state.starting) return; disconnect(); state.select(); resetView(); $('message').value = ''; loadHistory(); $('message').focus(); };
$('returnLive').onclick = () => { if (state.activeSid) openSession(state.activeSid); };
$('turn').onchange = () => {state.selectedTurn = $('turn').value; selectedRoute = null; editorGoal = ''; $('edit').hidden = true; $('editButton').setAttribute('aria-expanded','false'); resultSignature = ''; inspectorSignature = ''; $('main').scrollTop = 0; render();};
$('traceFilter').onchange = () => { $('trace').scrollTop = 0; renderTrace(chosenOpportunity()); };
$('followTrace').onchange = () => renderTrace(chosenOpportunity());
$('traceTab').onclick = () => switchTab('trace'); $('evidenceTab').onclick = () => switchTab('evidence');
for (const tab of [$('traceTab'), $('evidenceTab')]) tab.onkeydown = event => {if (['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {event.preventDefault(); switchTab(event.key === 'Home' ? 'trace' : event.key === 'End' ? 'evidence' : panelTab === 'trace' ? 'evidence' : 'trace'); $(panelTab === 'trace' ? 'traceTab' : 'evidenceTab').focus();}};
$('clearScope').onclick = () => {selectedRoute = null; inspectorSignature = ''; $('trace').scrollTop = 0; renderPanel();};
$('editButton').onclick = () => {if (!state.turn) return; $('edit').hidden = !$('edit').hidden; $('editButton').setAttribute('aria-expanded', !$('edit').hidden); if (!$('edit').hidden) hydrateEditor(state.turn.goal);};
$('trip').onchange = updateStay;
$('edit').onsubmit = event => {
  event.preventDefault();
  if (!$('dateFrom').value || !$('dateTo').value || $('dateFrom').value > $('dateTo').value) {showError('开始日期不能晚于结束日期。'); return;}
  const stay = Number($('stay').value);
  if ($('trip').value === 'round_trip' && (!Number.isInteger(stay) || stay < 1 || stay > 30)) {showError('往返停留天数需为 1～30 的整数。'); return;}
  run(`${$('dateFrom').value} 至 ${$('dateTo').value}，${$('trip').value === 'round_trip' ? '往返，停留 ' + stay + ' 天' : '单程'}，${$('red').value === 'true' ? '不要红眼' : '可以红眼'}`);
};
window.addEventListener('pagehide', disconnect);
// History browsing does not attach to the live stream. Check the global task
// lock so a completed background research cannot leave these buttons disabled.
setInterval(() => {if (state.activeSid && state.activeSid !== state.sid && !state.starting) loadHistory();}, 4000);
render(); loadHistory({initial:true});
