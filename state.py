from typing import TypedDict
import pandas as pd


class RGMState(TypedDict):
    raw_df: pd.DataFrame
    metrics: dict
    narrative: dict
    judge_results: list
    revised_narrative: dict
    report: str
