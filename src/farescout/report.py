from __future__ import annotations

import html
from collections import defaultdict
from datetime import timedelta

from .models import Evidence, Opportunity, Session, Turn, now
from .research import AIRPORTS


def plain(value: str) -> str:
    value = html.escape(value).replace("\n", " ")
    for char in "\\`*_[]|":
        value = value.replace(char, "\\" + char)
    return value


def synthesize(opportunity: Opportunity, evidence: dict[str, Evidence]) -> None:
    fares = opportunity.fares
    notes = []
    if not fares:
        notes.append("当前价格尚未验证；这只是社区线索，不能据此判断现在仍便宜。")
    else:
        groups = defaultdict(list)
        for fare in fares:
            key = (fare.request.model_dump_json(), fare.currency, fare.price_basis)
            groups[key].append(fare)
        for (_, currency, basis), group in groups.items():
            sources = {f.source for f in group}
            if len(sources) > 1:
                minima = [min(f.amount for f in group if f.source == source) for source in sources]
                low, high = min(minima), max(minima)
                if low != high:
                    notes.append(f"相同搜索条件/币种/税费口径的不同渠道最低报价为 {currency} {low:g}～{high:g}；存在价差，不压成一个确定价格。")
                else:
                    notes.append(f"相同条件的不同实时渠道最低报价一致：{currency} {low:g}，不代表同一航班或可售承诺。")
        if len({f.source for f in fares}) == 1:
            notes.append("社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。")
        elif len({f.price_basis for f in fares}) > 1:
            notes.append("实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。")
        if any(s.seen_price_text for s in opportunity.candidate.signals):
            notes.append("社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。")
    opportunity.comparison = notes
    limitations = ["仅核查列出的具体日期；不是整个日期窗口的最低价保证。",
                   "帖文、作者或活动来源的独立性未确认；不同正文不自动等于独立佐证。",
                   "社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。"]
    limitations.append("典型价格仅来自Google本次同条件洞察；不代表自建历史库、历史最低或库存保证。" if
                       opportunity.deal.get("typical_price_range") else "没有本轮可比的可靠典型价格，不声称历史低点或折扣幅度。")
    if opportunity.candidate.origin in {"HKG", "MFM"}:
        limitations.append("从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。")
    if any((now() - evidence[s.evidence_id].observed_at) > timedelta(days=1) for s in opportunity.candidate.signals):
        limitations.append("本轮复用了此前采集的社区内容，抓取时间见引用；不能据此声称今天仍有效。")
    limitations.extend(sorted({w for s in opportunity.candidate.signals for w in evidence[s.evidence_id].warnings}))
    opportunity.limitations = limitations


