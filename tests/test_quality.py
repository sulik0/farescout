from datetime import date

import pytest

from farescout.engine import Store
from farescout.models import DateCoverage, DateSample, Opportunity, Session, Turn
from farescout.providers import serpapi_fares
from farescout.quality import assess_evidence, deal_strength
from farescout.research import evolve_goal
from test_prices import request, serp
from test_research import candidate, evidence


def test_commercial_duplicate_and_image_labels_do_not_assert_falsehood():
    a = evidence().model_copy(update={'body': '香港飞东京机票促销，价格见图，私信我找我订。' * 5})
    b = a.model_copy(update={'id': 'copy'})
    assess_evidence({'a': a, 'b': b}, today=date(2026, 10, 1))
    assert a.quality['commercial_signals'] == ['私信我', '找我订']
    assert a.quality['image_dependent']
    assert b.quality['independence_group'] == a.quality['independence_group']
    assert b.quality['duplicate_of'] == a.id
    assert '不等于虚假' in a.quality['flags'][0]


def test_generated_independence_claim_does_not_change_original_excerpt():
    from farescout.research import grounded
    from farescout.models import Discovery
    c = candidate().model_copy(update={'why':'多篇独立社区帖与独立讨论，但需要实时验价'})
    excerpt = c.signals[0].excerpt
    d = grounded(Discovery(candidates=[c]), {'p1':evidence()}, evolve_goal('香港日本11月'))
    assert '独立' not in d.candidates[0].why
    assert d.candidates[0].signals[0].excerpt == excerpt


def test_only_explicit_sale_end_can_be_expired():
    a = evidence().model_copy(update={'body': '优惠日期2026年9月30日至10月11日'})
    b = evidence().model_copy(update={'id': 'full', 'body': '销售期2026年9月17日至2026年9月20日\n出行至2027年1月'})
    assess_evidence({'a': a, 'b': b}, today=date(2026, 10, 1))
    assert a.quality['sales_end'] == '未确认'
    assert b.quality['sales_end'] == '2026-09-20'
    assert any('销售期已过' in f for f in b.quality['flags'])


def test_sponsorship_and_sale_without_year_are_uncertain_not_current_deal():
    a = evidence().model_copy(update={'body': '感谢赞助商trip.com\n抢票时间：9月17日～9月20日\n出发日期2026/9/22～2027/1/31'})
    assess_evidence({'a': a}, today=date(2026, 10, 1))
    assert a.quality['commercial_signals'] == ['赞助商']
    assert a.quality['sales_end'] == '未确认'
    assert any('不能断言仍有效' in flag for flag in a.quality['flags'])


@pytest.mark.parametrize('bounds', [None, [], [900], [1200, 900], [True, 1800], [float('nan'), 1800], [-2, 1800]])
def test_invalid_insights_never_create_discount(bounds):
    p = serp(800)
    p['price_insights'] = {'typical_price_range': bounds, 'lowest_price': 800}
    f = serpapi_fares(p, request())[0]
    assert f.price_insights == {}
    assert deal_strength(Opportunity(candidate=candidate(), fares=[f]))['level'] == 'unknown'


@pytest.mark.parametrize('amount,level', [(800, 'below_typical'), (1100, 'typical'), (1900, 'above_typical')])
def test_deal_compares_same_source_and_request(amount, level):
    p = serp(amount)
    p['price_insights'] = {'typical_price_range': [1000, 1800], 'lowest_price': amount, 'price_level': 'low'}
    f = serpapi_fares(p, request())[0]
    deal = deal_strength(Opportunity(candidate=candidate(), fares=[f]))
    assert deal['level'] == level and deal['fare_id'] == f.id
    assert deal['request']['outbound_date'] == '2026-11-10'


def test_red_eye_filter_and_price_mismatch_disable_baseline():
    p = serp(1100)
    p['price_insights'] = {'typical_price_range': [1200, 1800], 'lowest_price': 800}
    assert not serpapi_fares(p, request())[0].price_insights['comparable']
    p['price_insights']['lowest_price'] = 1100
    f = serpapi_fares(p, request(no_red_eye=True))[0]
    assert not f.price_insights['comparable']
    assert deal_strength(Opportunity(candidate=candidate(), fares=[f]))['level'] == 'unknown'


def test_loading_legacy_samples_never_fabricates_observation_time(tmp_path):
    goal = evolve_goal('香港11月日本', today=date(2026, 10, 1))
    s = Session(id='legacy', goal=goal, turns=[Turn(id='t', user_input='q', goal=goal,
        opportunities=[Opportunity(candidate=candidate(), date_coverage=DateCoverage(
            date_from=goal.date_from, date_to=goal.date_to,
            samples=[DateSample(date=goal.date_from, source='test', stage='coarse', status='ok')]))])])
    data = s.model_dump(mode='json')
    data['turns'][0]['opportunities'][0]['date_coverage']['samples'][0].pop('observed_at')
    import json
    (tmp_path/'legacy.json').write_text(json.dumps(data))
    loaded = Store(tmp_path).load('legacy')
    assert loaded.turns[0].opportunities[0].date_coverage.samples[0].observed_at is None
