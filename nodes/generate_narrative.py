import os
from langchain_google_genai import ChatGoogleGenerativeAI


def _build_prompt(sku_id: str, m: dict) -> str:
    weekly_rows = "\n".join(
        f"  {w['week']}: GSV Plan={w['gsv_plan']:.1f}  Actual={w['gsv_actual']:.1f}  "
        f"LE={w['gsv_le']:.1f}  Trade Plan={w['trade_plan']:.1f}  Trade Actual={w['trade_actual']:.1f}"
        for w in m["weekly_series"]
    )

    flags_text = "\n".join(f"  - {r}" for r in m["flag_reasons"])
    promo_text = ", ".join(m["promo_weeks"]) if m["promo_weeks"] else "None"

    return f"""You are an RGM analyst preparing a weekly briefing. Analyse the following SKU data and write a concise, professional commentary.

SKU: {sku_id} | Brand: {m['brand']} | Segment: {m['segment']} | Pack Size: {m['pack_size']} | Channel: {m['channel']}

13-WEEK SUMMARY ($K unless noted):
  GSV Plan:         {m['gsv_plan_13w']:.1f}
  GSV Actual:       {m['gsv_actual_13w']:.1f}
  GSV LE:           {m['gsv_le_13w']:.1f}
  GSV Var $:        {m['gsv_var_dollar']:+.1f}
  GSV Var %:        {m['gsv_var_pct']:+.1%}
  Trade Plan:       {m['trade_plan_13w']:.1f}
  Trade Actual:     {m['trade_actual_13w']:.1f}
  Trade Var $:      {m['trade_var_dollar']:+.1f}
  Trade Var %:      {m['trade_var_pct']:+.1%}
  NSV Plan:         {m['nsv_plan_13w']:.1f}
  NSV Actual:       {m['nsv_actual_13w']:.1f}
  NSV Var $:        {m['nsv_var_dollar']:+.1f}
  Trade Efficiency Gap: {m['trade_efficiency_gap']:+.1%}
  Promo Weeks (GSV Actual >125% of Plan): {promo_text}

FLAGS TRIGGERED:
{flags_text}

WEEKLY SERIES ($K):
{weekly_rows}

Write exactly three things:
1. A 2-3 sentence business interpretation of what these numbers mean (plain language, no jargon overload).
2. Which specific weeks drove the variance and why.
3. 1-2 concrete recommended actions for the RGM Associate.

Be concise. Write as a professional speaking to a colleague, not as a report template."""


def generate_narrative(state: dict) -> dict:
    metrics = state["metrics"]
    flagged_skus = {sku: m for sku, m in metrics.items() if m["flagged"]}

    if not flagged_skus:
        print("generate_narrative: No flagged SKUs — skipping LLM call")
        return {"narrative": ""}

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )

    narratives = {}
    for sku_id, m in flagged_skus.items():
        print(f"generate_narrative: calling LLM for {sku_id}...")
        prompt = _build_prompt(sku_id, m)
        response = llm.invoke(prompt)
        narratives[sku_id] = response.content
        print(f"generate_narrative: {sku_id} done")

    return {"narrative": narratives}