def render_report(session: Session, turn: Turn) -> str:
    goal = turn.goal
    lines = ["# 飞探 FareScout 研究报告", "", f"**状态：{turn.status}** · 会话 `{session.id}` · 轮次 `{turn.id}`", "",
             f"需求：{plain(turn.user_input)}", "",
             f"出发：{' / '.join(goal.origins)}；地区：{goal.region or '国际探索'}；日期：{goal.date_from}～{goal.date_to}；"
             f"{'往返' if goal.trip_type == 'round_trip' else '单程'}，1 成人，经济舱。", "",
             f"排除红眼：{'是（任一段当地 22:00～06:00 或跨夜保守排除）' if goal.no_red_eye else '未要求'}。", "",
             f"研究开始：{turn.started_at.isoformat()}；结束：{turn.finished_at.isoformat() if turn.finished_at else '进行中'}。", ""]
    if goal.assumptions:
        lines += ["研究假设：", "", *[f"- {plain(s)}" for s in dict.fromkeys(goal.assumptions)], ""]
    if turn.metrics:
        lines += ["调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：", "",
                  f"- 社区 {turn.metrics.get('community_calls', 0)} 次；日期探索 {turn.metrics.get('date_calls', 0)} 次；最终精确验价 {turn.metrics.get('verification_calls', 0)} 次；模型操作 {turn.metrics.get('model_operations', 0)} 次。",
                  f"- 本轮耗时 {turn.metrics.get('elapsed_seconds', '进行中')} 秒。", ""]
        lines += [f"- socai实际搜索命令 {turn.metrics.get('socai_commands', '未记录')} 次（含重试）；模型实际请求 {turn.metrics.get('model_requests', '未记录')} 次（含Pydantic AI重试）。", ""]
    if goal.constraints:
        labels = {"explicit":"用户明确", "inferred":"语义解释", "default":"系统默认", "context":"沿用上下文"}
        lines += ["约束解释：", "", "| 字段 | 生效值 | 来源 | 规则 |", "|---|---|---|---|"]
        lines += [f"| {c.field} | {plain(str(c.value))} | {labels[c.provenance]} | {plain(c.rule)} |" for c in goal.constraints]
        lines.append("")
    verified = sum(bool(o.fares) for o in turn.opportunities)
    lines += [f"本轮整理 {len(turn.opportunities)} 个调查方向，其中 {verified} 个取得可核对的当前报价。", ""]
    if turn.opportunities:
        lines += ["| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |", "|---|---|"]
        for opportunity in turn.opportunities:
            lowest = {}
            for fare in opportunity.fares:
                key = (fare.source, fare.price_basis)
                if key not in lowest or fare.amount < lowest[key].amount:
                    lowest[key] = fare
            summary = "；".join(
                f"{plain(f.source)} CNY {f.amount:g}（{'含税' if f.price_basis == 'total_including_taxes' else '税费未确认'}）"
                for f in lowest.values()
            ) or "当前未验证"
            lines.append(f"| {opportunity.candidate.origin} → {opportunity.candidate.destination} | {summary} |")
        lines.append("")
    if len(turn.opportunities) < 3 or verified < 3:
        lines += ["**尚未满足 3～5 个有价格证据的机会要求。不会用社区晒价补齐当前价格。**", ""]
    for index, opportunity in enumerate(turn.opportunities, 1):
        candidate = opportunity.candidate
        synthesize(opportunity, session.evidence)
        origin_name = AIRPORTS[candidate.origin][0]
        lines += [f"## {index}. {origin_name} {candidate.origin} → {candidate.destination_name} {candidate.destination}", "",
                  "**发现依据 / 社区出现价格（不是当前票价）**", ""]
        sources = {s.evidence_id for s in candidate.signals}
        lines += [f"从 {len(sources)} 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。", ""]
        for signal in candidate.signals[:3]:
            source = session.evidence[signal.evidence_id]
            lines += [f"- [{plain(source.title or source.source)}]({source.url}) · {plain(source.source)} · "
                      f"发布/更新：{plain(source.published_at or '未知')} · 读取：{source.observed_at.isoformat()}",
                      f"  - 原文：{plain(signal.excerpt)}",
                      f"  - 社区晒价：{plain(signal.seen_price_text or '未取得可引用价格')}；航司：{plain(signal.airline or '未确认')}。"]
            if source.quality:
                lines += [f"  - 证据质量：{plain('；'.join(source.quality.get('flags', [])) or '有正文，未命中风险词；不等于已证实')}。{plain(str(source.quality.get('independence', '独立性未知')))}。"]
        conflict_comments = list(dict.fromkeys(
            comment.text for source_id in sources for comment in session.evidence[source_id].comments
            if any(word in comment.text for word in ["不可用", "不匹配", "没有便宜", "搜不出", "没那么便宜", "没行李"])
        ))
        if conflict_comments:
            lines += ["", "社区内的不同反馈（用户评论，未独立证实）：", "", *[f"- {plain(c)}" for c in conflict_comments[:4]]]
        lines += ["", "**当前验证价格**", ""]
        if opportunity.date_coverage:
            c = opportunity.date_coverage
            attempted = sorted({str(s.date) for s in c.samples if s.stage != "range"})
            failed = sorted({str(s.date) for s in c.samples if s.status == "failed"})
            lines += [f"日期窗：{c.date_from}～{c.date_to}；最终选定：{c.selected_date or '未选定'}。", "",
                      f"实际精确请求日期（含失败）：{', '.join(attempted) or '无'}；范围响应返回日期：{', '.join(map(str, c.returned_dates)) or '无'}。", "",
                      f"失败日期：{', '.join(failed) or '无'}。未覆盖日期保持未知，不声称全月最低。", "",
                      "| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |", "|---|---|---|---|---|"]
            lines += [f"| {s.date} | {plain(s.source)} | {s.stage} | {s.status} | {str(s.amount) if s.amount is not None else '未取得'} / {s.price_basis or '未知'} |" for s in c.samples]
            lines.append("")
        if not opportunity.fares:
            lines += ["未验证，不能作为当前低价推荐。", ""]
        else:
            # The full matching quote set remains in session JSON. The user
            # report shows one cheapest itinerary per source/tax basis.
            selected = {}
            for fare in opportunity.fares:
                key = (fare.source, fare.price_basis)
                if key not in selected or fare.amount < selected[key].amount:
                    selected[key] = fare
            for fare in selected.values():
                req = fare.request
                label = "含税总价" if fare.price_basis == "total_including_taxes" else "票价，税费口径未确认"
                lines += [f"- **{fare.currency} {fare.amount:g}**（{label}）· [{fare.source}]({fare.source_url}) · "
                          f"出发 {req.outbound_date}" + (f" / 返回 {req.return_date}" if req.return_date else " / 单程") +
                          f" · 查询 {fare.observed_at.isoformat()}"]
                for segment in fare.segments:
                    lines += [f"  - {plain(segment.airline)} {plain(segment.flight_number)}：{segment.origin} {segment.departure} → {segment.destination} {segment.arrival}"]
                lines += [f"  - 行李：{plain(fare.baggage)}。", *[f"  - {plain(x)}" for x in fare.restrictions]]
                if fare.price_insights.get("typical_price_range"):
                    bounds = fare.price_insights['typical_price_range']
                    lines += [f"  - Google典型区间：CNY {bounds[0]:g}～{bounds[1]:g}；{'本轮同条件可比' if fare.price_insights.get('comparable') else '条件不齐，仅作为来源参考，不算折扣'}。"]
            lines.append("")
        lines += ["**交叉验证与结论**", "", *[f"- {plain(x)}" for x in opportunity.comparison], "",
                  ("值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。" if opportunity.fares
                   else "目前只值得保留为待查线索；缺少当前价格证据，暂不推荐。"), "",
                  "**主要限制**", "", *[f"- {plain(x)}" for x in opportunity.limitations], ""]
        if opportunity.deal:
            lines += [f"Deal基础判断：**{plain(opportunity.deal['label'])}**。{plain(opportunity.deal['reason'])}", ""]
    lines += ["## 研究循环与来源状态", ""]
    for expansion in turn.expansions:
        lines += [f"- 根据证据 `{expansion.evidence_id}` 中的“{plain(expansion.discovered_term)}”扩展搜索："
                  f"**{plain(expansion.query)}**。理由：{plain(expansion.reason)}"]
    lines += ["", "| 阶段 | 来源 | 状态 | 说明 |", "|---|---|---|---|"]
    lines += [f"| {e.stage} | {plain(e.source or 'FareScout')} | {e.status} | {plain(e.detail)} |" for e in turn.events]
    lines += ["", f"停止原因：{plain(turn.stop_reason)}", "", "研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。", ""]
    return "\n".join(lines)
