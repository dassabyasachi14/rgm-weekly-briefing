from evals.llm_judge import run_llm_judge


def evaluate_narratives(state: dict) -> dict:
    narratives = state.get("narrative") or {}
    if not narratives:
        print("evaluate_narratives: no narratives to judge — skipping")
        return {"judge_results": []}

    results = run_llm_judge(state["metrics"], narratives)
    passes = sum(1 for r in results if r["verdict"] == "PASS")
    fails = sum(1 for r in results if r["verdict"] == "FAIL")
    print(f"evaluate_narratives: {passes} PASS, {fails} FAIL")
    return {"judge_results": results}
