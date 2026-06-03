"""
Q1 Scheme - East: Dealer Status Dashboard
Mobile-friendly Streamlit app showing where each dealer stands on the Q1 FY26
volume scheme. Data is read from data/transactions.csv.
"""
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Scheme constants (East region)
# ----------------------------------------------------------------------------
REGION = "East"
POINTS_PER_MT = 50          # base points earned per MT
GIFT_PER_POINT = 12         # gift value (INR) per point
EB_MULT = 1.25              # early-bird multiplier (+25%)
MIN_MT = 12                 # minimum total MT to qualify for any points
EB_DATE = date(2026, 5, 20)  # early-bird cutoff: billings on/before this date
TIERS = [12, 24, 36, 48, 60, 80, 100]  # reference milestones (MT)

DATA_PATH = Path(__file__).parent / "data" / "transactions.csv"

st.set_page_config(
    page_title="Q1 Scheme – East | Dealer Status",
    page_icon="📊",
    layout="centered",
)


# ----------------------------------------------------------------------------
# Data loading & per-dealer calculation
# ----------------------------------------------------------------------------
@st.cache_data
def load_transactions(mtime: float) -> pd.DataFrame:
    """Load and normalize the transactions CSV. `mtime` busts the cache when
    the file changes on disk."""
    df = pd.read_csv(DATA_PATH, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Normalize text columns
    for col in ["Zone", "State", "Distributor", "Dealer"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Parse dates. Year-first strings (ISO, e.g. 2026-05-10) are parsed as-is;
    # everything else is treated as day-first (Indian DD-MM-YYYY, e.g. 10-05-2026).
    raw = df["Date"].fillna("").astype(str).str.strip()
    iso_mask = raw.str.match(r"^\d{4}[-/.]")
    parsed = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    parsed[iso_mask] = pd.to_datetime(
        raw[iso_mask], errors="coerce", dayfirst=False
    )
    parsed[~iso_mask] = pd.to_datetime(
        raw[~iso_mask], errors="coerce", dayfirst=True
    )
    df["Date"] = parsed

    # Coerce MT to numeric
    df["MT"] = pd.to_numeric(df["MT"], errors="coerce")

    # Drop rows with no dealer / no valid MT
    df = df[(df["Dealer"] != "") & df["MT"].notna()].copy()
    return df


def _dealer_points(v_eb: float, v_after: float) -> tuple[float, bool, bool]:
    """Return (points, qualified, early_bird_applied) for one dealer."""
    v_total = v_eb + v_after
    qualified = v_total >= MIN_MT
    eb_applied = v_eb >= MIN_MT
    eb_points = v_eb * POINTS_PER_MT * (EB_MULT if eb_applied else 1.0)
    after_points = v_after * POINTS_PER_MT
    points = (eb_points + after_points) if qualified else 0.0
    return points, qualified, eb_applied


@st.cache_data
def aggregate_dealers(mtime: float) -> pd.DataFrame:
    """Roll transactions up to one row per dealer with scheme metrics."""
    df = load_transactions(mtime)
    eb_cutoff = pd.Timestamp(EB_DATE)

    rows = []
    keys = ["Zone", "State", "Distributor", "Dealer"]
    for key_vals, g in df.groupby(keys, dropna=False):
        v_eb = g.loc[g["Date"] <= eb_cutoff, "MT"].sum()
        v_after = g.loc[g["Date"] > eb_cutoff, "MT"].sum()
        # billings with an unparseable date count toward total (after-bucket)
        v_nodate = g.loc[g["Date"].isna(), "MT"].sum()
        v_after += v_nodate
        v_total = v_eb + v_after

        points, qualified, eb_applied = _dealer_points(v_eb, v_after)
        rows.append(
            {
                "Zone": key_vals[0],
                "State": key_vals[1],
                "Distributor": key_vals[2],
                "Dealer": key_vals[3],
                "MT (≤20 May)": round(v_eb, 2),
                "MT (after)": round(v_after, 2),
                "Total MT": round(v_total, 2),
                "Points": round(points, 0),
                "Gift Value ₹": round(points * GIFT_PER_POINT, 0),
                "Qualified": qualified,
                "Early Bird": eb_applied and qualified,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("Total MT", ascending=False).reset_index(drop=True)
    return out


def next_milestone(total_mt: float) -> tuple[int | None, float]:
    """Return (next tier MT, MT remaining) or (None, 0) if at/above top tier."""
    for t in TIERS:
        if total_mt < t:
            return t, t - total_mt
    return None, 0.0


def inr(n: float) -> str:
    """Format a number in the Indian comma style (e.g. 1,23,456)."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-" if n < 0 else "") + s


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("📊 Q1 Scheme – East")
st.caption(
    f"Dealer qualifying status · {POINTS_PER_MT} pts/MT · ₹{GIFT_PER_POINT}/pt · "
    f"+25% early-bird on volume billed by {EB_DATE.strftime('%d %b %Y')} "
    f"(min {MIN_MT} MT)"
)

if not DATA_PATH.exists():
    st.error("No data file found at data/transactions.csv.")
    st.stop()

mtime = DATA_PATH.stat().st_mtime
dealers = aggregate_dealers(mtime)
last_updated = datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
st.caption(f"Data as of {last_updated}")

if dealers.empty:
    st.info("No dealer data yet. Add billings to data/transactions.csv.")
    st.stop()


# ----------------------------------------------------------------------------
# Cascading filters: Zone -> State -> Distributor -> Dealer
# ----------------------------------------------------------------------------
def pick(label: str, frame: pd.DataFrame, col: str) -> pd.DataFrame:
    options = ["All"] + sorted(frame[col].unique().tolist())
    choice = st.selectbox(label, options, key=f"f_{col}")
    return frame if choice == "All" else frame[frame[col] == choice]

st.subheader("Find a dealer")
f1, f2 = st.columns(2)
with f1:
    scope = pick("Zone", dealers, "Zone")
with f2:
    scope = pick("State", scope, "State")
f3, f4 = st.columns(2)
with f3:
    scope = pick("Distributor", scope, "Distributor")
with f4:
    scope = pick("Dealer", scope, "Dealer")

st.divider()


# ----------------------------------------------------------------------------
# Detail view (single dealer) vs Overview (multiple dealers)
# ----------------------------------------------------------------------------
def status_badge(row) -> str:
    if not row["Qualified"]:
        return "🔴 Not yet qualified"
    if row["Early Bird"]:
        return "🟢 Qualified · ⚡ Early-bird bonus applied"
    return "🟡 Qualified (no early-bird bonus)"


if len(scope) == 1:
    row = scope.iloc[0]
    st.subheader(f"🏪 {row['Dealer']}")
    st.caption(f"{row['Distributor']} · {row['State']} · {row['Zone']}")
    st.markdown(f"**{status_badge(row)}**")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total MT", f"{row['Total MT']:g}")
    c2.metric("Points", inr(row["Points"]))
    c3.metric("Gift Value", f"₹{inr(row['Gift Value ₹'])}")

    if not row["Qualified"]:
        need = MIN_MT - row["Total MT"]
        st.warning(
            f"Needs **{need:g} more MT** to reach the {MIN_MT} MT qualifying minimum."
        )
    else:
        tier, remaining = next_milestone(row["Total MT"])
        if tier is not None:
            mult = EB_MULT if row["Early Bird"] else 1.0
            tier_pts = tier * POINTS_PER_MT * mult
            tier_gift = tier_pts * GIFT_PER_POINT
            st.progress(min(row["Total MT"] / tier, 1.0))
            st.info(
                f"**{remaining:g} MT** more to reach the **{tier} MT** milestone → "
                f"~{inr(tier_pts)} pts (₹{inr(tier_gift)})"
            )
        else:
            st.success("🏆 Top milestone (100 MT) reached!")

    if not row["Early Bird"] and row["Qualified"]:
        st.caption(
            f"💡 Tip: at least {MIN_MT} MT must be billed by "
            f"{EB_DATE.strftime('%d %b')} to unlock the +25% early-bird bonus on "
            "that volume."
        )

    # Billing breakdown for this dealer
    txn = load_transactions(mtime)
    mask = (
        (txn["Zone"] == row["Zone"])
        & (txn["State"] == row["State"])
        & (txn["Distributor"] == row["Distributor"])
        & (txn["Dealer"] == row["Dealer"])
    )
    dt = txn[mask].copy().sort_values("Date")
    dt["Window"] = dt["Date"].apply(
        lambda d: "≤ 20 May (early bird)"
        if pd.notna(d) and d <= pd.Timestamp(EB_DATE)
        else "after 20 May"
    )
    dt["Date"] = dt["Date"].dt.strftime("%d %b %Y").fillna("—")
    with st.expander(f"Billing history ({len(dt)} entries)"):
        st.dataframe(
            dt[["Date", "MT", "Window"]],
            hide_index=True,
            width='stretch',
        )

else:
    # Overview for the current filter scope
    n = len(scope)
    qualified = int(scope["Qualified"].sum())
    eb = int(scope["Early Bird"].sum())
    tot_mt = scope["Total MT"].sum()
    tot_pts = scope["Points"].sum()
    tot_gift = scope["Gift Value ₹"].sum()

    st.subheader(f"Overview · {n} dealers")
    c1, c2, c3 = st.columns(3)
    c1.metric("Qualified", f"{qualified}/{n}")
    c2.metric("Early-bird", f"{eb}/{n}")
    c3.metric("Total MT", f"{tot_mt:g}")
    c4, c5 = st.columns(2)
    c4.metric("Total Points", inr(tot_pts))
    c5.metric("Total Gift Value", f"₹{inr(tot_gift)}")

    st.divider()
    st.subheader("Dealers")

    def status_icon(r) -> str:
        if not r["Qualified"]:
            return "🔴"
        return "🟢⚡" if r["Early Bird"] else "🟡"

    show = scope.copy()
    show.insert(0, "Status", show.apply(status_icon, axis=1))
    show["Gift Value ₹"] = show["Gift Value ₹"].apply(lambda x: f"₹{inr(x)}")
    show["Points"] = show["Points"].apply(inr)
    st.dataframe(
        show[
            [
                "Status",
                "Dealer",
                "Distributor",
                "Total MT",
                "Points",
                "Gift Value ₹",
            ]
        ],
        hide_index=True,
        width='stretch',
    )
    st.caption("🟢⚡ qualified + early-bird · 🟡 qualified · 🔴 not yet qualified")
    st.caption("Pick a Dealer above to see full details and billing history.")
