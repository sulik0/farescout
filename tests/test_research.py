from datetime import date

from farescout.models import Candidate, Discovery, Evidence, Expansion, Signal
from farescout.research import evolve_goal, grounded


def evidence():
    return Evidence(id="p1", source="小红书", url="https://www.xiaohongshu.com/explore/12345678", query="深圳 香港 便宜机票",
                    title="香港飞东京", body="香港快运从香港去东京，往返899元，2026-11-10。")


def candidate(**updates):
    values = dict(origin="HKG", destination="NRT", destination_name="东京", country="JP",
                  signals=[Signal(evidence_id="p1", excerpt="香港快运从香港去东京，往返899元", seen_price_text="899元")],
                  why="社区出现具体路线和晒价，值得继续调查")
    return Candidate(**(values | updates))


def test_multiturn_preserves_origins_region_and_month():
    goal = None
    for message in ["深圳香港便宜国际机票", "日本呢？", "11 月呢？", "不要红眼"]:
        goal = evolve_goal(message, goal, date(2026, 9, 30))
    assert goal.origins == ["SZX", "HKG"]
    assert goal.region == "JP"
    assert (goal.date_from, goal.date_to) == (date(2026, 11, 1), date(2026, 11, 30))
    assert goal.no_red_eye


def test_month_rolls_into_next_year_and_exclude_hkg():
    goal = evolve_goal("深圳香港便宜机票", today=date(2026, 12, 20))
    goal = evolve_goal("2月呢，香港机场太麻烦", goal, date(2026, 12, 20))
    assert goal.origins == ["SZX"]
    assert goal.date_to == date(2027, 2, 28)


def test_expansion_must_come_from_read_body_and_be_in_query():
    source = evidence()
    valid = Expansion(query="香港快运 东京 11月 促销", discovered_term="香港快运", evidence_id="p1", reason="正文提到航司")
    invented = Expansion(query="宿务航空 马尼拉 促销", discovered_term="宿务航空", evidence_id="p1", reason="猜的")
    goal = evolve_goal("深圳香港便宜国际机票", today=date(2026, 9, 30))
    result = grounded(Discovery(candidates=[candidate()], expansions=[valid, invented]), {"p1": source}, goal)
    assert len(result.candidates) == 1
    assert result.expansions == [valid]


def test_hallucinated_source_excerpt_route_and_price_are_rejected():
    source = evidence()
    goal = evolve_goal("深圳香港便宜国际机票", today=date(2026, 9, 30))
    nonexistent = candidate(signals=[Signal(evidence_id="fake", excerpt="香港快运从香港去东京")])
    wrong_route = candidate(destination="CDG")
    invented_excerpt = candidate(signals=[Signal(evidence_id="p1", excerpt="香港飞东京目前只要500")])
    assert not grounded(Discovery(candidates=[nonexistent, wrong_route, invented_excerpt]), {"p1": source}, goal).candidates
    wrong_price = candidate(signals=[Signal(evidence_id="p1", excerpt="香港快运从香港去东京", seen_price_text="500元")])
    result = grounded(Discovery(candidates=[wrong_price]), {"p1": source}, goal)
    assert result.candidates[0].signals[0].seen_price_text is None


def test_followup_filters_country_but_keeps_evidence():
    source = evidence()
    source.body += "香港往返马尼拉也有活动。"
    manila = candidate(destination="MNL", country="PH", signals=[Signal(evidence_id="p1", excerpt="香港往返马尼拉也有活动")])
    goal = evolve_goal("日本呢", today=date(2026, 9, 30))
    result = grounded(Discovery(candidates=[candidate(), manila]), {"p1": source}, goal)
    assert [c.destination for c in result.candidates] == ["NRT"]


def test_publication_age_is_not_retrieval_age():
    from datetime import datetime, timezone
    from farescout.research import publication_time
    recent = evidence().model_copy(update={'observed_at': datetime(2026, 9, 30, tzinfo=timezone.utc), 'published_at': '5小时前 广东'})
    old = recent.model_copy(update={'published_at': '2025-05-16'})
    unknown = recent.model_copy(update={'published_at': None})
    assert publication_time(recent) > publication_time(old) > publication_time(unknown)
