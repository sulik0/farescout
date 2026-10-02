"""Isolate live date-loop performance on historical, evidence-grounded routes.

This is NOT a fresh community study or a cold-start end-to-end acceptance run.
Run in separate processes with PYTHONPATH selecting the old or new implementation.
"""
import argparse
import asyncio
import json
from pathlib import Path
from time import monotonic

from farescout.config import Settings
from farescout.dates import DateExplorer
from farescout.engine import Researcher
from farescout.models import Opportunity, Session, Turn, now


async def run(label, reference, output):
    settings = Settings.from_env()
    previous = Session.model_validate_json(Path(reference).read_text())
    session = Session(id=label, goal=previous.goal, evidence=previous.evidence)
    turn = Turn(id=label, user_input='仅测试历史有证据路线的实时日期探索；不是新社区研究', goal=session.goal,
                opportunities=[Opportunity(candidate=o.candidate) for o in previous.turns[0].opportunities])
    session.turns.append(turn)
    researcher = Researcher(settings)
    researcher._session = session
    started = monotonic()
    await DateExplorer(researcher, turn).run(turn.opportunities)
    turn.finished_at = now()
    turn.status = 'partial'
    turn.stop_reason = '日期阶段独立实测；没有重新读取社区或运行Agent，不能作为端到端成功'
    turn.metrics['elapsed_seconds'] = round(monotonic()-started,3)
    turn.metrics['verified_routes'] = sum(bool(o.fares) for o in turn.opportunities)
    Path(output).write_text(session.model_dump_json(indent=2))
    print(json.dumps(turn.metrics, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--label', required=True)
    p.add_argument('--reference', default='reports/p1-core-session.json')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    asyncio.run(run(a.label, a.reference, a.output))
