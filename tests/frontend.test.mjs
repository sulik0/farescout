import test from 'node:test';
import assert from 'node:assert/strict';
import {ViewState, bestFare, coverageDates, scopedEvents, validMessage} from '../src/farescout/ui-state.mjs';

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
