"""Shared logic for the notebook and the Streamlit app."""
import numpy as np, pandas as pd

DATA = "partner_data.xlsx"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ---------------- Part 1 ----------------
def load_supply(path=DATA):
    d = pd.read_excel(path, sheet_name="Sheet1")
    d.columns = ["pid", "date", "hours", "tasks"]
    d["month"] = d.date.dt.to_period("M")
    d["dow"] = d.date.dt.dayofweek                      # Mon=0
    d["week"] = d.date.dt.to_period("W-SUN")            # Mon-Sun weeks
    return d

DEFAULT_RATES = {"Sun/Mon": 1.5, "Fri/Sat": 1.0, "Tue-Thu": 0.5}
DEFAULT_PARAMS = dict(rates=DEFAULT_RATES, cap=12, active_min=4,
                      bonus5=10, bonus7=25)

def rate_map(r):
    return {0: r["Sun/Mon"], 6: r["Sun/Mon"], 4: r["Fri/Sat"], 5: r["Fri/Sat"],
            1: r["Tue-Thu"], 2: r["Tue-Thu"], 3: r["Tue-Thu"]}

def points(d, p=DEFAULT_PARAMS):
    """Returns (daily_df with base points, weekly_df with bonus)."""
    x = d.copy()
    x["base_pts"] = x.hours.clip(upper=p["cap"]) * x.dow.map(rate_map(p["rates"]))
    x["active"] = x.hours >= p["active_min"]
    wk = (x[x.active].groupby(["week", "pid"]).date.nunique()
          .rename("active_days").reset_index())
    wk["bonus"] = np.select([wk.active_days >= 7, wk.active_days >= 5],
                            [p["bonus7"], p["bonus5"]], 0)
    wk["month"] = wk.week.apply(lambda w: w.end_time.to_period("M"))  # paid in month the week ends
    return x, wk

def budget(d, p=DEFAULT_PARAMS, hours_uplift=0.0, task_uplift=0.0, bonus_uplift=0.0):
    x, wk = points(d, p)
    b = pd.DataFrame({
        "tasks": d.groupby("month").tasks.sum(),
        "hours": d.groupby("month").hours.sum(),
        "base_pts": x.groupby("month").base_pts.sum()})
    b["bonus_pts"] = wk.groupby("month").bonus.sum().reindex(b.index).fillna(0)
    b["base_pts"] *= (1 + hours_uplift)
    b["bonus_pts"] *= (1 + bonus_uplift)
    b["tasks"] *= (1 + task_uplift)
    b["total_pts"] = b.base_pts + b.bonus_pts
    b["CPT"] = b.total_pts / b.tasks
    return b

# ---------------- Part 2 ----------------
Q_COLS = ["pid", "tasks", "acc", "canc", "tnd", "pcanc", "ttime", "inter", "contact", "rating"]
# metric: (weight, bad anchor, good anchor)  -> score 0 at 'bad', 1 at 'good', linear in between
DEFAULT_Q = {
    "rating":   (25, 3.5, 5.0),
    "acc":      (15, 60, 100),
    "tnd_pct":  (15, 3, 0),
    "pcanc":    (15, 5, 0),
    "canc":     (10, 10, 0),
    "ttime":    (10, 70, 25),
    "inter":    (5, 70, 10),
    "contact":  (5, 40, 0),
}
LABELS = {"rating": "Customer rating", "acc": "Acceptance rate (%)", "tnd_pct": "Tasks not delivered (% of tasks)",
          "pcanc": "Partner-induced cancellation (%)", "canc": "Cancellation rate (%)",
          "ttime": "Task time (min)", "inter": "Support interaction rate (%)", "contact": "Customer contact rate (%)"}

def load_quality(path=DATA):
    s = pd.read_excel(path, sheet_name="Sheet2"); s.columns = Q_COLS
    s["tnd_pct"] = s.tnd / s.tasks * 100        # raw column is a COUNT (0-4), not a %
    return s

def quality_score(s, cfg=DEFAULT_Q, threshold=70, min_tasks=10, severe=60):
    s = s.copy(); tot = sum(v[0] for v in cfg.values())
    s["score"] = 0.0
    for k, (w, bad, good) in cfg.items():
        v = s[k].fillna(s[k].median())          # 46 partners have no rating -> median
        s[f"s_{k}"] = ((v - bad) / (good - bad)).clip(0, 1)
        s["score"] += s[f"s_{k}"] * w / tot * 100
    s["bucket"] = np.select(
        [(s.tasks >= min_tasks) & (s.score < threshold), (s.tasks < min_tasks) & (s.score < severe)],
        ["Retrain", "Retrain (severe, low volume)"], "OK")
    s.loc[(s.tasks < min_tasks) & (s.score >= severe) & (s.score < threshold), "bucket"] = "Watch (low volume)"
    return s
