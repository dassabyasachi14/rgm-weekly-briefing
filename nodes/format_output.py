import os


def format_output(state: dict) -> dict:
    metrics = state["metrics"]
    narratives = state.get("narrative") or {}
    revised_narratives = state.get("revised_narrative") or {}

    green_skus = {sku: m for sku, m in metrics.items() if not m["flagged"]}
    flagged_skus = {sku: m for sku, m in metrics.items() if m["flagged"]}

    lines = []

    lines.append("# RGM Weekly Briefing\n")

    # ── Section 1: Green SKUs ──────────────────────────────────────────────────
    lines.append("## ✅ Healthy SKUs — 13W Performance\n")
    lines.append(
        "| SKU ID | Brand | Segment | Channel | GSV Actual ($K) | GSV Var% | Trade Var% | NSV Actual ($K) |"
    )
    lines.append("|--------|-------|---------|---------|-----------------|----------|------------|-----------------|")
    for sku_id, m in green_skus.items():
        lines.append(
            f"| {sku_id} | {m['brand']} | {m['segment']} | {m['channel']} "
            f"| {m['gsv_actual_13w']:.1f} | {m['gsv_var_pct']:+.1%} "
            f"| {m['trade_var_pct']:+.1%} | {m['nsv_actual_13w']:.1f} |"
        )

    lines.append("")

    # ── Section 2: Flagged SKUs ────────────────────────────────────────────────
    if flagged_skus:
        lines.append("## ⚠️ Flagged SKUs — Action Required\n")
        for sku_id, m in flagged_skus.items():
            lines.append(
                f"### {sku_id} | {m['brand']} | {m['segment']} | {m['channel']}\n"
            )

            lines.append("**13W Summary ($K)**\n")
            lines.append("| Metric | Plan | Actual | LE | Var $ | Var % |")
            lines.append("|--------|------|--------|----|-------|-------|")
            lines.append(
                f"| GSV | {m['gsv_plan_13w']:.1f} | {m['gsv_actual_13w']:.1f} "
                f"| {m['gsv_le_13w']:.1f} | {m['gsv_var_dollar']:+.1f} | {m['gsv_var_pct']:+.1%} |"
            )
            lines.append(
                f"| Trade | {m['trade_plan_13w']:.1f} | {m['trade_actual_13w']:.1f} "
                f"| {m['trade_le_13w']:.1f} | {m['trade_var_dollar']:+.1f} | {m['trade_var_pct']:+.1%} |"
            )
            lines.append(
                f"| NSV | {m['nsv_plan_13w']:.1f} | {m['nsv_actual_13w']:.1f} "
                f"| — | {m['nsv_var_dollar']:+.1f} | — |"
            )
            lines.append("")

            lines.append(
                f"**Trade Efficiency Gap:** {m['trade_efficiency_gap']:+.1%}  "
            )
            if m["promo_weeks"]:
                lines.append(
                    f"**Promo Weeks (GSV Actual >125% Plan):** {', '.join(m['promo_weeks'])}"
                )
            lines.append("")

            flags_text = "  \n".join(f"- {r}" for r in m["flag_reasons"])
            lines.append(f"**Flags Triggered:**  \n{flags_text}\n")

            narrative_text = revised_narratives.get(sku_id) or narratives.get(sku_id, "_No narrative generated._")
            lines.append(f"**Analysis:**\n\n{narrative_text}\n")
            lines.append("---\n")

    report = "\n".join(lines)

    os.makedirs("output", exist_ok=True)
    with open("output/report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print("\nReport saved to output/report.md")

    return {"report": report}
