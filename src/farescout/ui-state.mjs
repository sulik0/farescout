// Small, DOM-free helpers shared by the workspace and regression tests.
export const routeKey = opportunity => `${opportunity.candidate.origin}-${opportunity.candidate.destination}`;

export function bestFare(opportunity) {
  const fares = opportunity.fares || [];
  const taxIncluded = fares.filter(f => f.price_basis === 'total_including_taxes');
  return (taxIncluded.length ? taxIncluded : fares).reduce((best, fare) => !best || fare.amount < best.amount ? fare : best, null);
}

export function coverageDates(coverage) {
  return dateResearchState(coverage).attempted_dates;
}

export function dateResearchState(coverage) {
  if (coverage?.research_state) return coverage.research_state;
  const samples = coverage?.samples || [];
  const reused = s => s.reused === true || (s.reused === undefined && (s.detail || '').includes('复用本轮'));
  const precise = samples.filter(s => s.stage !== 'range' && s.request_issued !== false && !reused(s));
  const dates = rows => [...new Set(rows.map(s => s.date))].sort();
  const successful = precise.filter(s => s.status === 'ok' && Number.isFinite(s.amount) && s.amount > 0);
  return {attempted_dates: dates(precise), precise_successful_dates: dates(successful),
    precise_successful_date_count: dates(successful).length, failed_dates: dates(precise.filter(s => s.status === 'failed')),
    range_hint_dates: [...new Set([...dates(samples.filter(s => s.stage === 'range' && s.status === 'ok')), ...(coverage?.returned_dates || [])])].sort(),
    reused_quote_dates: dates(samples.filter(reused)), quote_reuse_count: samples.filter(reused).length};
}

export function eventRoute(event) {
  if (event.data?.route) return event.data.route;
  const request = event.data?.request;
  return request?.origin && request?.destination ? `${request.origin}-${request.destination}` : null;
}

export function matchesRoute(event, opportunity, evidence = {}) {
  const route = eventRoute(event);
  if (route) return route === routeKey(opportunity);
  if (['goal', 'context', 'conclusion', 'stop', 'resume', 'source_availability'].includes(event.stage)) return true;
  const ids = new Set((opportunity.candidate.signals || []).map(s => s.evidence_id));
  if ((event.evidence_ids || []).some(id => ids.has(id))) return true;
  const queries = new Set([...ids].map(id => evidence[id]?.query).filter(Boolean));
  return Boolean(event.data?.query && queries.has(event.data.query));
}

export function scopedEvents(session, turn, opportunity = null) {
  const current = (turn?.events || []).map(event => ({event, inherited: false}));
  if (!opportunity) return current;
  const ids = new Set((opportunity.candidate.signals || []).map(s => s.evidence_id));
  const earlier = session.turns.slice(0, session.turns.findIndex(t => t.id === turn.id));
  // Follow-ups reuse community material. Bring back only linked original evidence,
  // never old fares or conclusions as current results.
  const inherited = earlier.flatMap((t, index) => (t.events || [])
    .filter(e => ['evidence', 'quality'].includes(e.stage) && (e.evidence_ids || []).some(id => ids.has(id)))
    .map(event => ({event, inherited: true, round: index + 1})));
  return [...inherited, ...current.filter(({event}) => matchesRoute(event, opportunity, session.evidence))];
}

export function validMessage(message) {
  return typeof message === 'string' && message.trim().length > 0 && message.length <= 3000;
}

export class ViewState {
  constructor() {
    this.sid = null;
    this.session = null;
    this.selectedTurn = null;
    this.activeSid = null;
    this.starting = false;
    this.epoch = 0;
    this.revision = 0;
  }
  select(id = null) {
    this.sid = id;
    this.session = null;
    this.selectedTurn = null;
    this.epoch += 1;
    this.revision = 0;
  }
  requestToken() { return {sid: this.sid, epoch: this.epoch, revision: ++this.revision}; }
  current(token) { return token.sid === this.sid && token.epoch === this.epoch && token.revision === this.revision; }
  accept(token, response) {
    if (!this.current(token) || response.session?.id !== this.sid) return false;
    this.session = response.session;
    this.activeSid = response.active || null;
    return true;
  }
  get turn() { return this.session?.turns.find(t => t.id === this.selectedTurn) || this.session?.turns.at(-1); }
  get waitingForBrowser() {
    const latest = this.session?.turns.at(-1);
    return ['partial','blocked'].includes(latest?.status) && latest?.checkpoint?.browser_recovery?.state === 'waiting';
  }
  get locked() { return this.starting || Boolean(this.activeSid); }
  get reportURL() {
    return this.sid && this.turn ? `/api/sessions/${encodeURIComponent(this.sid)}/report?turn=${encodeURIComponent(this.turn.id)}` : null;
  }
}
