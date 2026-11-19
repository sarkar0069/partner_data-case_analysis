import streamlit as st, pandas as pd, plotly.express as px
from core import *

st.set_page_config(page_title="Partner Performance Program", layout="wide")
st.title("Partner Performance Improvement Program")

@st.cache_data
def _d(): return load_supply()
@st.cache_data
def _q(): return load_quality()
d, q = _d(), _q()

tab0, tab1, tab2, tab3 = st.tabs(["Summary", "Part 1: Point structure & budget", "Part 2: Partner quality", "Data insights"])

# ---------- Part 1 ----------
with tab1:
    st.sidebar.header("Part 1 levers")
    r = {"Sun/Mon": st.sidebar.slider("Points/hr Sun & Mon", 0.0, 3.0, 1.5, 0.25),
         "Fri/Sat": st.sidebar.slider("Points/hr Fri & Sat", 0.0, 3.0, 1.0, 0.25),
         "Tue-Thu": st.sidebar.slider("Points/hr Tue-Thu", 0.0, 3.0, 0.5, 0.25)}
    cap = st.sidebar.slider("Max hours counted per day", 6, 16, 12)
    amin = st.sidebar.slider("Hours for an 'active day'", 1, 8, 4)
    b5 = st.sidebar.number_input("Weekly bonus: 5+ active days", 0, 100, 10)
    b7 = st.sidebar.number_input("Weekly bonus: all 7 active days", 0, 200, 25)
    st.sidebar.header("Stress test (behaviour change)")
    hu = st.sidebar.slider("Supply hours increase %", 0, 30, 10) / 100
    tu = st.sidebar.slider("Tasks increase %", 0, 30, 5) / 100
    bu = st.sidebar.slider("More partners hitting bonus %", 0, 100, 25) / 100
    p = dict(rates=r, cap=cap, active_min=amin, bonus5=b5, bonus7=b7)

    st.subheader("Proposed point structure (1 point = Rs 1)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sun & Mon (highest demand)", f"{r['Sun/Mon']} pts / hour")
    c2.metric("Fri & Sat", f"{r['Fri/Sat']} pts / hour")
    c3.metric("Tue, Wed, Thu", f"{r['Tue-Thu']} pts / hour")
    st.info(f"Bonus (consistency): online {amin}+ hrs on **5 days** in a week = **+{b5} pts**; on **all 7 days** = **+{b7} pts**. "
            f"Max {cap} hrs count per day.")

    base = budget(d, p); stress = budget(d, p, hu, tu, bu)
    out = pd.DataFrame({"Tasks": base.tasks, "Base pts": base.base_pts, "Bonus pts": base.bonus_pts,
                        "Total pts": base.total_pts, "CPT (baseline)": base.CPT, "CPT (stress)": stress.CPT})
    out.index = out.index.astype(str)
    st.subheader("Budget summary: CPT impact")
    st.dataframe(out.style.format({"Tasks": "{:,.0f}", "Base pts": "{:,.0f}", "Bonus pts": "{:,.0f}", "Total pts": "{:,.0f}",
                                   "CPT (baseline)": "{:.3f}", "CPT (stress)": "{:.3f}"}), use_container_width=True)
    ok = max(base.CPT.max(), stress.CPT.max()) < 0.9
    (st.success if ok else st.error)(f"Worst-month CPT: baseline {base.CPT.max():.3f}, stress {stress.CPT.max():.3f} (limit 0.90)")
    f = px.bar(out.reset_index().melt("month", ["CPT (baseline)", "CPT (stress)"]), x="month", y="value", color="variable", barmode="group")
    f.add_hline(y=0.9, line_dash="dash", line_color="red"); f.update_layout(yaxis_title="CPT (Rs)", xaxis_title="")
    st.plotly_chart(f, use_container_width=True)

# ---------- Part 2 ----------
with tab2:
    st.subheader("Partner Quality Score (0-100)")
    cfg = {}
    cols = st.columns(4)
    for i, (k, (w, bad, good)) in enumerate(DEFAULT_Q.items()):
        cfg[k] = (cols[i % 4].number_input(f"Weight: {LABELS[k]}", 0, 100, w, key=f"w{k}"), bad, good)
    thr = st.slider("Retraining threshold (score below)", 40, 90, 70)
    mt = st.slider("Min tasks for a reliable score", 1, 30, 10)
    s = quality_score(q, cfg, thr, mt)
    c = s.bucket.value_counts()
    a, b, c_ = st.columns(3)
    a.metric("Partners scored", f"{len(s):,}"); b.metric("Retraining bucket", f"{(s.bucket.str.startswith('Retrain')).sum():,}")
    c_.metric("Share of fleet", f"{s.bucket.str.startswith('Retrain').mean():.1%}")
    st.plotly_chart(px.histogram(s, x="score", nbins=50, color="bucket"), use_container_width=True)
    st.markdown("**Lowest-scoring partners**")
    st.dataframe(s.sort_values("score").head(50)[["pid", "tasks", "score", "bucket"] + list(DEFAULT_Q)].round(2), use_container_width=True)
    st.markdown("""**Escalation plan if a partner is in the retraining bucket again**
| Times flagged | Action |
|---|---|
| 1st | Short refresher module + in-app tips on their weakest metrics; 2-week watch |
| 2nd | Mandatory classroom/video retraining + buddy ride-along; **points paused until completed** |
| 3rd | Final warning, 1:1 call with city ops, reduced order allocation priority for 2 weeks |
| 4th | Temporary deactivation (7 days), re-onboarding required; permanent exit if no improvement |
""")
    st.download_button("Download scored partners (CSV)", s.to_csv(index=False), "partner_scores.csv")

# ---------- Insights ----------
with tab3:
    st.subheader("What the data says")
    dow = d.groupby("dow").agg(hours=("hours", "mean"), tasks=("tasks", "mean"), partner_days=("pid", "size")).reset_index()
    dow["day"] = dow.dow.map(dict(enumerate(DAYS)))
    st.plotly_chart(px.bar(dow, x="day", y="partner_days", title="Partner-days online by weekday"), use_container_width=True)
    d2 = d.assign(bucket=pd.cut(d.hours.clip(upper=16), [0, 2, 4, 6, 8, 10, 12, 14, 16]).astype(str))
    t = d2.groupby("bucket").tasks.mean().reset_index()
    st.plotly_chart(px.bar(t, x="bucket", y="tasks", title="Avg tasks vs hours online: returns flatten after ~8-10 hrs"), use_container_width=True)

# ---------- Summary ----------
with tab0:
    st.markdown("""
### Approach in one page
**Part 1.** Points = hours online x a weekday rate (higher on Sun/Mon, then Fri/Sat, then Tue-Thu, mirroring demand), plus a flat weekly bonus for showing up on most days. Four numbers to remember. Budget is checked against the 0.9 CPT cap for every month, including a stress test where partners respond by working more.

**Part 2.** Eight partner metrics are converted to 0-100 sub-scores, weighted (rating, partner-controllable failures such as non-delivery and cancellation weigh most), and combined into one Partner Quality Score. Partners below 70 go to retraining, with an escalating plan for repeat offenders.

Use the tabs above; sidebar levers re-compute everything live.
""")
