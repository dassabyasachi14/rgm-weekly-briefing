import pandas as pd
from nodes.compute_metrics import compute_metrics


def _flat(val, n=13):
    return [val] * n


def _build_state(sku_id, gsv_plan, gsv_actual, gsv_le, trade_plan, trade_actual, trade_le):
    data = {
        "SKU ID": [sku_id],
        "Brand": ["TestBrand"],
        "Segment": ["Dry Dog Food"],
        "Pack Size": ["5kg"],
        "Channel": ["Grocery"],
    }
    for i in range(13):
        w = f"W{i + 1}"
        data[f"GSV Plan ($K)\n{w}"] = [gsv_plan[i]]
        data[f"GSV Actual ($K)\n{w}"] = [gsv_actual[i]]
        data[f"GSV LE ($K)\n{w}"] = [gsv_le[i]]
        data[f"Trade Plan ($K)\n{w}"] = [trade_plan[i]]
        data[f"Trade Actual ($K)\n{w}"] = [trade_actual[i]]
        data[f"Trade LE ($K)\n{w}"] = [trade_le[i]]
    return {"raw_df": pd.DataFrame(data)}


def _run(test_fn):
    try:
        detail = test_fn()
        return {"name": test_fn.__name__, "passed": True, "detail": detail or "OK"}
    except AssertionError as e:
        return {"name": test_fn.__name__, "passed": False, "detail": str(e)}
    except Exception as e:
        return {"name": test_fn.__name__, "passed": False, "detail": f"Unexpected error: {e}"}


# ── Test cases ─────────────────────────────────────────────────────────────────

def test_13w_sums_correct():
    state = _build_state("T-001", _flat(10), _flat(11), _flat(9), _flat(2), _flat(3), _flat(2.5))
    m = compute_metrics(state)["metrics"]["T-001"]
    assert abs(m["gsv_plan_13w"] - 130.0) < 0.01, f"gsv_plan_13w={m['gsv_plan_13w']}, expected 130"
    assert abs(m["gsv_actual_13w"] - 143.0) < 0.01, f"gsv_actual_13w={m['gsv_actual_13w']}, expected 143"
    assert abs(m["trade_plan_13w"] - 26.0) < 0.01, f"trade_plan_13w={m['trade_plan_13w']}, expected 26"
    assert abs(m["trade_actual_13w"] - 39.0) < 0.01, f"trade_actual_13w={m['trade_actual_13w']}, expected 39"
    return "gsv_plan=130 ✓  gsv_actual=143 ✓  trade_plan=26 ✓  trade_actual=39 ✓"


def test_gsv_variance_calculation():
    # plan=100/wk, actual=110/wk → var_dollar=130, var_pct=+10%
    state = _build_state("T-002", _flat(100), _flat(110), _flat(110), _flat(20), _flat(20), _flat(20))
    m = compute_metrics(state)["metrics"]["T-002"]
    assert abs(m["gsv_var_dollar"] - 130.0) < 0.01, f"gsv_var_dollar={m['gsv_var_dollar']}, expected 130"
    assert abs(m["gsv_var_pct"] - 0.10) < 0.001, f"gsv_var_pct={m['gsv_var_pct']:.4f}, expected 0.10"
    return "gsv_var_dollar=+130 ✓  gsv_var_pct=+10.0% ✓"


def test_trade_variance_calculation():
    # trade_plan=20/wk, trade_actual=22/wk → var_dollar=26, var_pct=+10%
    state = _build_state("T-003", _flat(100), _flat(100), _flat(100), _flat(20), _flat(22), _flat(22))
    m = compute_metrics(state)["metrics"]["T-003"]
    assert abs(m["trade_var_dollar"] - 26.0) < 0.01, f"trade_var_dollar={m['trade_var_dollar']}, expected 26"
    assert abs(m["trade_var_pct"] - 0.10) < 0.001, f"trade_var_pct={m['trade_var_pct']:.4f}, expected 0.10"
    return "trade_var_dollar=+26 ✓  trade_var_pct=+10.0% ✓"


def test_nsv_calculation():
    # gsv_actual=110/wk, trade_actual=25/wk → nsv_actual=1105
    # gsv_plan=100/wk,   trade_plan=20/wk  → nsv_plan=1040
    state = _build_state("T-004", _flat(100), _flat(110), _flat(110), _flat(20), _flat(25), _flat(25))
    m = compute_metrics(state)["metrics"]["T-004"]
    assert abs(m["nsv_actual_13w"] - 1105.0) < 0.01, f"nsv_actual={m['nsv_actual_13w']}, expected 1105"
    assert abs(m["nsv_plan_13w"] - 1040.0) < 0.01, f"nsv_plan={m['nsv_plan_13w']}, expected 1040"
    assert abs(m["nsv_var_dollar"] - 65.0) < 0.01, f"nsv_var={m['nsv_var_dollar']}, expected 65"
    return "nsv_actual=1105 ✓  nsv_plan=1040 ✓  nsv_var=+65 ✓"


