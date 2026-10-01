from __future__ import annotations

import re
from difflib import SequenceMatcher
from datetime import date, datetime, timezone

from .models import identity
from .research import publication_time, today_local


def assess_evidence(evidence, today=None):
    """Explainable text heuristics, not account credibility or a truth score."""
    today = today or today_local()
    groups = []
    for item in evidence.values():
        text = item.body
        normalized = re.sub(r"\s+|#[^\s#]+", "", text).lower()
        duplicate = next((other for other, body in groups if len(normalized) >= 50 and
                          (normalized == body or SequenceMatcher(None, normalized, body).ratio() >= .9)), None)
        group = duplicate.quality['independence_group'] if duplicate else identity(normalized)
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
            'method': 'text_rules_v1', 'body_read': bool(text.strip()),
            'commercial_signals': commercial, 'image_dependent': image,
            'independence_group': group, 'duplicate_of': duplicate.id if duplicate else '',
            'independence': '同文关联' if duplicate else '不同正文，作者/活动来源独立性未确认',
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
