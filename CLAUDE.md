# RGM Agentic Workflow — Project Context

## What this project does
A LangGraph workflow that ingests weekly Pet Food sales data, computes GSV and trade spend variances, and generates an RGM (Revenue Growth Management) briefing. Healthy SKUs are summarised in a green status block. Flagged SKUs (where variance exceeds threshold) get a detailed LLM-generated narrative with interpretation and recommended actions.

---

## Tech Stack
- Python 3.11+
- LangGraph (StateGraph, linear graph, no conditional routing)
- Gemini via langchain-google-genai
- pandas for all data manipulation and metric computation
- openpyxl for Excel ingestion
- Output: markdown file + terminal print

---

## Data Source
Single Excel file: `data/pet_food_rgm_data_v2.xlsx`

Two sheets are used:
- **Weekly Raw Data** — 10 SKUs × 13 weeks × 6 metrics per week (GSV Plan, GSV Actual, GSV LE, Trade Plan, Trade Actual, Trade LE). Each metric has its own column per week, so 78 data columns + 5 meta columns.
- **13W Summary Dashboard** — pre-computed totals. Do NOT use this sheet in the workflow. Always compute totals from Weekly Raw Data to ensure consistency.

### SKU meta columns (Weekly Raw Data)
| Column | Description |
|--------|-------------|
| SKU ID | e.g. PF-001 |
| Brand | NutriPaws / VitaCat / PureProtein |
| Segment | Dry Dog Food / Wet Dog Food / Dry Cat Food / Wet Cat Food / Treats & Snacks |
| Pack Size | e.g. 5kg, 400g x6 |
| Channel | Grocery / Mass / Pet Specialty |

### Key business terms
- **GSV** — Gross Sales Value. Revenue before trade deductions ($K)
- **Trade Spend** — Payments to retailers to fund promotions ($K)
- **NSV** — Net Sales Value = GSV Actual minus Trade Actual ($K)
- **Plan** — Locked annual target, prorated weekly. Never changes.
- **LE (Latest Estimate)** — Current forward projection of year-end landing, refreshed periodically. Reflects latest business intelligence.
- **Variance** — Actual minus Plan ($ and %). Positive variance = above plan for GSV (good). Positive variance = overspend for Trade (concern).

---

## Folder Structure
```
rgm_workflow/
├── main.py                  # builds and runs the graph
├── state.py                 # RGMState TypedDict
├── nodes/
│   ├── load_data.py         # reads Excel, returns raw DataFrame
│   ├── compute_metrics.py   # 13W totals, variances, promo detection, flags
│   ├── generate_narrative.py # LLM node for flagged SKUs only
│   └── format_output.py     # assembles final markdown report
├── data/
│   └── pet_food_rgm_data_v2.xlsx
└── requirements.txt
```

---

## State
```python
class RGMState(TypedDict):
    raw_df: pd.DataFrame   # weekly raw data from Excel
    metrics: dict          # computed summaries + flags per SKU
    narrative: str         # LLM output for flagged SKUs
    report: str            # final formatted output
```

---

## Graph Structure
Four linear nodes. No conditional routing.
```
load_data → compute_metrics → generate_narrative → format_output
```

---

## Compute Metrics Logic
All arithmetic happens in `compute_metrics.py` using pandas. The LLM never does math.

### Per SKU, compute:
- `gsv_plan_13w` — sum of GSV Plan across 13 weeks
- `gsv_actual_13w` — sum of GSV Actual across 13 weeks
- `gsv_le_13w` — sum of GSV LE across 13 weeks
- `gsv_var_dollar` — gsv_actual_13w minus gsv_plan_13w
- `gsv_var_pct` — gsv_var_dollar / gsv_plan_13w
- `trade_plan_13w` — sum of Trade Plan across 13 weeks
- `trade_actual_13w` — sum of Trade Actual across 13 weeks
- `trade_var_dollar` — trade_actual_13w minus trade_plan_13w
- `trade_var_pct` — trade_var_dollar / trade_plan_13w
- `nsv_actual_13w` — gsv_actual_13w minus trade_actual_13w
- `nsv_plan_13w` — gsv_plan_13w minus trade_plan_13w
- `nsv_var_dollar` — nsv_actual_13w minus nsv_plan_13w
- `trade_efficiency_gap` — trade_var_pct minus gsv_var_pct (positive = trade growing faster than GSV, a concern)
- `promo_weeks` — list of week labels where GSV Actual > 25% above GSV Plan for that week

### Flagging thresholds:
A SKU is flagged if ANY of these are true:
- `abs(gsv_var_pct) > 0.08` (GSV variance > 8% above or below plan)
- `trade_var_pct > 0.08` (trade overspend > 8%)
- `trade_efficiency_gap > 0.03` (trade growing >3pp faster than GSV)

Flagged SKUs get detailed LLM narrative. Non-flagged SKUs go into the green summary block.

---

## LLM Node
Model: `gemini-2.5-flash` via `langchain-google-genai`

The LLM receives a pre-formatted string per flagged SKU containing:
1. SKU metadata (brand, segment, channel)
2. 13W summary metrics (all computed values above)
3. Weekly series — one row per week with GSV Plan, Actual, LE, Trade Plan, Trade Actual
4. Computed flags that triggered the alert

The LLM should output for each flagged SKU:
- 2–3 sentence interpretation of what the numbers mean in plain business language
- Identification of which weeks drove the variance
- 1–2 specific recommended actions for the RGM Associate

Keep the output concise. No bullet-point overload. Write it as a professional would speak to a colleague.

---

## Output Format
A single markdown report with two sections:

### Section 1 — Green SKUs
A single table listing all non-flagged SKUs with their 13W GSV Actual, GSV Var%, Trade Var%, and NSV Actual. Label this section with ✅.

### Section 2 — Flagged SKUs
One block per flagged SKU with:
- Header: SKU ID | Brand | Segment | Channel
- Summary metrics table
- LLM narrative
Label this section with ⚠️.

Save output to `output/report.md` and also print to terminal.

---

## Coding Conventions
- Keep each node function focused — one responsibility only
- No LLM calls outside of `generate_narrative.py`
- No hardcoded column names scattered across files — parse column names dynamically from the Excel header row
- Use f-strings for string formatting
- No unnecessary comments — code should be self-explanatory
- If something can be done with pandas, do it with pandas
