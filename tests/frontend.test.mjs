import test from 'node:test';
import assert from 'node:assert/strict';
import {ViewState, bestFare, coverageDates, dateResearchState, scopedEvents, validMessage} from '../src/farescout/ui-state.mjs';

const opportunity = {candidate:{origin:'HKG',destination:'KIX',signals:[{evidence_id:'e1'}]},fares:[]};
const response = (id, turns = [{id:'t1',events:[]}], active = null) => ({session:{id,turns,evidence:{}},active});

test('a late response cannot replace a different selected session', async () => {
  const state = new ViewState(); state.select('first'); const first = state.requestToken();
  state.select('second'); const second = state.requestToken();
  assert.equal(state.accept(second, response('second')), true);
  await Promise.resolve();
  assert.equal(state.accept(first, response('first','', 'first')), false);
  assert.equal(state.sid, 'second'); assert.equal(state.session.id, 'second'); assert.equal(state.activeSid, null);
});
test('overlapping snapshots accept only the newest request for the same view', () => {
  const state = new ViewState(); state.select('first'); const old = state.requestToken(), recent = state.requestToken();
  assert.equal(state.accept(recent, response('first',[{id:'latest'}])), true);
  assert.equal(state.accept(old, response('first',[{id:'stale'}])), false);
  assert.equal(state.turn.id, 'latest');
});
test('new research clears the report and selected turn but keeps the global running lock', () => {
  const state = new ViewState(); state.select('first'); state.accept(state.requestToken(), response('first', [{id:'t1'}], 'first'));
  assert.equal(state.locked, true); assert.ok(state.reportURL);
  state.select(); assert.equal(state.reportURL, null); assert.equal(state.turn, undefined); assert.equal(state.locked, true);
});
test('viewing an old round produces the report for that round', () => {
  const state = new ViewState(); state.select('first'); state.accept(state.requestToken(), response('first', [{id:'t1'},{id:'t2'}]));
  assert.ok(state.reportURL.endsWith('turn=t2')); state.selectedTurn = 't1'; assert.ok(state.reportURL.endsWith('turn=t1'));
});
test('a reloaded waiting session keeps listening for authorization, even while an older round is viewed', () => {
  const state = new ViewState(); state.select('saved');
  const turns = [{id:'old',status:'complete'}, {id:'paused',status:'blocked',checkpoint:{browser_recovery:{state:'waiting'}}}];
  state.accept(state.requestToken(), response('saved',turns));
  state.selectedTurn = 'old';
  assert.equal(state.activeSid, null);
  assert.equal(state.waitingForBrowser, true);
  state.accept(state.requestToken(), response('saved',[turns[0],{...turns[1],checkpoint:{browser_recovery:{state:'expired'}}}]));
  assert.equal(state.waitingForBrowser, false);
  state.accept(state.requestToken(), response('saved',[turns[0],{...turns[1],status:'running',checkpoint:{browser_recovery:{state:'resumed'}}}], 'saved'));
  assert.equal(state.waitingForBrowser, false);
  assert.equal(state.locked, true);
  state.select('other');
  assert.equal(state.waitingForBrowser, false);
});
test('a cheaper tax-unknown quote never displaces a tax-inclusive headline', () => {
  const taxed = {id:'taxed',amount:850,price_basis:'total_including_taxes',request:{outbound_date:'2026-11-04'}};
  const unknown = {id:'unknown',amount:816,price_basis:'adult_fare_tax_unknown',request:{outbound_date:'2026-11-30'}};
  const selected = bestFare({...opportunity,fares:[unknown,taxed]});
  assert.equal(selected, taxed); assert.equal(selected.request.outbound_date, '2026-11-04');
  assert.equal(bestFare(opportunity), null);
});
test('range hints do not count as exact date coverage; failed exact requests remain visible', () => {
  assert.deepEqual(coverageDates({samples:[{date:'2026-11-01',stage:'range',status:'ok'}, {date:'2026-11-04',stage:'coarse',status:'failed'}, {date:'2026-11-05',stage:'fine',status:'ok'}, {date:'2026-11-05',stage:'verification',status:'ok'}]}), ['2026-11-04','2026-11-05']);
});
test('route trace contains linked evidence and failures, excludes another route', () => {
  const turn = {id:'t1',events:[{id:'goal',stage:'goal'},{id:'evidence',stage:'evidence',evidence_ids:['e1']},{id:'mine',stage:'fare',status:'failed',data:{route:'HKG-KIX'}},{id:'other',stage:'fare',data:{route:'HKG-OKA'}},{id:'end',stage:'conclusion'}]};
  assert.deepEqual(scopedEvents({turns:[turn],evidence:{}},turn,opportunity).map(x=>x.event.id), ['goal','evidence','mine','end']);
});
test('follow-ups can trace inherited evidence without showing old fares as current', () => {
  const old = {id:'t1',events:[{id:'evidence',stage:'evidence',evidence_ids:['e1']},{id:'oldfare',stage:'fare',data:{route:'HKG-KIX'}},{id:'oldend',stage:'conclusion'}]};
  const current = {id:'t2',events:[{id:'newfare',stage:'fare',data:{route:'HKG-KIX'}}]};
  const events = scopedEvents({turns:[old,current],evidence:{}},current,opportunity);
  assert.deepEqual(events.map(x=>x.event.id), ['evidence','newfare']); assert.equal(events[0].inherited, true); assert.equal(events[0].round, 1);
});
test('empty or oversized messages cannot create a session', () => {
  assert.equal(validMessage('  '), false); assert.equal(validMessage('a'.repeat(3001)), false); assert.equal(validMessage('香港11月日本'), true);
});

test('date state keeps attempts, success, failure, range and reuse separate', () => {
  const sample = (date, changes = {}) => ({date, stage:'coarse', status:'ok', amount:800, ...changes});
  const coverage = {samples:[sample('2026-11-04'), sample('2026-11-04', {source:'other'}),
    sample('2026-11-05', {status:'failed', amount:null}), sample('2026-11-06', {stage:'range'}),
    sample('2026-11-07', {reused:true, request_issued:false}), sample('2026-11-08', {detail:'复用本轮同条件报价'})]};
  const state = dateResearchState(coverage);
  assert.deepEqual(coverageDates(coverage), ['2026-11-04','2026-11-05']);
  assert.deepEqual(state.precise_successful_dates, ['2026-11-04']);
  assert.deepEqual(state.failed_dates, ['2026-11-05']);
  assert.deepEqual(state.range_hint_dates, ['2026-11-06']);
  assert.deepEqual(state.reused_quote_dates, ['2026-11-07','2026-11-08']);
  assert.equal(state.quote_reuse_count, 2);
});
