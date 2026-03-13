#!/usr/bin/env python3
"""
GoldFish-Stock — 个股舆情分析引擎
定位：不预测股价，只分析各类资金对个股事件的解读分歧
输出：定性判断（看多/看空/分歧/中性）+ 各方核心逻辑 + 潜在风险

设计原则：
- 不输出"涨多少点"，只输出"谁在买/谁在卖/为什么"
- 适合中小权重股（B站、TME、PDD等），恒指权重低但机构持仓有意义
- 5个有人格的分析师Agent，每个代表一类资金视角
"""
import os
import sys
import json
import yaml
from openai import OpenAI

api_key = os.environ.get("LLM_API_KEY") or "sk-bf316c318b77410a91dc8f4bceca6b93"
base_url = os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com"
client = OpenAI(api_key=api_key, base_url=base_url)

# ── 5个分析师Agent：各代表一类资金视角 ────────────────────

ANALYSTS = {
    "quant_hedge": {
        "name": "量化对冲",
        "persona": """你是量化对冲基金分析师（Two Sigma/Citadel风格）。
你用数据说话：营收增速、利润率变化、估值倍数、与预期的偏差（beat/miss幅度）。
你不信故事，只信可量化的指标。
你会主动识别"利好已price in"或"市场低估某个数字"。
发言简洁，2-3句，必须引用具体数字。"""
    },
    "long_only_growth": {
        "name": "成长型外资",
        "persona": """你是成长型长线外资基金经理（Baillie Gifford/Ark风格）。
你关注长期增长赛道：用户增长、变现效率、行业地位护城河。
你愿意接受短期亏损，只要长期逻辑没有被破坏。
你对中国互联网公司既有机会感也有监管顾虑。
发言简洁，2-3句，聚焦长期逻辑。"""
    },
    "value_hk_local": {
        "name": "港股本地价值派",
        "persona": """你是香港本地价值投资基金经理（惠理基金风格）。
你看估值：P/E、P/S、EV/EBITDA，与历史均值和同业比较。
你关注现金流和股东回报（回购/分红）。
你对"概念股"天生怀疑，只认实打实的盈利改善。
发言简洁，2-3句，必须提到估值或回购。"""
    },
    "southbound_retail": {
        "name": "南向散户",
        "persona": """你是内地南下散户（情绪化，有政策信仰）。
你关注：政策风向、热点板块、技术面（涨停/突破）。
你容易被大涨吸引，也容易被大跌吓走。
你相信"国家队会撑"，对中国互联网公司天然亲近。
发言简洁，2-3句，带点散户情绪，可以不理性。"""
    },
    "risk_arb": {
        "name": "风险套利",
        "persona": """你是风险套利/事件驱动型基金经理。
你专注：财报后的价格效应（gap up/gap down后的动量），期权定价，
短期催化剂（下一季度guidance、回购节奏、分析师评级变化）。
你不做长线，只做财报后3-10个交易日的走势判断。
发言简洁，2-3句，聚焦短期价格动能。"""
    }
}


def _llm(system: str, user: str, json_mode: bool = False) -> str:
    kwargs = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.7,
        "max_tokens": 250
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
        kwargs["max_tokens"] = 200
    return client.chat.completions.create(**kwargs).choices[0].message.content


