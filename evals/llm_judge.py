import os
from langchain_google_genai import ChatGoogleGenerativeAI


def _judge_prompt(sku_id: str, m: dict, narrative: str) -> str:
    flags = "; ".join(m["flag_reasons"]) or "None"
    promo = ", ".join(m["promo_weeks"]) or "None"
    weekly_rows = "\n".join(
        f"  {w['week']}: GSV Plan={w['gsv_plan']:.1f}  Actual={w['gsv_actual']:.1f}  "
        f"LE={w['gsv_le']:.1f}  Trade Plan={w['trade_plan']:.1f}  Trade Actual={w['trade_actual']:.1f}"
        for w in m["weekly_series"]
    )
    return f"""You are an impartial evaluator checking whether an AI-generated RGM briefing narrative is factually consistent with the computed ground-truth data. You must not be lenient — flag any hallucinated numbers or directional errors.

SKU: {sku_id} | {m['brand']} | {m['segment']} | {m['channel']}

GROUND TRUTH METRICS ($K unless noted):
  GSV Plan 13W:        {m['gsv_plan_13w']:.1f}
  GSV Actual 13W:      {m['gsv_actual_13w']:.1f}
  GSV Variance:        {m['gsv_var_pct']:+.1%} ({m['gsv_var_dollar']:+.1f})
  Trade Plan 13W:      {m['trade_plan_13w']:.1f}
  Trade Actual 13W:    {m['trade_actual_13w']:.1f}
  Trade Variance:      {m['trade_var_pct']:+.1%} ({m['trade_var_dollar']:+.1f})
  NSV Plan 13W:        {m['nsv_plan_13w']:.1f}
  NSV Actual 13W:      {m['nsv_actual_13w']:.1f}
  NSV Variance:        {m['nsv_var_dollar']:+.1f}
  Trade Eff. Gap:      {m['trade_efficiency_gap']:+.1%}
  Promo Weeks:         {promo}
  Flags Triggered:     {flags}

WEEKLY SERIES ($K):
{weekly_rows}

NARRATIVE TO EVALUATE:
{narrative}

Evaluate the narrative against the ground truth on these four criteria:
1. GSV direction — does it correctly state whether GSV is above or below plan?
2. Trade direction — does it correctly state whether trade spend is over or under plan?
3. No hallucination — does it avoid citing specific numbers that are inconsistent with the data above?
4. Action relevance — are the recommended actions appropriate given the flags triggered?

Respond in this exact format (nothing else):
VERDICT: PASS
REASONING: <2-3 sentences>

or

VERDICT: FAIL
REASONING: <2-3 sentences explaining specifically what is factually wrong>"""


def _revision_prompt(sku_id: str, m: dict, original_narrative: str, judge_feedback: str) -> str:
    flags_text = "\n".join(f"  - {r}" for r in m["flag_reasons"])
    promo_text = ", ".join(m["promo_weeks"]) if m["promo_weeks"] else "None"
    weekly_rows = "\n".join(
        f"  {w['week']}: GSV Plan={w['gsv_plan']:.1f}  Actual={w['gsv_actual']:.1f}  "
        f"LE={w['gsv_le']:.1f}  Trade Plan={w['trade_plan']:.1f}  Trade Actual={w['trade_actual']:.1f}"
        for w in m["weekly_series"]
    )
    return f"""You are an RGM analyst preparing a weekly briefing. A reviewer has identified factual errors in your draft narrative. Rewrite the narrative correcting those errors.

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

ORIGINAL NARRATIVE (contains errors):
{original_narrative}

REVIEWER FEEDBACK — errors to fix:
{judge_feedback}

Rewrite the narrative fixing only the identified errors. Keep the same structure: business interpretation, which weeks drove variance, and recommended actions. Be concise. Write as a professional speaking to a colleague."""


def revise_narratives(metrics: dict, narratives: dict, judge_results: list[dict]) -> dict:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )
    revised = {}
    for r in judge_results:
        if r["verdict"] != "FAIL":
            continue
        sku_id = r["sku_id"]
        prompt = _revision_prompt(sku_id, metrics[sku_id], narratives[sku_id], r["reasoning"])
        response = llm.invoke(prompt)
        revised[sku_id] = response.content
    return revised


def run_llm_judge(metrics: dict, narratives: dict) -> list[dict]:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )

    results = []
    for sku_id, narrative in narratives.items():
        m = metrics[sku_id]
        prompt = _judge_prompt(sku_id, m, narrative)
        try:
            response = llm.invoke(prompt)
            text = response.content.strip()

            verdict = "PASS" if "VERDICT: PASS" in text else "FAIL"
            reasoning_start = text.find("REASONING:")
            reasoning = text[reasoning_start + len("REASONING:"):].strip() if reasoning_start != -1 else text

            results.append({
                "sku_id": sku_id,
                "brand": m["brand"],
                "segment": m["segment"],
                "verdict": verdict,
                "reasoning": reasoning,
            })
        except Exception as e:
            results.append({
                "sku_id": sku_id,
                "brand": m["brand"],
                "segment": m["segment"],
                "verdict": "ERROR",
                "reasoning": str(e),
            })

    return results
