# WHYX — Business Intelligence AI

> **From KPI → Cause → Decision**

WHYX is a proof-of-concept KPI intelligence-to-action engine designed to reduce the gap between a dashboard signal and a defensible business decision. Instead of only reporting that revenue moved, WHYX tests whether the movement is meaningful, evaluates competing explanations, and recommends action only when evidence clears a governed threshold.

## Problem

Dashboards tell leaders **what changed**, but the reasoning from KPI movement to root cause and action is often manual. WHYX focuses on three questions:

1. Is the movement meaningful?
2. What explains it?
3. What should we do — and how sure are we?

A core design principle is **abstention**: if evidence is insufficient or contradictory, WHYX does not guess.

## Target users

- **Executives / business leaders:** enterprise KPI movement, evidence, confidence, decision risk and recommended action.
- **Regional managers / operations leaders:** entitled regional and category-level detail, operational levers and monitoring plans.
- **Analysts (production extension):** evidence lineage, hypothesis diagnostics and human feedback for calibration.

## Round-2 prototype coverage

- 3 connected simulated data sources: sales, inventory and marketing
- 4 KPIs: revenue, orders, AOV and inventory
- Different data grains/cadences
- KPI semantic contract
- Executive and Regional Manager personas
- Multi-factor revenue movement
- Competing hypotheses with deterministic, data-derived PoC confidence scores
- Low-confidence abstention scenario
- Sparse-history/new-KPI scenario
- Role-based access demonstration
- Evidence/lineage display
- Explicit LLM vs non-LLM separation
- Runtime telemetry including latency, model calls, token usage and estimated cost

## Submission Links:

### Final Presentation
https://drive.google.com/file/d/1UhKc3JGCWT8ed7NNEimnGjqhRac3Fd6c/view?usp=sharing

### Prototype Demo Video
https://drive.google.com/file/d/1PPo1-ZrLJifZV2wQ9XknCq30G5ooyQY6/view?usp=sharing

---

## Solution architecture

```text
Sales / Inventory / Marketing
            |
            v
   Data reconciliation
   + KPI semantic layer
            |
            v
 Deterministic analytical engine
 anomaly + contribution analysis
            |
            v
   Driver / evidence engine
 competing hypotheses + counter-evidence
            |
            v
      Confidence engine
   threshold + abstention logic
            |
            v
     Decision workspace
 driver → lever → action → owner → monitoring
            |
            v
     Narrative layer
 persona-specific explanation
```

### Key principle

**Numbers are deterministic. Narratives are generative.**

The prototype does not use an LLM to calculate KPI values or recommendation eligibility. A production deployment can add an LLM for intent understanding and narrative synthesis after the analytical engine produces a structured evidence packet.

## Data sources and lineage

- `data/sales.csv` — daily, region/category grain; used for revenue movement and order-behavior evidence.
- `data/inventory.csv` — daily, region/category grain; used for inventory and stockout corroboration.
- `data/marketing.csv` — weekly, region grain; used for conversion context as a market-pressure proxy.

The application surfaces this lineage explicitly. Marketing is not decorative: West India conversion change is used in the competitor/market-pressure hypothesis. It is clearly labelled as a **proxy**, not direct competitor-price data.

## KPI semantic contract

| KPI | Definition | Grain | Example materiality |
|---|---|---|---|
| Revenue | Sum of completed sales revenue | date × region × category | outside expected ±3% |
| Orders | Completed orders | date × region × category | relative movement vs baseline |
| AOV | Revenue / Orders | date × region × category | relative movement vs baseline |
| Inventory | Available units | date × region × category | stockout risk threshold |
| Marketing conversion | Conversions / impressions (represented by `conversion_rate`) | week × region | relative movement vs baseline |

## Analytical approach

The PoC intentionally uses lightweight deterministic heuristics rather than pretending to have a production causal model. KPI movement and evidence inputs are computed from the CSVs, then converted into reproducible evidence scores.

### Confidence and abstention

For the West India revenue-decline scenario, the displayed scores are **computed from observed source values**, not hardcoded labels:

- Inventory shortage — **78%**: revenue movement + inventory deterioration + stockout deterioration.
- Competitor pricing — **51%**: marketing conversion movement as a market-pressure proxy.
- Customer churn — **46%**: order movement as a customer-behavior proxy.
- Seasonal effect — **21%**: observed weekday-pattern strength with conservative shrinkage.

The prototype uses a **65% action threshold**. If a hypothesis clears the threshold and the proposed action is low-risk/reversible, WHYX can recommend action. If no hypothesis clears it, WHYX **abstains** and proposes the next-best investigation.

These scores are **not calibrated probabilities**. Production would replace the heuristics with validated statistical/causal models, calibrated confidence estimates and historical backtesting.

## Personas and security

### Executive
Receives concise strategic impact, confidence, risk and ownership with enterprise-wide KPI/evidence visibility.

### Regional Manager
Receives operational detail scoped to **West India** in this prototype, including category-level inventory and stockout signals. Other regional operational detail is intentionally excluded from this persona view.

### Production security
The prototype demonstrates the RBAC concept. Production should enforce row-, column- and domain-level controls through enterprise identity, governed data access and auditable policy enforcement.

## Key risks and mitigations

| Risk | Mitigation |
|---|---|
| False confidence / spurious root cause | Calibrated confidence, corroborating + counter-evidence, 65% threshold and abstention |
| Proxy evidence mistaken for causal proof | Label proxy signals explicitly; add validated causal inference and experiment data in production |
| Data freshness / KPI semantic drift | Governed KPI semantic contract, source lineage and freshness checks |
| Overexposure of operational data | Persona-scoped views plus production row/column/domain-level access controls |
| Recommendation causes unintended operational impact | Risk/reversibility rules, owner assignment and post-action monitoring |
| LLM hallucination of quantitative facts | Keep quantitative truth outside the LLM; pass a structured evidence packet to the narrative layer |

## LLM vs non-LLM processing

**Non-LLM:** KPI computation, baseline comparison, anomaly detection, evidence scoring, confidence thresholding, access control and recommendation eligibility.

**LLM (production extension):** intent understanding, persona-specific narrative synthesis and contextual explanation from the structured evidence packet. The LLM is not trusted to calculate quantitative truth.

## Runtime telemetry

The prototype exposes example runtime telemetry for:

- latency
- model calls
- LLM token usage
- estimated LLM cost

The current PoC uses **0 model calls / 0 LLM tokens / $0.00 LLM cost** because the analytical path is deterministic. Production telemetry should capture actual model latency, token counts, cache hits, cost per insight and failure rates.

## Run locally

```bash
git clone <your-public-repository-url>
cd WHYX_submission
pip install -r requirements.txt
streamlit run app.py
```

The application will open in your browser.

## Project structure

```text
WHYX_submission/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   ├── sales.csv
│   ├── inventory.csv
│   └── marketing.csv
└── screenshots/
```

## Limitations

This is a proof-of-concept using simulated data. Confidence scoring is deliberately lightweight and deterministic; it should not be interpreted as calibrated probability. Production deployment would require validated statistical/causal methods, enterprise connectors, calibrated confidence, stronger access controls, observability, human feedback loops and continuous evaluation.

## Roadmap

1. Enterprise data connectors and governed KPI catalog
2. Statistical/causal driver analysis
3. Retrieval-backed evidence and source citations
4. Human feedback and confidence calibration
5. Continuous drift and quality monitoring
6. Production security, audit and cost optimization
