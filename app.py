import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from main import build_graph
from evals.unit_tests import run_unit_tests

st.set_page_config(page_title="RGM Weekly Briefing", layout="wide", page_icon="📊")


def run_workflow():
    app = build_graph()
    final_state = {}
    with st.status("Running workflow...", expanded=True) as status:
        for chunk in app.stream({}):
            node_name = next(iter(chunk))
            final_state.update(chunk[node_name])
            labels = {
                "load_data": "✅ Data loaded",
                "compute_metrics": "✅ Metrics computed",
                "generate_narrative": "✅ Narratives generated",
                "evaluate_narratives": "✅ Narratives evaluated",
                "revise_narratives": "✅ Narratives revised",
                "format_output": "✅ Report formatted",
            }
            st.write(labels.get(node_name, node_name))
        status.update(label="Analysis complete!", state="complete")
    return final_state


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 RGM Briefing")
    st.caption("Pet Food — 13-Week Rolling Analysis")
    st.divider()

    run_btn = st.button("▶ Run Analysis", type="primary", use_container_width=True)

    if run_btn:
        st.session_state.pop("results", None)

    if "results" in st.session_state:
        metrics = st.session_state.results["metrics"]
        green = sum(1 for m in metrics.values() if not m["flagged"])
        flagged = sum(1 for m in metrics.values() if m["flagged"])
        st.divider()
        st.metric("Total SKUs", len(metrics))
        col1, col2 = st.columns(2)
        col1.metric("✅ Healthy", green)
        col2.metric("⚠️ Flagged", flagged)

    st.divider()
    st.caption("**Flagging thresholds**")
    st.caption("• GSV Var% > ±8%")
    st.caption("• Trade Var% > 8%")
    st.caption("• Trade Efficiency Gap > 3pp")


# ── Run workflow ───────────────────────────────────────────────────────────────
if run_btn:
    st.session_state.results = run_workflow()

if "results" not in st.session_state:
    st.markdown("## Welcome to the RGM Weekly Briefing")
    st.info("Click **▶ Run Analysis** in the sidebar to load and analyse this week's data.")
    st.stop()