def test_trade_efficiency_gap():
    # gsv_var_pct=+2%, trade_var_pct=+6% → gap=+4%
    state = _build_state("T-005", _flat(100), _flat(102), _flat(102), _flat(20), _flat(21.2), _flat(21.2))
    m = compute_metrics(state)["metrics"]["T-005"]
    assert abs(m["trade_efficiency_gap"] - 0.04) < 0.001, f"gap={m['trade_efficiency_gap']:.4f}, expected 0.04"
    return "trade_efficiency_gap=+4.0% (trade +6% vs GSV +2%) ✓"


def test_promo_week_detection():
    gsv_plan = _flat(100)
    gsv_actual = _flat(100)
    gsv_actual[4] = 130   # W5: 130 > 125% of 100
    gsv_actual[9] = 128   # W10: 128 > 125% of 100
    gsv_actual[2] = 120   # W3: 120 = 120% of 100 — below threshold, should NOT flag
    state = _build_state("T-006", gsv_plan, gsv_actual, _flat(100), _flat(20), _flat(20), _flat(20))
    m = compute_metrics(state)["metrics"]["T-006"]
    assert len(m["promo_weeks"]) == 2, f"Expected 2 promo weeks, got {len(m['promo_weeks'])}: {m['promo_weeks']}"
    assert any("W5" in w for w in m["promo_weeks"]), f"W5 not in promo_weeks: {m['promo_weeks']}"
    assert any("W10" in w for w in m["promo_weeks"]), f"W10 not in promo_weeks: {m['promo_weeks']}"
    return f"Detected 2 promo weeks ✓  W3 correctly excluded ✓"


def test_flag_triggered_by_gsv_variance():
    # GSV var = -9% → above ±8% threshold
    state = _build_state("T-007", _flat(100), _flat(91), _flat(91), _flat(20), _flat(20), _flat(20))
    m = compute_metrics(state)["metrics"]["T-007"]
    assert m["flagged"], "Expected SKU flagged for GSV variance -9% but was not"
    assert any("GSV variance" in r for r in m["flag_reasons"]), f"GSV reason missing: {m['flag_reasons']}"
    return "Flagged for GSV variance -9% ✓"


def test_flag_triggered_by_trade_overspend():
    # Trade var = +9% → above 8% threshold
    state = _build_state("T-008", _flat(100), _flat(100), _flat(100), _flat(20), _flat(21.8), _flat(21.8))
    m = compute_metrics(state)["metrics"]["T-008"]
    assert m["flagged"], "Expected SKU flagged for trade overspend +9% but was not"
    assert any("Trade overspend" in r for r in m["flag_reasons"]), f"Trade reason missing: {m['flag_reasons']}"
    return "Flagged for trade overspend +9% ✓"


def test_flag_triggered_by_efficiency_gap():
    # gsv_var=+2%, trade_var=+6% → gap=+4% > 3pp threshold
    state = _build_state("T-009", _flat(100), _flat(102), _flat(102), _flat(20), _flat(21.2), _flat(21.2))
    m = compute_metrics(state)["metrics"]["T-009"]
    assert m["flagged"], "Expected SKU flagged for efficiency gap +4% but was not"
    assert any("efficiency gap" in r for r in m["flag_reasons"]), f"Gap reason missing: {m['flag_reasons']}"
    return "Flagged for trade efficiency gap +4% ✓"


def test_no_flag_within_thresholds():
    # gsv_var=+5%, trade_var=+5% → gap=0%, all within thresholds
    state = _build_state("T-010", _flat(100), _flat(105), _flat(105), _flat(20), _flat(21), _flat(21))
    m = compute_metrics(state)["metrics"]["T-010"]
    assert not m["flagged"], f"Expected no flag but got: {m['flag_reasons']}"
    assert m["flag_reasons"] == [], f"Expected empty flag_reasons, got: {m['flag_reasons']}"
    return "Correctly not flagged (GSV +5%, Trade +5%, Gap 0%) ✓"


def test_zero_plan_guard():
    # Zero plan values — must not raise ZeroDivisionError
    state = _build_state("T-011", _flat(0), _flat(10), _flat(10), _flat(0), _flat(5), _flat(5))
    m = compute_metrics(state)["metrics"]["T-011"]
    assert m["gsv_var_pct"] == 0, f"Expected gsv_var_pct=0 for zero plan, got {m['gsv_var_pct']}"
    assert m["trade_var_pct"] == 0, f"Expected trade_var_pct=0 for zero plan, got {m['trade_var_pct']}"
    return "Zero plan guard: no ZeroDivisionError, var_pct=0 ✓"


# ── Entry point ────────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_13w_sums_correct,
    test_gsv_variance_calculation,
    test_trade_variance_calculation,
    test_nsv_calculation,
    test_trade_efficiency_gap,
    test_promo_week_detection,
    test_flag_triggered_by_gsv_variance,
    test_flag_triggered_by_trade_overspend,
    test_flag_triggered_by_efficiency_gap,
    test_no_flag_within_thresholds,
    test_zero_plan_guard,
]


def run_unit_tests() -> list[dict]:
    return [_run(t) for t in ALL_TESTS]
