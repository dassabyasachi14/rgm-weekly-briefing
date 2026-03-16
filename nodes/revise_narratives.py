from evals.llm_judge import revise_narratives as _revise


def revise_narratives(state: dict) -> dict:
    judge_results = state.get("judge_results") or []
    fails = [r for r in judge_results if r["verdict"] == "FAIL"]

    if not fails:
        print("revise_narratives: no failures to revise — skipping")
        return {"revised_narrative": {}}

    print(f"revise_narratives: revising {len(fails)} narrative(s)...")
    revised = _revise(state["metrics"], state["narrative"], judge_results)
    print(f"revise_narratives: done")
    return {"revised_narrative": revised}
