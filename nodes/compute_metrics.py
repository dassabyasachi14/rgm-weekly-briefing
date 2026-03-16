import pandas as pd


META_COLS = ["SKU ID", "Brand", "Segment", "Pack Size", "Channel"]


def _week_label(col_name: str) -> str:
    return col_name.split("\n")[1] if "\n" in col_name else col_name


def compute_metrics(state: dict) -> dict:
    df = state["raw_df"]

    gsv_plan_cols = [c for c in df.columns if c.startswith("GSV Plan ($K)")]
    gsv_actual_cols = [c for c in df.columns if c.startswith("GSV Actual ($K)")]
    gsv_le_cols = [c for c in df.columns if c.startswith("GSV LE ($K)")]
    trade_plan_cols = [c for c in df.columns if c.startswith("Trade Plan ($K)")]
    trade_actual_cols = [c for c in df.columns if c.startswith("Trade Actual ($K)")]
    trade_le_cols = [c for c in df.columns if c.startswith("Trade LE ($K)")]

    for label, cols in [
        ("GSV Plan", gsv_plan_cols),
        ("GSV Actual", gsv_actual_cols),
        ("GSV LE", gsv_le_cols),
        ("Trade Plan", trade_plan_cols),
        ("Trade Actual", trade_actual_cols),
        ("Trade LE", trade_le_cols),
    ]:
        assert len(cols) == 13, f"Expected 13 {label} columns, found {len(cols)}"

    week_labels = [_week_label(c) for c in gsv_plan_cols]

    metrics = {}
    for _, row in df.iterrows():
        sku_id = row["SKU ID"]

        gsv_plan_13w = sum(row[c] for c in gsv_plan_cols)
        gsv_actual_13w = sum(row[c] for c in gsv_actual_cols)
        gsv_le_13w = sum(row[c] for c in gsv_le_cols)
        trade_plan_13w = sum(row[c] for c in trade_plan_cols)
        trade_actual_13w = sum(row[c] for c in trade_actual_cols)
        trade_le_13w = sum(row[c] for c in trade_le_cols)

        gsv_var_dollar = gsv_actual_13w - gsv_plan_13w
        gsv_var_pct = gsv_var_dollar / gsv_plan_13w if gsv_plan_13w else 0

        trade_var_dollar = trade_actual_13w - trade_plan_13w
        trade_var_pct = trade_var_dollar / trade_plan_13w if trade_plan_13w else 0

        nsv_actual_13w = gsv_actual_13w - trade_actual_13w
        nsv_plan_13w = gsv_plan_13w - trade_plan_13w
        nsv_var_dollar = nsv_actual_13w - nsv_plan_13w

        trade_efficiency_gap = trade_var_pct - gsv_var_pct

        promo_weeks = [
            week_labels[i]
            for i, (ap, pp) in enumerate(zip(gsv_actual_cols, gsv_plan_cols))
            if pp and row[pp] and row[ap] > 1.25 * row[pp]
        ]

        flagged = (
            abs(gsv_var_pct) > 0.08
            or trade_var_pct > 0.08
            or trade_efficiency_gap > 0.03
        )

        weekly_series = [
            {
                "week": week_labels[i],
                "gsv_plan": row[gsv_plan_cols[i]],
                "gsv_actual": row[gsv_actual_cols[i]],
                "gsv_le": row[gsv_le_cols[i]],
                "trade_plan": row[trade_plan_cols[i]],
                "trade_actual": row[trade_actual_cols[i]],
            }
            for i in range(13)
        ]

        flag_reasons = []
        if abs(gsv_var_pct) > 0.08:
            flag_reasons.append(f"GSV variance {gsv_var_pct:+.1%} (threshold ±8%)")
        if trade_var_pct > 0.08:
            flag_reasons.append(f"Trade overspend {trade_var_pct:+.1%} (threshold 8%)")
        if trade_efficiency_gap > 0.03:
            flag_reasons.append(
                f"Trade efficiency gap {trade_efficiency_gap:+.1%} (threshold 3pp)"
            )

        metrics[sku_id] = {
            "brand": row["Brand"],
            "segment": row["Segment"],
            "pack_size": row["Pack Size"],
            "channel": row["Channel"],
            "gsv_plan_13w": gsv_plan_13w,
            "gsv_actual_13w": gsv_actual_13w,
            "gsv_le_13w": gsv_le_13w,
            "gsv_var_dollar": gsv_var_dollar,
            "gsv_var_pct": gsv_var_pct,
            "trade_plan_13w": trade_plan_13w,
            "trade_actual_13w": trade_actual_13w,
            "trade_le_13w": trade_le_13w,
            "trade_var_dollar": trade_var_dollar,
            "trade_var_pct": trade_var_pct,
            "nsv_actual_13w": nsv_actual_13w,
            "nsv_plan_13w": nsv_plan_13w,
            "nsv_var_dollar": nsv_var_dollar,
            "trade_efficiency_gap": trade_efficiency_gap,
            "promo_weeks": promo_weeks,
            "flagged": flagged,
            "flag_reasons": flag_reasons,
            "weekly_series": weekly_series,
        }

    flagged_count = sum(1 for v in metrics.values() if v["flagged"])
    print(f"compute_metrics: {len(metrics)} SKUs processed, {flagged_count} flagged")

    return {"metrics": metrics}