metrics = st.session_state.results["metrics"]
narratives = st.session_state.results.get("narrative") or {}
revised_narratives = st.session_state.results.get("revised_narrative") or {}
judge_results = st.session_state.results.get("judge_results") or []
green_skus = {sku: m for sku, m in metrics.items() if not m["flagged"]}
flagged_skus = {sku: m for sku, m in metrics.items() if m["flagged"]}


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_analysis, tab_evals = st.tabs(["📊 Analysis", "🧪 Evals"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Analysis
# ══════════════════════════════════════════════════════════════════════════════
with tab_analysis:

    # ── Section 1: Healthy SKUs ───────────────────────────────────────────────
    st.header("✅ Healthy SKUs")
    st.caption(
        "All metrics within threshold — no action required. "
        "GSV Var within ±8%, Trade Var ≤ 8%, Trade Efficiency Gap ≤ 3pp."
    )

    for sku_id, m in green_skus.items():
        with st.expander(
            f"**{sku_id}** — {m['brand']} | {m['segment']} | {m['channel']}",
            expanded=True,
        ):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("GSV Actual ($K)", f"{m['gsv_actual_13w']:.1f}")
            c2.metric("GSV Var%", f"{m['gsv_var_pct']:+.1%}", delta="threshold ±8%", delta_color="off")
            c3.metric("Trade Var%", f"{m['trade_var_pct']:+.1%}", delta="threshold 8%", delta_color="off")
            c4.metric("Trade Efficiency Gap", f"{m['trade_efficiency_gap']:+.1%}", delta="threshold 3pp", delta_color="off")
            c5.metric("NSV Actual ($K)", f"{m['nsv_actual_13w']:.1f}")

            st.caption(
                f"**Why no action needed:** "
                f"GSV variance of {m['gsv_var_pct']:+.1%} is within the ±8% band. "
                f"Trade spend is {m['trade_var_pct']:+.1%} vs plan — within the 8% cap. "
                f"Trade efficiency gap is {m['trade_efficiency_gap']:+.1%}, below the 3pp threshold. "
                f"NSV Actual ${m['nsv_actual_13w']:.1f}K vs Plan ${m['nsv_plan_13w']:.1f}K "
                f"({m['nsv_var_dollar']:+.1f}K)."
            )

    st.divider()

    # ── Section 2: Flagged SKUs ───────────────────────────────────────────────
    st.header("⚠️ Flagged SKUs — Action Required")
    st.caption(f"{len(flagged_skus)} SKU(s) exceeded at least one threshold and require review.")

    for sku_id, m in flagged_skus.items():
        is_revised = sku_id in revised_narratives
        expander_label = (
            f"**{sku_id}** — {m['brand']} | {m['segment']} | {m['pack_size']} | {m['channel']}"
            + (" ✏️ *revised*" if is_revised else "")
        )
        with st.expander(expander_label, expanded=True):
            for reason in m["flag_reasons"]:
                st.error(f"🚨 {reason}", icon=None)

            st.markdown("**13-Week Summary ($K)**")
            col_gsv, col_trade, col_nsv = st.columns(3)

            with col_gsv:
                st.markdown("**GSV**")
                g1, g2, g3 = st.columns(3)
                g1.metric("Plan", f"{m['gsv_plan_13w']:.1f}")
                g2.metric("Actual", f"{m['gsv_actual_13w']:.1f}", delta=f"{m['gsv_var_dollar']:+.1f}")
                g3.metric("LE", f"{m['gsv_le_13w']:.1f}")
                st.metric("GSV Var%", f"{m['gsv_var_pct']:+.1%}")

            with col_trade:
                st.markdown("**Trade Spend**")
                t1, t2, t3 = st.columns(3)
                t1.metric("Plan", f"{m['trade_plan_13w']:.1f}")
                t2.metric("Actual", f"{m['trade_actual_13w']:.1f}", delta=f"{m['trade_var_dollar']:+.1f}", delta_color="inverse")
                t3.metric("LE", f"{m['trade_le_13w']:.1f}")
                st.metric("Trade Var%", f"{m['trade_var_pct']:+.1%}")

            with col_nsv:
                st.markdown("**NSV**")
                n1, n2 = st.columns(2)
                n1.metric("Plan", f"{m['nsv_plan_13w']:.1f}")
                n2.metric("Actual", f"{m['nsv_actual_13w']:.1f}", delta=f"{m['nsv_var_dollar']:+.1f}")
                st.metric("Trade Efficiency Gap", f"{m['trade_efficiency_gap']:+.1%}")

            if m["promo_weeks"]:
                st.caption(f"**Promo weeks** (GSV Actual >125% Plan): {', '.join(m['promo_weeks'])}")

            st.markdown("---")
            st.markdown("**Analysis**")
            final_narrative = revised_narratives.get(sku_id) or narratives.get(sku_id, "_No narrative available._")
            st.markdown(final_narrative)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Evals
# ══════════════════════════════════════════════════════════════════════════════
with tab_evals:
    st.header("🧪 Evaluation Suite")

    # ── Unit Tests ────────────────────────────────────────────────────────────
    st.subheader("Unit Tests — compute_metrics")
    st.caption("Synthetic data tests that verify all metric calculations and flagging logic.")

    if "unit_test_results" not in st.session_state:
        if st.button("▶ Run Unit Tests", type="primary"):
            with st.spinner("Running 11 unit tests..."):
                st.session_state.unit_test_results = run_unit_tests()
    else:
        ut_results = st.session_state.unit_test_results
        passed = sum(1 for r in ut_results if r["passed"])
        failed = len(ut_results) - passed

        score_col, reset_col = st.columns([3, 1])
        with score_col:
            if failed == 0:
                st.success(f"All {passed} tests passed")
            else:
                st.error(f"{passed} passed / {failed} failed")
        with reset_col:
            if st.button("Re-run"):
                del st.session_state.unit_test_results
                st.rerun()

        for r in ut_results:
            icon = "✅" if r["passed"] else "❌"
            label = r["name"].replace("test_", "").replace("_", " ").title()
            with st.expander(f"{icon} {label}", expanded=not r["passed"]):
                if r["passed"]:
                    st.caption(r["detail"])
                else:
                    st.error(r["detail"])

    st.divider()

    # ── LLM Judge Results ─────────────────────────────────────────────────────
    st.subheader("LLM-as-a-Judge — Narrative Factual Accuracy")
    st.caption(
        "Runs automatically as part of the workflow. Evaluates each narrative against "
        "ground-truth metrics to catch directional errors, hallucinated numbers, or irrelevant recommendations."
    )

    if not judge_results:
        st.info("No judge results yet. Run the analysis first.")
    else:
        passes = sum(1 for r in judge_results if r["verdict"] == "PASS")
        fails = sum(1 for r in judge_results if r["verdict"] == "FAIL")
        errors = sum(1 for r in judge_results if r["verdict"] == "ERROR")

        if fails == 0 and errors == 0:
            st.success(f"All {passes} narratives passed factual accuracy check")
        else:
            st.warning(f"{passes} PASS  |  {fails} FAIL  |  {errors} ERROR")

        for r in judge_results:
            verdict = r["verdict"]
            icon = "✅" if verdict == "PASS" else ("❌" if verdict == "FAIL" else "⚠️")
            label = f"{icon} {r['sku_id']} — {r['brand']} | {r['segment']}  [{verdict}]"
            with st.expander(label, expanded=(verdict != "PASS")):
                if verdict == "PASS":
                    st.success(r["reasoning"])
                elif verdict == "FAIL":
                    st.error(r["reasoning"])
                else:
                    st.warning(r["reasoning"])

    # ── Narrative Revision ────────────────────────────────────────────────────
    failed_results = [r for r in judge_results if r["verdict"] == "FAIL"]
    if failed_results:
        st.divider()
        st.subheader("Narrative Revision")
        st.caption(
            f"The judge identified {len(failed_results)} narrative(s) with factual errors. "
            "Below are the original narrative, judge feedback, and the corrected version produced by the workflow."
        )

        for r in failed_results:
            sku_id = r["sku_id"]
            with st.expander(f"🔄 {sku_id} — {r['brand']} | {r['segment']}", expanded=True):
                col_original, col_feedback, col_revised = st.columns(3)

                with col_original:
                    st.markdown("**Original Narrative**")
                    st.markdown(narratives.get(sku_id, "_Not available._"))

                with col_feedback:
                    st.markdown("**Judge Feedback**")
                    st.error(r["reasoning"])

                with col_revised:
                    st.markdown("**Revised Narrative**")
                    revised_text = revised_narratives.get(sku_id, "_Not available._")
                    st.success(revised_text)
