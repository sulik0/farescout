import copy
from datetime import date

import pytest

from farescout.models import FareRequest, Opportunity
from farescout.providers import flyai_fares, serpapi_fares, socai_evidence
from farescout.report import synthesize
from farescout.safety import SourceFailure, clean_text, public_url
from test_research import candidate, evidence


def request(**values):
    return FareRequest(**(dict(origin="HKG", destination="NRT", outbound_date=date(2026, 11, 10)) | values))


def payload(price="¥1200.00", **segment_changes):
    segment = dict(depStationCode="HKG", arrStationCode="NRT", depDateTime="2026-11-10 10:00:00",
                   arrDateTime="2026-11-10 15:00:00", marketingTransportName="测试航司", marketingTransportNo="TEST1", seatClassName="经济舱")
    segment.update(segment_changes)
    return {"status": 0, "data": {"itemList": [{"adultPrice": price, "journeys": [{"segments": [segment]}]}]}}


def serp(price=1300):
    return {"search_metadata": {"status": "Success"},
            "search_parameters": {"departure_id": "HKG", "arrival_id": "NRT", "outbound_date": "2026-11-10", "currency": "CNY"},
            "best_flights": [{"price": price, "flights": [{
                "departure_airport": {"id": "HKG", "time": "2026-11-10 10:00"},
                "arrival_airport": {"id": "NRT", "time": "2026-11-10 15:00"}, "travel_class": "Economy",
            }]}]}


@pytest.mark.parametrize("changes", [{"arrStationCode": "HND"}, {"depStationCode": "SZX"},
                                     {"depDateTime": "2026-11-11 10:00:00"}, {"seatClassName": "公务舱"}])
def test_wrong_airport_date_or_cabin_never_verified(changes):
    assert flyai_fares(payload(**changes), request()) == []


@pytest.mark.parametrize("price", ["USD 1200", "¥1200起", "1200～1400", "0", "-100", "nan", "inf"])
def test_ambiguous_currency_or_price_never_verified(price):
    assert not flyai_fares(payload(price), request())


def test_runtime_ticket_price_schema():
    data = payload()
    item = data["data"]["itemList"][0]
    item["ticketPrice"] = item.pop("adultPrice").replace("¥", "")
    fares = flyai_fares(data, request())
    assert fares[0].amount == 1200
    assert fares[0].price_basis == "adult_fare_tax_unknown"


def test_socai_released_cli_shape_reads_entity_body_and_comments():
    payload = {"notes": [{"entity": {
        "note_id": "6abc6f1e0000000018029233",
        "url": "https://www.xiaohongshu.com/explore/6abc6f1e0000000018029233?xsec_token=private",
        "title": "香港飞冲绳",
        "content": "香港飞冲绳有促销，记得查日期。",
        "date": "5小时前 广东",
        "top_comments": ["优惠不可用", {"text": "换个日期", "replies": ["11月也试试"]}],
    }}]}
    records = socai_evidence(payload, "香港便宜国际机票")
    assert len(records) == 1
    assert records[0].body == "香港飞冲绳有促销，记得查日期。"
    assert [c.text for c in records[0].comments] == ["优惠不可用", "换个日期", "11月也试试"]
    assert records[0].url == "https://www.xiaohongshu.com/explore/6abc6f1e0000000018029233"


def test_red_eye_and_overnight_rejected_even_when_api_ignores_filter():
    req = request(no_red_eye=True)
    assert not flyai_fares(payload(depDateTime="2026-11-10 23:30:00", arrDateTime="2026-11-11 04:30:00"), req)
    assert not flyai_fares(payload(depDateTime="2026-11-10 21:00:00", arrDateTime="2026-11-11 07:00:00"), req)
    assert flyai_fares(payload(), req)


def test_one_way_cannot_be_misrepresented_as_round_trip():
    assert not flyai_fares(payload(), request(return_date=date(2026, 11, 15)))
    data = payload()
    item = data["data"]["itemList"][0]
    item["journeys"].append({"segments": [dict(depStationCode="NRT", arrStationCode="HKG", depDateTime="2026-11-15 10:00:00",
                                           arrDateTime="2026-11-15 14:00:00", seatClassName="经济舱")]})
    assert flyai_fares(data, request(return_date=date(2026, 11, 15)))
    assert not flyai_fares(data, request())
    with pytest.raises(SourceFailure):
        serpapi_fares(serp(), request(return_date=date(2026, 11, 15)))


def test_serp_requires_parameter_echo_and_valid_itinerary():
    assert serpapi_fares(serp(), request())[0].amount == 1300
    data = serp()
    data["search_parameters"]["currency"] = "HKD"
    with pytest.raises(SourceFailure):
        serpapi_fares(data, request())
    data = serp()
    data["best_flights"][0]["flights"][0]["arrival_airport"]["id"] = "HND"
    assert not serpapi_fares(data, request())


def test_price_basis_conflicts_not_merged_and_seen_price_not_current():
    op = Opportunity(candidate=candidate(), fares=flyai_fares(payload(), request()) + serpapi_fares(serp(), request()))
    synthesize(op, {"p1": evidence()})
    text = " ".join(op.comparison)
    assert "税费口径不同" in text
    assert "1200～1300" not in text
    assert "未认定复现社区低价" in text


def test_same_conditions_keep_range_when_sources_disagree():
    a = serpapi_fares(serp(), request())[0]
    b = a.model_copy(update={"source": "第二个测试票价渠道", "amount": 1450})
    op = Opportunity(candidate=candidate(), fares=[a, b])
    synthesize(op, {"p1": evidence()})
    assert any("1300～1450" in x for x in op.comparison)


def test_search_titles_alone_do_not_count_as_post_reads():
    card = {"note_id": "12345678", "title": "香港东京899", "url": "https://www.xiaohongshu.com/explore/12345678"}
    assert not socai_evidence({"notes": [card]}, "q")
    card["content"] = "香港飞东京往返899，行李另买。"
    card["url"] += "?xsec_token=secret&session_token=secret2"
    records = socai_evidence({"notes": [{"note": card, "comments": [{"content": "今天已经涨价", "date": "今天"}]}]}, "q")
    assert records[0].comments[0].text == "今天已经涨价"
    assert "secret" not in records[0].model_dump_json()


def test_secrets_and_transaction_links_never_enter_reports():
    assert public_url("https://example.com/payment?id=1") == ""
    assert public_url("https://user:password@example.com/a") == ""
    assert public_url("https://example.com/post?api_key=SECRET") == "https://example.com/post"
    assert "SECRET" not in clean_text("api_key=SECRET cookie=SECRET password=SECRET")
