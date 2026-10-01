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
        routes.append({
            "route": opportunity.candidate.key,
            "evidence_ids": list(dict.fromkeys(s.evidence_id for s in opportunity.candidate.signals)),
            "window": [str(turn.goal.date_from), str(turn.goal.date_to)],
            "precise_requested_dates": sorted({str(s.date) for s in coverage.samples if s.stage != 'range'}) if coverage else [],
            "precise_successful_dates": sorted({str(s.date) for s in coverage.samples if s.stage != 'range' and s.status == 'ok'}) if coverage else [],
            "range_returned_dates": list(map(str, coverage.returned_dates)) if coverage else [],
            "selected_date": str(coverage.selected_date) if coverage else None,
            "fares": [f.model_dump(mode='json') for f in opportunity.fares],
            "deal": opportunity.deal,
        })
    return {
        "kind": "recorded_live_research_audit",
        "session_id": session.id, "turn_id": turn.id, "input": turn.user_input,
        "started_at": turn.started_at.isoformat(), "finished_at": turn.finished_at.isoformat() if turn.finished_at else None,
        "status": turn.status, "stop_reason": turn.stop_reason, "metrics": turn.metrics,
        "call_count_definition": "community_calls=provider search invocations; socai_commands=actual CLI search attempts; date_calls=range/coarse/fine provider invocations; verification_calls=final exact provider invocations; model_requests=Pydantic AI recorded requests (including retries), not model_operations",
        "expansions": [e.model_dump(mode='json') for e in turn.expansions],
        "failures": [e.model_dump(mode='json') for e in turn.events if e.status == 'failed'],
        "sources": sorted({e.source for e in turn.events if e.source}),
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
