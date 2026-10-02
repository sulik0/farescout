from __future__ import annotations

import re
from difflib import SequenceMatcher
from datetime import date, datetime, timezone

from .models import identity
from .research import publication_time, today_local


def campaign_anchors(text):
    """Only explicit common campaign facts can link differently worded posts."""
    airlines = {"peach": r"peach|乐桃|樂桃", "hkexpress": r"香港快运|香港快運|hk\s*express", "airasia": r"亚航|亞航|airasia",
                "greaterbay": r"greater\s*bay\s*airlines|大湾区(?:航空|促销|日本航点)|大灣區航空",
                "hongkongairlines": r"hong\s*kong\s*airlines|香港航空"}
    found = [key for key, pattern in airlines.items() if re.search(pattern, text, re.I)]
    if len(found) != 1:
        return set()
    anchors = {"airline:" + found[0]}
    for label, words in [("sale", ["优惠日期", "销售期", "售票日期", "抢票时间", "搶票時間"]),
                         ("travel", ["出行日期", "出发日期", "出發日期", "旅行日期"] )]:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if not any(w in line for w in words):
                continue
            dates = re.findall(r"(?:(20\d{2})[年/.-])?(\d{1,2})[月/.-](\d{1,2})日?", line)
            if len(dates) < 2:
                dates = re.findall(r"(?:(20\d{2})[年/.-])?(\d{1,2})[月/.-](\d{1,2})日?", ' '.join(lines[index:index+3]))
            if len(dates) >= 2:
                anchors.add(label + ':' + '|'.join('-'.join(parts) for parts in dates[:2]))
    for url in re.findall(r'https://[^\s<>]+', text):
        from .safety import public_url
        safe = public_url(url)
        if re.search(r'https://(?:[^/]+\.)?(?:flypeach\.com|hkexpress\.com|airasia\.com)/.+', safe):
            anchors.add('official:' + safe)
    return anchors


def assess_evidence(evidence, today=None):
    """Explainable text heuristics, not account credibility or a truth score."""
    today = today or today_local()
    groups = []
    group_anchors = {}
    for item in evidence.values():
        text = item.body
        normalized = re.sub(r"\s+|#[^\s#]+", "", text).lower()
        anchors = campaign_anchors(text)
        def conflicts(previous):
            return any({a for a in anchors if a.startswith(label)} and {a for a in previous if a.startswith(label)}
                       and {a for a in anchors if a.startswith(label)} != {a for a in previous if a.startswith(label)}
                       for label in ['airline:', 'sale:', 'travel:'])
        duplicate = next((other for other, body in groups if len(normalized) >= 50 and
                          not conflicts(group_anchors[other.quality['independence_group']]) and
                          (normalized == body or SequenceMatcher(None, normalized, body).ratio() >= .9)), None)
        campaign = None
        match_basis = []
        for other, body in groups:
            previous = campaign_anchors(other.body)
            shared = anchors & previous
            conflict = conflicts(group_anchors[other.quality['independence_group']])
            if not conflict and any(a.startswith('airline:') for a in shared) and (
                    any(a.startswith('sale:') for a in shared) and any(a.startswith('travel:') for a in shared)
                    or any(a.startswith('official:') for a in shared) and any(a.startswith('sale:') for a in shared)):
                campaign, match_basis = other, sorted(shared)
                break
        related = duplicate or campaign
        group = related.quality['independence_group'] if related else identity(normalized)
        group_anchors.setdefault(group, set()).update(anchors)
        commercial = [w for w in ['私信我', '找我订', '代订', '加微信', '返佣', '代理售票', '联系出票', '赞助商', '付费推广', '广告合作'] if w in text]
        image = any(w in text for w in ['价格见图', '看截图', '看图', '图中价格', '图上价格'])
        pub = publication_time(item)
        age = (datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).timestamp()-pub)/86400 if pub else None
        sales_line = next((line for line in text.splitlines() if any(w in line for w in
                         ['优惠日期', '销售期', '售票日期', '抢票日期', '抢票时间', '活动截止']) and not any(w in line for w in ['出行', '出发'])), '')
        # Only fully specified source dates may create a definite expiry label.
        explicit = re.findall(r'(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})(?:日)?', sales_line)
        sales_end = None
        if len(explicit) >= 2 or (len(explicit) == 1 and '截止' in sales_line):
            try:
                sales_end = date(*map(int, explicit[-1]))
            except ValueError:
                pass
        flags = []
        if commercial:
            flags.append('出现商业/导流关键词；不等于虚假')
        if duplicate:
            flags.append('疑似同文转载；不重复计作独立佐证')
        elif campaign:
            flags.append('正文不同但活动线索相同；按同一促销计数，作者关系未知')
        if image:
            flags.append('价格可能依赖未分析图片')
        if age is not None and age > 90:
            flags.append('帖子超过90天；只保留为待验证线索')
        if sales_end and sales_end < today:
            flags.append('原文明确销售期已过；当前价需重新确认')
        elif sales_line and not sales_end:
            flags.append('销售期日期/年份未完全确认；不能断言仍有效')
        if not pub:
            flags.append('发帖时间未知')
        item.quality = {
            'method': 'text_rules_v3', 'body_read': bool(text.strip()),
            'commercial_signals': commercial, 'image_dependent': image,
            'independence_group': group, 'duplicate_of': duplicate.id if duplicate else '',
            'campaign_duplicate_of': campaign.id if campaign else '', 'campaign_match_basis': match_basis,
            'independence': '同文关联' if duplicate else '同一活动线索' if campaign else '不同正文，作者/活动来源独立性未确认',
            'has_price_text': bool(re.search(r'[¥￥$]|\d+(?:\.\d+)?\s*(?:元|HKD|CNY|k)', text, re.I)),
            'has_date_text': bool(re.search(r'\d+[月/-]\d+|\d+月', text)),
            'sales_end': str(sales_end) if sales_end else '未确认',
            'flags': flags,
        }
        groups.append((item, normalized))


def deal_strength(opportunity):
    fares = opportunity.fares
    eligible = [f for f in fares if f.price_insights.get('comparable') and f.price_insights.get('typical_price_range')]
    if not fares:
        return {'level':'unverified', 'label':'当前未验证', 'reason':'只有社区线索，不能判断当前Deal。'}
    if not eligible:
        return {'level':'unknown', 'label':'已验价，廉价程度未知', 'reason':'未取得与本轮条件一致的可靠典型区间；不估算折扣。'}
    fare = min(eligible, key=lambda f:f.amount)
    low, high = fare.price_insights['typical_price_range']
    level = 'below_typical' if fare.amount < low else 'above_typical' if fare.amount > high else 'typical'
    label = {'below_typical':'低于 Google 典型区间', 'above_typical':'高于 Google 典型区间', 'typical':'处于 Google 典型区间'}[level]
    return {'level':level, 'label':label, 'fare_id':fare.id, 'source':fare.source,
            'current_price':fare.amount, 'typical_price_range':[low,high],
            'observed_at':fare.observed_at.isoformat(), 'request':fare.request.model_dump(mode='json'),
            'reason':'同一搜索条件的 Google 价格洞察；不是 FareScout 自建历史库或可售承诺。'}
