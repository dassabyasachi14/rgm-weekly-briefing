# RGM Weekly Briefing

An agentic LangGraph workflow that ingests weekly pet food sales data, computes GSV and trade spend variances, flags underperforming SKUs, and generates an LLM-written briefing — complete with factual evaluation and auto-correction.

---

## What it does

1. **Loads** weekly Excel data (10 SKUs × 13 weeks)
2. **Computes** 13-week GSV, Trade, and NSV metrics per SKU using pandas
3. **Flags** SKUs that breach any threshold (GSV var >±8%, trade overspend >8%, trade efficiency gap >3pp)
4. **Generates** LLM narratives for flagged SKUs — business interpretation, which weeks drove variance, recommended actions
5. **Evaluates** each narrative with an LLM-as-a-judge for factual accuracy against the ground-truth metrics
6. **Revises** any narrative the judge flags as incorrect, using judge feedback as context
7. **Outputs** a Streamlit dashboard and a markdown report (`output/report.md`)

---

## Graph structure

```
load_data → compute_metrics → generate_narrative → evaluate_narratives → revise_narratives → format_output
```

All nodes are linear (no conditional routing). The LLM never does arithmetic — all numbers come from pandas.

---

## Project structure

```
├── main.py                        # builds and runs the LangGraph graph
├── state.py                       # RGMState TypedDict
├── app.py                         # Streamlit UI
├── nodes/
│   ├── load_data.py               # reads Excel, returns raw DataFrame
│   ├── compute_metrics.py         # 13W totals, variances, promo detection, flags
│   ├── generate_narrative.py      # LLM node — narratives for flagged SKUs
│   ├── evaluate_narratives.py     # LLM-as-a-judge node
│   ├── revise_narratives.py       # revision node — fixes judge-flagged narratives
│   └── format_output.py           # assembles markdown report
├── evals/
│   ├── llm_judge.py               # judge prompt, revision prompt, Gemini calls
│   └── unit_tests.py              # 11 synthetic unit tests for compute_metrics
├── data/
│   └── pet_food_rgm_data_v2.xlsx  # source data (Weekly Raw Data sheet)
├── requirements.txt
└── .env                           # not committed — see setup below
```

---

## Setup

**1. Clone and create a virtual environment**
```bash
git clone https://github.com/dassabyasachi14/rgm-weekly-briefing.git
cd rgm-weekly-briefing
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

**2. Add your API key**

Create a `.env` file in the project root:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey). The workflow uses `gemini-2.5-flash`.

---

## Running

**Streamlit UI (recommended)**
```bash
python -m streamlit run app.py
```
- Click **▶ Run Analysis** in the sidebar to run the full workflow
- **Analysis tab** — healthy SKUs summary table + flagged SKU detail with final (revised) narratives
- **Evals tab** — unit test runner + LLM judge verdicts + original/feedback/revised narrative comparison for any failures

**CLI**
```bash
python main.py
```
Runs the full graph and writes `output/report.md`.

---

## Flagging thresholds

| Metric | Threshold |
|--------|-----------|
| GSV Variance % | > ±8% |
| Trade Variance % | > 8% |
| Trade Efficiency Gap | > 3pp |

Trade Efficiency Gap = `trade_var_pct − gsv_var_pct`. A positive value means trade spend is growing faster than revenue — a concern.

---

## Eval suite

**Unit tests** — 11 synthetic tests covering all metric calculations and flagging logic in `compute_metrics`. Run from the Evals tab in the UI.

**LLM-as-a-judge** — runs automatically as part of the workflow. A second Gemini call reviews each narrative against the ground-truth metrics and returns PASS/FAIL with reasoning. Failed narratives are automatically revised before the final report is produced.

---

## Tech stack

- Python 3.11+
- [LangGraph](https://github.com/langchain-ai/langgraph) — StateGraph orchestration
- [langchain-google-genai](https://python.langchain.com/docs/integrations/llms/google_ai/) — Gemini via `ChatGoogleGenerativeAI`
- pandas + openpyxl — data ingestion and metric computation
- Streamlit — interactive dashboard
