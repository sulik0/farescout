"""Export recorded research facts, never substitute for a live run."""
import argparse
import json
from pathlib import Path
from farescout.engine import Store


def audit(session):
    turn = session.turns[-1]
    routes = []
    for opportunity in turn.opportunities:
        coverage = opportunity.date_coverage
        # Preserve a verifiable itinerary for every successful exact day, not
        # only the selected day. Range samples and reuse never supply quotes.
        exact = {}
        successful = coverage.research_state['precise_successful_dates'] if coverage else []
        for rows in turn.checkpoint.get('quotes', {}).values():
            for fare in rows:
                req = fare['request']
                if (req['origin'] != opportunity.candidate.origin or req['destination'] != opportunity.candidate.destination
                        or req['outbound_date'] not in successful):
                    continue
                key = (fare['source'], req['outbound_date'], fare['price_basis'], fare['currency'])
                if key not in exact or fare['amount'] < exact[key]['amount']:
                    exact[key] = fare
        routes.append({
            "route": opportunity.candidate.key,
            "evidence_ids": list(dict.fromkeys(s.evidence_id for s in opportunity.candidate.signals)),
            "window": [str(turn.goal.date_from), str(turn.goal.date_to)],
            "precise_requested_dates": coverage.research_state['attempted_dates'] if coverage else [],
            "precise_successful_dates": coverage.research_state['precise_successful_dates'] if coverage else [],
            "range_returned_dates": list(map(str, coverage.returned_dates)) if coverage else [],
            "date_research_state": coverage.research_state if coverage else None,
            "precise_success_quotes": list(exact.values()),
            "selected_date": str(coverage.selected_date) if coverage else None,
            "fares": [f.model_dump(mode='json') for f in opportunity.fares],
            "deal": opportunity.deal,
        })
    return {
        "kind": "recorded_live_research_audit",
        "session_id": session.id, "turn_id": turn.id, "input": turn.user_input,
        "started_at": turn.started_at.isoformat(), "finished_at": turn.finished_at.isoformat() if turn.finished_at else None,
        "status": turn.status, "stop_reason": turn.stop_reason, "metrics": turn.metrics,
        "grounding_evidence_count": len({s.evidence_id for o in turn.opportunities for s in o.candidate.signals}),
        "dual_current_source_routes": sum(len({f.source for f in o.fares}) >= 2 for o in turn.opportunities),
        "call_count_definition": "community_calls=provider search invocations; socai_commands=actual CLI commands (search/read/status/retries); date_calls=range/coarse/fine invocations; verification_calls=actual final exact provider invocations; quote_reuses=same-turn quote reuse without an API request; model_requests=Pydantic AI recorded requests including retries; stage_*_seconds=request duration sums, parent community stages include read children; date_phase=actual date-stage wall time",
        "evidence_groups": [{"id":e.id, "source": e.source, "url": e.url, "title": e.title,
            "observed_at": e.observed_at.isoformat(), "group":e.quality.get('independence_group'),
            "duplicate_of":e.quality.get('duplicate_of'), "campaign_duplicate_of":e.quality.get('campaign_duplicate_of'),
            "match_basis":e.quality.get('campaign_match_basis',[])} for e in session.evidence.values()],
        "expansions": [e.model_dump(mode='json') for e in turn.expansions],
        "research_trace": [e.model_dump(mode="json") for e in turn.events if e.stage in {"browser_connection", "browser_recovery", "research_decision", "checkpoint", "result_available", "resume", "source_availability", "date_plan", "date_selected", "coverage"}],
        "browser_recovery": turn.checkpoint.get("browser_recovery"),
        "recovery_required": turn.checkpoint.get("recovery_required"),
        "failures": [e.model_dump(mode='json') for e in turn.events if e.status == 'failed'],
        "sources": sorted({e.source for e in turn.events if e.source}),
        "source_availability": turn.checkpoint.get("source_availability", {}),
        "routes": routes,
        "not_a_month_minimum": True,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True)
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    session = Store(Path(args.data_dir)).load(args.session)
    if not session or not session.turns:
        raise SystemExit('session not found')
    Path(args.output).write_text(json.dumps(audit(session), ensure_ascii=False, indent=2))
