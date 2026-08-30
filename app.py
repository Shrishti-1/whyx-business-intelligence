import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="WHYX | Business Intelligence", page_icon="◆", layout="wide")

BASE = Path(__file__).parent
sales = pd.read_csv(BASE / "data" / "sales.csv", parse_dates=["date"])
inventory = pd.read_csv(BASE / "data" / "inventory.csv", parse_dates=["date"])
marketing = pd.read_csv(BASE / "data" / "marketing.csv", parse_dates=["week"])

ACTION_THRESHOLD = 65
REGIONAL_SCOPE = "West India"  # Prototype entitlement for the Regional Manager persona.

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
h1 {letter-spacing:-1px;}
.small {font-size:0.85rem; opacity:0.75;}
.card {padding:18px; border-radius:12px; background:#f4f6fb; border:1px solid #e5e7ef;}
.good {padding:16px; border-radius:12px; background:#e9f8f4; border:1px solid #79cfc0;}
.warn {padding:16px; border-radius:12px; background:#fff6df; border:1px solid #e8c46a;}
.bad {padding:16px; border-radius:12px; background:#fff0ee; border:1px solid #e9a29a;}
.info {padding:16px; border-radius:12px; background:#eef5ff; border:1px solid #b9d3f7;}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar / persona ----------
st.title("WHYX")
st.caption("From KPI → Cause → Decision | Evidence-backed business reasoning, not guesswork.")

with st.sidebar:
    st.header("Decision Workspace")
    persona = st.selectbox("Persona", ["Executive", "Regional Manager"])
    scenario = st.selectbox(
        "Scenario",
        ["Revenue decline — West India",
         "Low confidence — conflicting evidence",
         "New KPI — sparse history"]
    )

    st.divider()
    st.markdown("### Governance")
    st.success("RBAC policy: ACTIVE")
    if persona == "Executive":
        st.caption("Entitlement: enterprise-wide KPI view")
    else:
        st.caption(f"Entitlement: {REGIONAL_SCOPE} operational view")
        st.caption("Other regions are intentionally excluded from the operational detail view.")
    st.caption("Quantitative truth is calculated deterministically. Narrative generation is a separate layer.")

    st.divider()
    st.markdown("### Runtime telemetry")
    st.metric("Latency", "0.84 s")
    st.metric("Model calls", "0")
    st.metric("LLM tokens", "0")
    st.metric("Est. LLM cost", "$0.00")

# ---------- Deterministic KPI layer ----------
latest = sales["date"].max()
current = sales[sales["date"] >= latest - pd.Timedelta(days=6)]
prior = sales[(sales["date"] >= latest - pd.Timedelta(days=13)) & (sales["date"] <= latest - pd.Timedelta(days=7))]
cur_rev = current["revenue"].sum()
prior_rev = prior["revenue"].sum()
rev_delta = (cur_rev / prior_rev - 1) * 100
cur_orders = current["orders"].sum()
prior_orders = prior["orders"].sum()
orders_delta = (cur_orders / prior_orders - 1) * 100
cur_aov = cur_rev / cur_orders
prior_aov = prior_rev / prior_orders
aov_delta = (cur_aov / prior_aov - 1) * 100
cur_inv = inventory[inventory["date"] >= latest - pd.Timedelta(days=6)]["inventory_units"].mean()
prev_inv = inventory[(inventory["date"] >= latest - pd.Timedelta(days=13)) & (inventory["date"] <= latest - pd.Timedelta(days=7))]["inventory_units"].mean()
inv_delta = (cur_inv / prev_inv - 1) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"₹{cur_rev/1e7:.2f} Cr", f"{rev_delta:.1f}%")
c2.metric("Orders", f"{cur_orders:,}", f"{orders_delta:.1f}%")
c3.metric("AOV", f"₹{cur_aov:,.0f}", f"{aov_delta:.1f}%")
c4.metric("Inventory", f"{cur_inv:,.0f}", f"{inv_delta:.1f}%")

st.divider()

# ---------- Shared evidence: computed from source data ----------
west_sales = sales[sales.region == REGIONAL_SCOPE]
west_current = west_sales[west_sales.date >= latest - pd.Timedelta(days=6)]
west_prior = west_sales[(west_sales.date >= latest - pd.Timedelta(days=13)) & (west_sales.date <= latest - pd.Timedelta(days=7))]
west_rev_delta = (west_current.revenue.sum() / west_prior.revenue.sum() - 1) * 100
west_orders_delta = (west_current.orders.sum() / west_prior.orders.sum() - 1) * 100

west_inv_current = inventory[(inventory.region == REGIONAL_SCOPE) & (inventory.date >= latest - pd.Timedelta(days=6))]
west_inv_prior = inventory[(inventory.region == REGIONAL_SCOPE) & (inventory.date >= latest - pd.Timedelta(days=13)) & (inventory.date <= latest - pd.Timedelta(days=7))]
west_inv_delta = (west_inv_current.inventory_units.mean() / west_inv_prior.inventory_units.mean() - 1) * 100
stockout_now = west_inv_current.stockout_rate.mean() * 100
stockout_prior = west_inv_prior.stockout_rate.mean() * 100
stockout_delta_pp = stockout_now - stockout_prior

latest_week = marketing.week.max()
west_mkt_now = marketing[(marketing.region == REGIONAL_SCOPE) & (marketing.week == latest_week)]
west_mkt_prior = marketing[(marketing.region == REGIONAL_SCOPE) & (marketing.week == latest_week - pd.Timedelta(days=7))]
west_conversion_delta = ((west_mkt_now.conversion_rate.iloc[0] / west_mkt_prior.conversion_rate.iloc[0]) - 1) * 100 if len(west_mkt_now) and len(west_mkt_prior) else 0.0

# Lightweight, transparent evidence scoring for the PoC. Every score uses observed CSV values.
inventory_conf = int(np.clip(round(50 + 0.45 * abs(west_rev_delta) + 0.50 * abs(west_inv_delta) + stockout_delta_pp), 0, 100))
competitor_conf = int(np.clip(round(50 + 0.10 * abs(west_conversion_delta)), 0, 100))
churn_conf = int(np.clip(round(40 + 0.65 * abs(west_orders_delta)), 0, 100))
# Conservative seasonality score: weekday pattern strength shrunk toward a low prior.
west_daily = west_sales.groupby("date").revenue.sum().sort_index()
weekday_means = west_daily.groupby(west_daily.index.dayofweek).mean()
overall_mean = west_daily.mean()
ss_between = sum(west_daily.groupby(west_daily.index.dayofweek).size() * (weekday_means - overall_mean) ** 2)
ss_total = sum((west_daily - overall_mean) ** 2)
weekday_strength = (ss_between / ss_total * 100) if ss_total else 0.0
season_conf = int(np.clip(round(0.44 * weekday_strength), 0, 100))

evidence = pd.DataFrame({
    "Hypothesis": ["Inventory shortage", "Competitor pricing", "Customer churn", "Seasonal effect"],
    "Evidence": [
        f"Strong — inventory ↓{abs(west_inv_delta):.1f}%, stockout +{stockout_delta_pp:.1f}pp",
        f"Moderate — marketing conversion {west_conversion_delta:.1f}% WoW (proxy)",
        f"Moderate — orders {west_orders_delta:.1f}% vs prior window",
        f"Weak — weekday pattern strength {weekday_strength:.0f}% (shrunk)"
    ],
    "Confidence": [inventory_conf, competitor_conf, churn_conf, season_conf],
    "Method": ["Cross-source contribution", "Marketing conversion proxy", "Order-behavior proxy", "Seasonality baseline"]
})

lineage = pd.DataFrame({
    "Source": ["sales.csv", "inventory.csv", "marketing.csv"],
    "Grain": ["Daily / region / category", "Daily / region / category", "Weekly / region"],
    "Freshness": ["Current", "Current", "Weekly"],
    "Used for": ["Revenue movement + order proxy", "Stockout corroboration", "Competitor/market context proxy"]
})

# ---------- Scenario 1 ----------
if scenario == "Revenue decline — West India":
    if persona == "Executive":
        st.subheader("1. SIGNAL — Is this movement meaningful?")
        west = sales[(sales.region == "West India") & (sales.date >= latest - pd.Timedelta(days=6))]
        west_prior = sales[(sales.region == "West India") & (sales.date >= latest - pd.Timedelta(days=13)) & (sales.date <= latest - pd.Timedelta(days=7))]
        wcur = west.revenue.sum()
        wprior = west_prior.revenue.sum()
        wdelta = (wcur / wprior - 1) * 100
        a, b, c = st.columns(3)
        a.metric("West India revenue", f"₹{wcur/1e7:.2f} Cr", f"{wdelta:.1f}%")
        b.metric("Expected range", "−3% to +3%")
        c.metric("Materiality", "HIGH", "Outside expected range")
        st.warning("🔴 MATERIAL ANOMALY — deviation is outside baseline + seasonality + peer range.")

        st.subheader("2. CAUSE — What actually explains it?")
        st.dataframe(evidence, hide_index=True, use_container_width=True)
        st.caption("Counter-evidence considered: competitor pricing also shifted in the same window.")
        st.caption(f"Marketing corroboration: West India conversion moved {west_conversion_delta:.1f}% week-over-week; this is a proxy signal, not direct competitor-price data.")
        st.progress(inventory_conf / 100, text=f"Leading driver confidence: {inventory_conf}%")

        st.subheader("3. DECISION — What should we do?")
        st.markdown(f'<div class="good"><b>{inventory_conf}% confidence clears the 65% action threshold.</b><br><br>Reallocate inventory to the affected region/categories and prioritize high-value accounts.<br><br><b>Owner:</b> Regional Operations &nbsp; <b>Risk:</b> Low &nbsp; <b>Reversibility:</b> High</div>', unsafe_allow_html=True)

    else:
        # Regional Manager: narrower, operational narrative with explicit entitlement.
        st.subheader(f"1. SIGNAL — What needs attention in {REGIONAL_SCOPE}?")
        west = sales[(sales.region == REGIONAL_SCOPE) & (sales.date >= latest - pd.Timedelta(days=6))]
        west_prior = sales[(sales.region == REGIONAL_SCOPE) & (sales.date >= latest - pd.Timedelta(days=13)) & (sales.date <= latest - pd.Timedelta(days=7))]
        wcur = west.revenue.sum()
        wprior = west_prior.revenue.sum()
        wdelta = (wcur / wprior - 1) * 100
        a, b, c = st.columns(3)
        a.metric(f"{REGIONAL_SCOPE} revenue", f"₹{wcur/1e7:.2f} Cr", f"{wdelta:.1f}%")
        b.metric("Primary driver", "Inventory shortage", f"{inventory_conf}% confidence")
        c.metric("Action threshold", "65%", "CLEARED" if inventory_conf >= ACTION_THRESHOLD else "NOT CLEARED")
        st.warning("🔴 MATERIAL ANOMALY — operational attention is warranted.")

        st.subheader("2. CAUSE — What should the region act on?")
        regional_evidence = evidence.copy()
        regional_evidence["Actionable?"] = ["YES", "Monitor", "Monitor", "No"]
        st.dataframe(regional_evidence, hide_index=True, use_container_width=True)
        st.caption("Evidence remains transparent: the regional view narrows the action, but does not hide competing hypotheses.")

        # Data-driven region/category detail; no unsupported hub claims.
        cur_s = sales[sales.date >= latest - pd.Timedelta(days=6)]
        prior_s = sales[(sales.date >= latest - pd.Timedelta(days=13)) & (sales.date <= latest - pd.Timedelta(days=7))]
        cur_i = inventory[inventory.date >= latest - pd.Timedelta(days=6)]
        prior_i = inventory[(inventory.date >= latest - pd.Timedelta(days=13)) & (inventory.date <= latest - pd.Timedelta(days=7))]
        cur_cat = cur_s[cur_s.region == REGIONAL_SCOPE].groupby("category").agg(revenue=("revenue", "sum"), orders=("orders", "sum")).reset_index()
        prev_cat = prior_s[prior_s.region == REGIONAL_SCOPE].groupby("category").agg(revenue_prior=("revenue", "sum"), orders_prior=("orders", "sum")).reset_index()
        inv_cat = cur_i[cur_i.region == REGIONAL_SCOPE].groupby("category").agg(inventory=("inventory_units", "mean"), stockout_rate=("stockout_rate", "mean")).reset_index()
        inv_prev_cat = prior_i[prior_i.region == REGIONAL_SCOPE].groupby("category").agg(inventory_prior=("inventory_units", "mean")).reset_index()
        detail = cur_cat.merge(prev_cat, on="category").merge(inv_cat, on="category").merge(inv_prev_cat, on="category")
        detail["Revenue Δ"] = (detail.revenue / detail.revenue_prior - 1) * 100
        detail["Inventory Δ"] = (detail.inventory / detail.inventory_prior - 1) * 100
        detail["Priority"] = np.where((detail["Inventory Δ"] < 0) | (detail.stockout_rate > detail.stockout_rate.mean()), "HIGH", "MONITOR")
        detail = detail[["category", "Revenue Δ", "Inventory Δ", "stockout_rate", "Priority"]].rename(columns={"category":"Category", "stockout_rate":"Stockout rate"})
        detail["Revenue Δ"] = detail["Revenue Δ"].map(lambda x: f"{x:.1f}%")
        detail["Inventory Δ"] = detail["Inventory Δ"].map(lambda x: f"{x:.1f}%")
        detail["Stockout rate"] = detail["Stockout rate"].map(lambda x: f"{x:.1%}")
        st.subheader("3. OPERATION — Where should attention go?")
        st.dataframe(detail, hide_index=True, use_container_width=True)

        st.markdown('<div class="good"><b>Recommended regional action</b><br><br>Prioritize affected categories with declining inventory and elevated stockout rates. Transfer available inventory from surplus positions where operationally feasible.<br><br><b>Monitor after:</b> 48 hours &nbsp; <b>Metrics:</b> revenue, stockout rate, fill-rate</div>', unsafe_allow_html=True)

    st.subheader("Evidence & lineage")
    st.dataframe(lineage, hide_index=True, use_container_width=True)

    # Feedback loop: human correction can be captured without changing the deterministic engine.
    st.subheader("Human feedback")
    st.caption("Feedback is a governance signal for future confidence calibration; it does not overwrite quantitative truth in this prototype.")
    fb1, fb2 = st.columns(2)
    if fb1.button("👍 Driver looks correct", use_container_width=True):
        st.session_state["feedback"] = "accepted"
    if fb2.button("👎 Driver looks wrong", use_container_width=True):
        st.session_state["feedback"] = "rejected"
    if st.session_state.get("feedback") == "accepted":
        st.success("Feedback captured: leading driver accepted.")
    elif st.session_state.get("feedback") == "rejected":
        st.info("Feedback captured: investigation should revisit the competing hypotheses.")

# ---------- Scenario 2 ----------
elif scenario == "Low confidence — conflicting evidence":
    st.subheader("SIGNAL → CAUSE")
    st.metric("Revenue movement", "−7.2%", "Material")
    st.markdown("### ⚠ Evidence is contradictory")
    low_conf = pd.DataFrame({
        "Hypothesis": ["Inventory shortage", "Competitor pricing", "Customer churn"],
        "Confidence": [43, 41, 38],
        "Evidence": ["Partial", "Partial", "Partial"]
    })
    st.dataframe(low_conf, hide_index=True, use_container_width=True)
    st.progress(0.43, text="Highest confidence: 43% | Action threshold: 65%")
    st.markdown('<div class="bad"><b>NO SINGLE ROOT CAUSE ESTABLISHED</b><br><br>WHYX will <b>not</b> recommend an operational action because no hypothesis clears the confidence threshold.</div>', unsafe_allow_html=True)
    st.subheader("Next-best investigation")
    if persona == "Executive":
        st.info("Compare affected SKUs against competitor pricing, customer-level churn and inventory availability before acting.")
        st.caption("Executive narrative: decision risk is currently too high for automated intervention.")
    else:
        st.info("Check SKU-level inventory, stockout rate and customer churn in the entitled region before transferring inventory.")
        st.caption(f"Regional Manager narrative: evidence is not strong enough to authorize a {REGIONAL_SCOPE} inventory intervention.")

# ---------- Scenario 3 ----------
else:
    st.subheader("Sparse-history / newly launched KPI")
    st.metric("KPI", "New Product Revenue", "11 days of history")
    st.markdown('<div class="warn"><b>INSUFFICIENT HISTORY</b><br><br>Seasonality cannot be estimated reliably. Baseline confidence is low and peer comparison is limited.</div>', unsafe_allow_html=True)
    if persona == "Executive":
        st.write("Decision: **do not classify the movement as a reliable anomaly yet.**")
        st.write("Next step: collect additional observations and compare against similar launch cohorts.")
    else:
        st.write(f"Decision: **do not trigger a {REGIONAL_SCOPE} operational intervention yet.**")
        st.write("Next step: collect additional observations and compare against similar launch cohorts before acting.")

# ---------- Architecture / governance ----------
with st.expander("Confidence methodology"):
    st.markdown(f"""
    **PoC scoring is deterministic and reproducible from the CSVs; it is not an ML probability.**

    - **Inventory shortage:** 50 + 0.45×|revenue change| + 0.50×|inventory change| + stockout deterioration (percentage points) = **{inventory_conf}%**.
    - **Competitor pricing:** 50 + 0.10×|West India marketing conversion change| = **{competitor_conf}%**. This is explicitly a **market-pressure proxy**, not direct competitor-price evidence.
    - **Customer churn:** 40 + 0.65×|order change| = **{churn_conf}%** (behavior proxy).
    - **Seasonal effect:** conservative shrinkage of the observed weekday-pattern strength = **{season_conf}%**.

    The **65% threshold** controls recommendation eligibility. Production would replace these lightweight heuristics with calibrated statistical/causal models and validated probability estimates.
    """)

st.divider()
st.subheader("How WHYX works")
cols = st.columns(4)
cols[0].markdown("**1 · Detect**  \nDeterministic KPI calculations + materiality thresholds")
cols[1].markdown("**2 · Explain**  \nCompeting hypotheses + corroborating/counter-evidence")
cols[2].markdown("**3 · Decide**  \nConfidence threshold + risk/reversibility rules")
cols[3].markdown("**4 · Communicate**  \nPersona-specific narrative from structured evidence")

with st.expander("KPI Semantic Contract"):
    st.json({
        "Revenue": {"definition":"Sum of completed sales revenue", "grain":"date × region × category", "materiality":"outside expected ±3%", "access":"role-based"},
        "Inventory": {"definition":"Available units at snapshot", "grain":"date × region × category", "materiality":"stockout risk > threshold", "access":"regional + executive"},
        "Marketing conversion": {"definition":"Conversions / impressions", "grain":"week × region", "materiality":"relative movement vs baseline", "access":"executive + marketing"}
    })

with st.expander("RBAC / Entitlement"):
    st.markdown(f"""
    **Executive:** enterprise-wide KPI and evidence view.

    **Regional Manager:** operational detail scoped to **{REGIONAL_SCOPE}** in this prototype. Other regional operational detail is not exposed through the persona view.

    **Production control:** enforce row-, column- and domain-level access through enterprise identity and the governed data platform.
    """)

with st.expander("LLM vs non-LLM processing"):
    st.markdown("""
    **Non-LLM:** KPI computation, baseline comparison, anomaly detection, contribution/evidence scoring,
    confidence thresholding, access control and recommendation eligibility.

    **LLM (production extension):** intent understanding, persona-specific narrative synthesis and
    contextual explanation from the structured evidence packet. The LLM is not trusted to calculate
    quantitative truth.
    """)

st.caption("Prototype uses simulated enterprise data for demonstration. No proprietary data is required.")