def analyze_event(stock_event: dict) -> dict:
    """
    对单个股票事件进行多Agent分析
    返回：各Agent观点 + 综合分歧度
    """
    stock = stock_event.get("stock", "未知个股")
    event_type = stock_event.get("event_type", "财报")
    description = stock_event.get("description", "")
    key_metrics = stock_event.get("key_metrics", {})
    context = stock_event.get("context", "")

    # 格式化关键指标
    metrics_str = "\n".join([f"  - {k}: {v}" for k, v in key_metrics.items()])

    event_brief = f"""
个股：{stock}
事件类型：{event_type}
事件描述：{description}
关键指标：
{metrics_str}
背景：{context}
"""

    print(f"\n{'='*64}")
    print(f"📊 个股舆情分析：{stock} — {event_type}")
    print(f"{'='*64}")
    print(f"  {description[:80]}")

    # 第1轮：量化对冲先发言（最理性，定锚）
    quant_view = _llm(
        system=ANALYSTS["quant_hedge"]["persona"],
        user=f"{event_brief}\n请给出你对这个事件的核心判断（2-3句，必须引用数字）。"
    )
    print(f"\n  📐 {ANALYSTS['quant_hedge']['name']}: {quant_view}")

    # 第2轮：南向散户回应（情绪对立面）
    retail_view = _llm(
        system=ANALYSTS["southbound_retail"]["persona"],
        user=f"{event_brief}\n量化对冲说：{quant_view[:100]}\n请用2-3句表达你的看法。"
    )
    print(f"\n  📱 {ANALYSTS['southbound_retail']['name']}: {retail_view}")

    # 其余3个Agent独立发言
    other_views = {}
    for ak in ["long_only_growth", "value_hk_local", "risk_arb"]:
        view = _llm(
            system=ANALYSTS[ak]["persona"],
            user=f"{event_brief}\n目前市场讨论：量化对冲认为「{quant_view[:80]}」，散户认为「{retail_view[:80]}」\n请给出你独立的判断（2-3句）。"
        )
        print(f"\n  {'🌱' if ak=='long_only_growth' else '💎' if ak=='value_hk_local' else '⚡'} {ANALYSTS[ak]['name']}: {view}")
        other_views[ak] = view

    # 综合判断：分歧度 + 主流方向
    all_views = {
        "quant_hedge": quant_view,
        "southbound_retail": retail_view,
        **other_views
    }

    synthesis_prompt = f"""
个股：{stock}，事件：{event_type}

五方观点摘要：
- 量化对冲：{quant_view[:100]}
- 成长外资：{other_views['long_only_growth'][:100]}
- 价值本地：{other_views['value_hk_local'][:100]}
- 南向散户：{retail_view[:100]}
- 风险套利：{other_views['risk_arb'][:100]}

请综合分析，输出JSON：
{{
  "consensus": "看多/看空/分歧/中性",
  "bull_camp": ["看多的阵营，逗号分隔"],
  "bear_camp": ["看空的阵营"],
  "key_debate": "核心争议点（一句话）",
  "short_term_catalyst": "未来1-2周最重要的催化剂",
  "risk": "最大下行风险"
}}"""

    synthesis_raw = _llm(
        system="你是资深港股研究员，负责综合多方观点给出客观判断。",
        user=synthesis_prompt,
        json_mode=True
    )

    try:
        synthesis = json.loads(synthesis_raw)
    except Exception:
        synthesis = {"consensus": "分歧", "key_debate": "解析失败"}

    print(f"\n{'─'*64}")
    print(f"  🔍 综合判断：{synthesis.get('consensus', '?')}")
    print(f"  📈 看多阵营：{', '.join(synthesis.get('bull_camp', []))}")
    print(f"  📉 看空阵营：{', '.join(synthesis.get('bear_camp', []))}")
    print(f"  ⚖️  核心争议：{synthesis.get('key_debate', '')}")
    print(f"  🎯 近期催化剂：{synthesis.get('short_term_catalyst', '')}")
    print(f"  ⚠️  最大风险：{synthesis.get('risk', '')}")

    return {"views": all_views, "synthesis": synthesis}


def run_stock_analysis(event_file: str):
    with open(event_file) as f:
        data = yaml.safe_load(f)

    events = data.get("events", [data])  # 支持单事件或多事件
    results = []
    for event in events:
        result = analyze_event(event)
        results.append(result)

    print(f"\n{'='*64}")
    print(f"分析完成，共{len(results)}个事件。")
    return results


if __name__ == "__main__":
    event_file = sys.argv[1] if len(sys.argv) > 1 else "events/bilibili_q4.yaml"
    run_stock_analysis(event_file)
