import asyncio
from datetime import date

import pytest

from farescout.config import Settings
from farescout.engine import Researcher, Store
from farescout.models import Candidate, Discovery, Expansion, Signal
from farescout.providers import flyai_fares
from farescout.research import grounded
from farescout.safety import SourceFailure
from test_prices import payload
from test_research import candidate, evidence


class TestBrain:
    __test__ = False

    async def patch(self, message, goal):
        return goal

    async def plan(self, message, goal):
        return ["香港 便宜机票", "深圳 国际机票"]

    async def discover(self, goal, sources):
        return grounded(Discovery(candidates=[candidate()], expansions=[Expansion(
            query="香港快运 东京 促销", discovered_term="香港快运", evidence_id="p1", reason="已读正文提到航司",
        )]), sources, goal)


class FailedSocial:
    name = "受阻的小红书测试适配器"

    async def search(self, query):
        raise SourceFailure(self.name, "ACCESS_BLOCKED", "验证码；不可绕过")


class WorkingSocial:
    name = "备用测试社区"

    async def search(self, query):
        e = evidence()
        e.query = query
        return [e]


class FailedFare:
    name = "故障票价测试源"

    async def verify(self, req):
        raise TimeoutError()


class WorkingFare:
    name = "备用票价测试源"

    async def verify(self, req):
        data = payload(depDateTime=f"{req.outbound_date} 10:00:00", arrDateTime=f"{req.outbound_date} 15:00:00")
        return flyai_fares(data, req)


async def test_fallback_expansion_persistence_and_current_price_refresh(tmp_path):
    researcher = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(),
                            social=[FailedSocial(), WorkingSocial()], fares=[FailedFare(), WorkingFare()])
    session = await researcher.run("深圳香港便宜国际机票", None, "a")
    first = session.turns[-1]
    assert first.status == "partial"  # one route isn't inflated into 3–5.
    assert len([x for x in first.events if x.stage == "community_search" and x.status == "ok"]) == 2
    assert first.expansions[0].discovered_term == "香港快运"
    assert first.opportunities[0].fares
    assert any(x.status == "failed" and x.source == FailedFare.name for x in first.events)
    store = Store(tmp_path)
    store.save(session)
    restored = store.load("a")
    assert restored.evidence["p1"].body == evidence().body
    session = await researcher.run("日本呢？", restored, "a")
    session = await researcher.run("11 月呢？", session, "a")
    session = await researcher.run("不要红眼", session, "a")
    assert session.goal.region == "JP"
    assert session.goal.origins == ["SZX", "HKG"]
    assert session.goal.no_red_eye
    assert session.goal.date_from.month == 11
    assert len(session.turns) == 4
    assert session.turns[-1].opportunities[0].fares[0].observed_at > first.opportunities[0].fares[0].observed_at


async def test_no_sources_does_not_fabricate_candidates(tmp_path):
    researcher = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[FailedSocial()], fares=[WorkingFare()])
    session = await researcher.run("深圳香港便宜国际机票", None, "a")
    assert session.turns[-1].status == "blocked"
    assert not session.turns[-1].opportunities


def test_session_path_cannot_escape_data_dir(tmp_path):
    with pytest.raises(ValueError):
        Store(tmp_path).load("../../credentials")


async def test_timeout_during_expansion_keeps_discovered_candidates(tmp_path):
    class SlowExpansion(WorkingSocial):
        async def search(self, query):
            if '香港快运' in query:
                await asyncio.sleep(2)
            return await super().search(query)
    researcher = Researcher(Settings(data_dir=tmp_path, max_seconds=0.05), brain=TestBrain(),
                            social=[SlowExpansion()], fares=[])
    session = await researcher.run('深圳香港便宜国际机票', None, 'timed')
    assert session.turns[-1].opportunities[0].candidate.key == 'HKG-NRT'
    assert '时间预算' in session.turns[-1].stop_reason
