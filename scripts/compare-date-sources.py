"""Probe existing date sources with real requests; discoveries are not verified fares."""
import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from time import monotonic

import httpx

from farescout.config import Settings
from farescout.models import FareRequest
from farescout.providers import FlyAI, SerpAPI
from farescout.research import evolve_goal
from farescout.safety import source_error


async def compare(output):
    settings = Settings.from_env()
    goal = evolve_goal('香港 11 月飞日本哪里便宜？')
    results = []
    exact = SerpAPI(settings)
    for destination in ['KIX', 'NRT', 'CTS']:
        for engine in ['FlyAI range', 'google_travel_explore', 'google_flights_deals']:
            start = monotonic()
            record = {'source': engine, 'route': f'HKG-{destination}', 'calls': 1, 'hints': []}
            try:
                if engine == 'FlyAI range':
                    samples = await FlyAI(settings).explore('HKG', destination, goal)
                    record['hints'] = [dict(date=str(s.date), amount=s.amount, basis=s.price_basis) for s in samples]
                else:
                    params = dict(engine=engine, departure_id='HKG', type='2', currency='CNY', hl='en',
                                  adults='1', travel_class='1', no_cache='true', api_key=settings.serpapi_key)
                    if engine == 'google_travel_explore':
                        params.update(arrival_id=destination, month=goal.date_from.month)
                    else:
                        params.update(query={'KIX':'Osaka', 'NRT':'Tokyo', 'CTS':'Sapporo'}[destination],
                                      outbound_date=f'{goal.date_from},{goal.date_to}')
                    async with httpx.AsyncClient(timeout=settings.source_timeout) as client:
                        response = await client.get('https://serpapi.com/search.json', params=params)
                        response.raise_for_status()
                        payload = response.json()
                    record['response_fields'] = sorted(payload.keys())
                    record['search_status'] = payload.get('search_metadata', {}).get('status')
                    record['returned_conditions'] = {k:v for k,v in payload.get('search_parameters', {}).items()
                        if k in ['engine','departure_id','arrival_id','type','month','outbound_date','return_date','currency','query']}
                    record['top_dates'] = {k:payload[k] for k in ['start_date','end_date'] if k in payload}
                    # Store only public date/route/price facts, never raw provider URLs or credentials.
                    record['provider_error'] = bool(payload.get('error'))
                    for item in payload.get('destinations', payload.get('deals', [])):
                        if not isinstance(item, dict):
                            continue
                        record['hints'].append({k:item[k] for k in ['name','destination_name','country', 'departure_airport_code',
                            'arrival_airport_code','start_date','end_date','outbound_date','return_date','price','flight_price','average_price',
                            'discount_percentage','airport_id'] if k in item})
                    for item in payload.get('flights', []):
                        if isinstance(item, dict):
                            hint = {k:item[k] for k in ['start_date','end_date','flight_price','price'] if k in item}
                            hint.update(record['top_dates'])
                            hint.update(departure_airport_code=item.get('departure_airport',{}).get('id'),
                                        arrival_airport_code=item.get('arrival_airport',{}).get('id'))
                            record['hints'].append(hint)
                record['status'] = 'ok' if record['hints'] else 'empty'
            except Exception as error:
                record.update(status='failed', reason=str(source_error(engine, error)))
            record['seconds'] = round(monotonic()-start, 3)
            results.append(record)
            Path(output).write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(engine, destination, record['status'], record['seconds'], flush=True)
    # Compare the existing coarse sample on one route. Only exact quotes count as prices.
    for day in [1, 15, 30]:
        start = monotonic()
        request = FareRequest(origin='HKG', destination='KIX', outbound_date=date(goal.date_from.year, 11, day))
        record = {'source':'google_flights exact', 'route':'HKG-KIX', 'date':str(request.outbound_date), 'calls':1}
        try:
            fares = await exact.verify(request)
            record.update(status='ok', fares=[f.model_dump(mode='json') for f in fares])
        except Exception as error:
            record.update(status='failed', reason=str(source_error('SerpAPI', error)))
        record['seconds'] = round(monotonic()-start,3)
        results.append(record)
        Path(output).write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print('exact', day, record['status'], record['seconds'], flush=True)
    # Verify a bounded number of returned date leads; mismatched windows/trip types remain rejected.
    seen = {('KIX',str(date(goal.date_from.year,11,day))) for day in [1,15,30]}
    for record in list(results):
        destination = record['route'].split('-')[-1]
        eligible = []
        for hint in record.get('hints', []):
            raw = hint.get('date', hint.get('start_date', hint.get('outbound_date')))
            try:
                day = date.fromisoformat(str(raw))
            except ValueError:
                continue
            if goal.date_from <= day <= goal.date_to:
                eligible.append(day)
        record['in_window_dates'] = sorted(set(map(str,eligible)))
        if record['source'] == 'google_flights_deals':
            record['return_dates_present'] = any(h.get('return_date') for h in record.get('hints', []))
            if record['return_dates_present']:
                continue
        if not eligible:
            continue
        day = eligible[0]
        if (destination,str(day)) in seen:
            continue
        seen.add((destination,str(day)))
        start = monotonic()
        check = {'source':'google_flights hint verification', 'hint_source':record['source'],
                 'route':record['route'], 'date':str(day), 'calls':1}
        try:
            fares = await exact.verify(FareRequest(origin='HKG', destination=destination, outbound_date=day))
            check.update(status='ok', fares=[f.model_dump(mode='json') for f in fares])
        except Exception as error:
            check.update(status='failed', reason=str(source_error('SerpAPI', error)))
        check['seconds'] = round(monotonic()-start,3)
        results.append(check)
    Path(output).write_text(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/p15-date-comparison.json')
    asyncio.run(compare(parser.parse_args().output))
