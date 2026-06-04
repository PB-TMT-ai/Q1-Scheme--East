"""
Q1 Scheme - East: Dealer Status Dashboard
Mobile-friendly Streamlit app showing where each dealer stands on the Q1 FY26
volume scheme.

Data sources (data/):
  - may_transactions.csv : May billings, date-wise (Zone,State,Distributor,Dealer,Date,MT)
  - june_secondary.csv   : June month-to-date aggregate (Zone,State,Distributor,Dealer,MT)
  - gifts.csv            : scheme gift catalog per MT tier (admin-only display)
"""
import html
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

DATA_DIR = Path(__file__).parent / "data"
MAY_PATH = DATA_DIR / "may_transactions.csv"
JUNE_PATH = DATA_DIR / "june_secondary.csv"
GIFTS_PATH = DATA_DIR / "gifts.csv"

st.set_page_config(
    page_title="Q1 Scheme – East | Dealer Status",
    page_icon="📊",
    layout="centered",
)

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
NAVY = "#003C71"
ACCENT = "#F5A623"
GREEN = "#1E8E3E"
AMBER = "#F9A825"
RED = "#D93025"

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 760px; }}
      #MainMenu, footer {{ visibility: hidden; }}

      .hero {{
        background: linear-gradient(135deg, {NAVY} 0%, #0A5BA0 100%);
        color: #fff; border-radius: 16px; padding: 16px 18px; margin-bottom: 14px;
      }}
      .hero h1 {{ font-size: 1.35rem; margin: 0; font-weight: 800; letter-spacing:.2px; }}
      .hero .sub {{ font-size: .82rem; opacity: .92; margin-top: 4px; }}
      .hero .pill {{
        display:inline-block; background: rgba(255,255,255,.18); border-radius: 999px;
        padding: 2px 10px; font-size: .72rem; font-weight: 700; margin-top: 8px;
      }}

      .kpi-grid {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px; margin: 6px 0 4px;
      }}
      .kpi {{
        background:#fff; border-radius: 14px; padding: 13px 14px;
        box-shadow: 0 1px 5px rgba(16,24,40,.08); border-left: 4px solid {NAVY};
      }}
      .kpi .v {{ font-size: 1.45rem; font-weight: 800; color:{NAVY}; line-height: 1.05; }}
      .kpi .l {{ font-size: .70rem; color:#5f6b7a; text-transform: uppercase;
                 letter-spacing:.04em; margin-top: 5px; font-weight:600; }}
      .kpi.accent {{ border-left-color:{ACCENT}; }} .kpi.accent .v {{ color:#B9770E; }}
      .kpi.green  {{ border-left-color:{GREEN};  }} .kpi.green  .v {{ color:{GREEN}; }}

      .row {{
        display:flex; align-items:center; gap:10px; background:#fff; border-radius:12px;
        padding:10px 12px; margin-bottom:8px; box-shadow:0 1px 4px rgba(16,24,40,.07);
      }}
      .row .rank {{ font-weight:800; color:{NAVY}; width:26px; text-align:center; font-size:.95rem; }}
      .row .info {{ flex:1; min-width:0; }}
      .row .name {{ font-weight:700; font-size:.92rem; color:#1a2433; white-space:nowrap;
                    overflow:hidden; text-overflow:ellipsis; }}
      .row .sub {{ font-size:.72rem; color:#6b7686; white-space:nowrap; overflow:hidden;
                   text-overflow:ellipsis; }}
      .row .num {{ text-align:right; font-size:.88rem; font-weight:700; color:#1a2433; }}
      .row .num span {{ display:block; font-size:.70rem; font-weight:600; color:#6b7686; }}
      .dot {{ width:10px; height:10px; border-radius:50%; flex:0 0 10px; }}

      .badge {{ display:inline-block; border-radius:999px; padding:5px 12px; font-size:.8rem;
                font-weight:700; }}
      .b-green {{ background:#E6F4EA; color:{GREEN}; }}
      .b-amber {{ background:#FEF7E0; color:#9A6700; }}
      .b-red   {{ background:#FCE8E6; color:{RED}; }}

      .card {{ background:#fff; border-radius:16px; padding:16px 16px 6px;
               box-shadow:0 2px 8px rgba(16,24,40,.10); margin-bottom:12px; }}
      .card h2 {{ margin:0; font-size:1.15rem; color:{NAVY}; font-weight:800; }}
      .card .csub {{ font-size:.78rem; color:#6b7686; margin:2px 0 10px; }}

      .pbar {{ background:#EAEEF3; border-radius:999px; height:10px; margin:8px 0 4px; overflow:hidden; }}
      .pbar > div {{ height:100%; background:linear-gradient(90deg,{NAVY},#0A5BA0); border-radius:999px; }}
      .ptext {{ font-size:.76rem; color:#6b7686; }}

      .gift {{ background:#FFF8E7; border:1px solid #F4D58B; border-radius:12px;
               padding:10px 12px; margin:10px 0 2px; font-size:.86rem; color:#5a4a1a; }}
      .gift .gcost {{ display:block; margin-top:4px; font-size:.74rem; color:#8a6d2f; font-weight:700; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Data loading & per-dealer calculation
# ----------------------------------------------------------------------------
KEYS = ["Zone", "State", "Distributor", "Dealer"]


@st.cache_data
def load_may(mtime: float) -> pd.DataFrame:
    """May billings, date-wise."""
    df = pd.read_csv(MAY_PATH, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for col in KEYS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Year-first strings (ISO) parsed as-is; everything else as day-first (DD-MM-YYYY).
    raw = df["Date"].fillna("").astype(str).str.strip()
    iso_mask = raw.str.match(r"^\d{4}[-/.]")
    parsed = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    parsed[iso_mask] = pd.to_datetime(raw[iso_mask], errors="coerce", dayfirst=False)
    parsed[~iso_mask] = pd.to_datetime(raw[~iso_mask], errors="coerce", dayfirst=True)
    df["Date"] = parsed
    df["MT"] = pd.to_numeric(df["MT"], errors="coerce")
    return df[(df["Dealer"] != "") & df["MT"].notna()].copy()


@st.cache_data
def load_june(mtime: float) -> pd.DataFrame:
    """June month-to-date aggregate (one row per dealer, no dates)."""
    if not JUNE_PATH.exists():
        return pd.DataFrame(columns=KEYS + ["MT"])
    df = pd.read_csv(JUNE_PATH, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for col in KEYS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["MT"] = pd.to_numeric(df["MT"], errors="coerce")
    return df[(df["Dealer"] != "") & df["MT"].notna()].copy()


@st.cache_data
def load_gifts(mtime: float) -> pd.DataFrame:
    """Gift catalog per MT tier."""
    g = pd.read_csv(GIFTS_PATH)
    g.columns = [c.strip() for c in g.columns]
    return g.sort_values("MT").reset_index(drop=True)


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
    """Combine May (date-wise) + June (aggregate) into one row per dealer.

    Early-bird volume = May billings on/before 20 May. Everything else
    (May after 20 May, undated May, and all June) is 'after'."""
    may = load_may(mtime)
    june = load_june(mtime)
    eb_cutoff = pd.Timestamp(EB_DATE)

    eb = (may[may["Date"] <= eb_cutoff].groupby(KEYS)["MT"].sum())
    after_may = (may[~(may["Date"] <= eb_cutoff)].groupby(KEYS)["MT"].sum())
    after_jun = june.groupby(KEYS)["MT"].sum() if not june.empty else pd.Series(dtype=float)

    idx = eb.index.union(after_may.index).union(after_jun.index)
    eb = eb.reindex(idx, fill_value=0.0)
    after = after_may.reindex(idx, fill_value=0.0).add(
        after_jun.reindex(idx, fill_value=0.0), fill_value=0.0)

    rows = []
    for key_vals, v_eb, v_after in zip(idx, eb.values, after.values):
        points, qualified, eb_applied = _dealer_points(v_eb, v_after)
        rows.append(
            {
                "Zone": key_vals[0], "State": key_vals[1],
                "Distributor": key_vals[2], "Dealer": key_vals[3],
                "MT_eb": round(v_eb, 2), "MT_after": round(v_after, 2),
                "Total MT": round(v_eb + v_after, 2),
                "Points": round(points, 0),
                "Gift Value": round(points * GIFT_PER_POINT, 0),
                "Qualified": qualified,
                "Early Bird": eb_applied and qualified,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("Total MT", ascending=False).reset_index(drop=True)
    return out


def gift_for(total_mt: float, gifts: pd.DataFrame):
    """Highest gift tier reached. Returns a row (Series) or None."""
    elig = gifts[gifts["MT"] <= total_mt]
    return elig.iloc[-1] if not elig.empty else None


def next_gift(total_mt: float, gifts: pd.DataFrame):
    """Next gift tier not yet reached. Returns (row, mt_needed) or (None, 0)."""
    nxt = gifts[gifts["MT"] > total_mt]
    if nxt.empty:
        return None, 0.0
    row = nxt.iloc[0]
    return row, row["MT"] - total_mt


def next_milestone(total_mt: float) -> tuple[int | None, float]:
    for t in TIERS:
        if total_mt < t:
            return t, t - total_mt
    return None, 0.0


def inr(n: float) -> str:
    """Format a number in the Indian comma style (e.g. 1,23,456)."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        last3, rest, parts = s[-3:], s[:-3], []
        while len(rest) > 2:
            parts.insert(0, rest[-2:]); rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-" if n < 0 else "") + s


def mt_fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def status_of(r) -> tuple[str, str]:
    """Return (color, label)."""
    if not r["Qualified"]:
        if r["Total MT"] >= 8:
            return AMBER, "Almost there"
        return RED, "Not qualified"
    if r["Early Bird"]:
        return GREEN, "Qualified · Early bird"
    return NAVY, "Qualified"


# ----------------------------------------------------------------------------
# Admin gate — costing (₹ gift value) is hidden until an admin unlocks it.
# ----------------------------------------------------------------------------
def _admin_password() -> str:
    """Admin password from Streamlit secrets, with a fallback default."""
    try:
        return str(st.secrets["admin_password"])
    except Exception:
        return "east-admin-2026"


def admin_gate() -> bool:
    """Sidebar login. Returns True when admin mode is active."""
    st.session_state.setdefault("admin", False)
    with st.sidebar:
        st.markdown("### 🔒 Admin")
        if st.session_state.admin:
            st.success("Admin mode — costing visible")
            if st.button("Log out"):
                st.session_state.admin = False
                st.rerun()
        else:
            st.caption("Sales team: leave this closed. Admins unlock gift-value / costing.")
            pw = st.text_input("Admin password", type="password", key="pw")
            if st.button("Unlock"):
                if pw and pw == _admin_password():
                    st.session_state.admin = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
    return st.session_state.admin


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
if not MAY_PATH.exists():
    st.error("No data file found at data/may_transactions.csv.")
    st.stop()

# Cache key reflects the newest of the data files so edits refresh the app.
mtime = max(p.stat().st_mtime for p in (MAY_PATH, JUNE_PATH, GIFTS_PATH) if p.exists())
dealers = aggregate_dealers(mtime)
gifts = load_gifts(mtime)
last_updated = datetime.fromtimestamp(mtime).strftime("%d %b %Y")
admin = admin_gate()

rate = f"₹{GIFT_PER_POINT}/pt · " if admin else ""
st.markdown(
    f"""
    <div class="hero">
      <h1>⚡ Q1 Scheme · East</h1>
      <div class="sub">{POINTS_PER_MT} pts/MT · {rate}+25% early-bird on volume
      by {EB_DATE.strftime('%d %b %Y')} (min {MIN_MT} MT) · qualify at {MIN_MT} MT</div>
      <span class="pill">Dealer qualifying status · updated {last_updated}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if dealers.empty:
    st.info("No dealer data yet. Add billings to data/transactions.csv.")
    st.stop()


# ----------------------------------------------------------------------------
# Scope filters (State -> Distributor -> Dealer; Zone is always East)
# ----------------------------------------------------------------------------
def pick(label, frame, col):
    opts = ["All"] + sorted(frame[col].unique().tolist())
    choice = st.selectbox(label, opts, key=f"f_{col}")
    return frame if choice == "All" else frame[frame[col] == choice]

with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        scope = pick("State", dealers, "State")
    with c2:
        scope = pick("Distributor", scope, "Distributor")
    with c3:
        scope = pick("Dealer", scope, "Dealer")


# ----------------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------------
def kpi_band(df: pd.DataFrame, admin: bool):
    n = len(df)
    qual = int(df["Qualified"].sum())
    eb = int(df["Early Bird"].sum())
    push = int(((df["Total MT"] >= 8) & (df["Total MT"] < MIN_MT)).sum())
    cells = [
        ("", "Active dealers", str(n)),
        ("", "Total MT", mt_fmt(df["Total MT"].sum())),
        ("", "MT by 20-May", mt_fmt(df["MT_eb"].sum())),
        ("green", "Qualified ≥12 MT", str(qual)),
        ("green", "Early bird", str(eb)),
        ("accent", "Push list (8–12)", str(push)),
        ("", "Total points", inr(df["Points"].sum())),
    ]
    if admin:
        cells.append(("accent", "Gift value", "₹" + inr(df["Gift Value"].sum())))
    html_cells = "".join(
        f'<div class="kpi {cls}"><div class="v">{v}</div><div class="l">{l}</div></div>'
        for cls, l, v in cells
    )
    st.markdown(f'<div class="kpi-grid">{html_cells}</div>', unsafe_allow_html=True)


def dealer_rows(df: pd.DataFrame, admin: bool, ranked=True, note_mode=None) -> str:
    out = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        color, _ = status_of(r)
        rank = f'<div class="rank">{i}</div>' if ranked else ""
        if note_mode == "push":
            need = MIN_MT - r["Total MT"]
            right = (f'{mt_fmt(r["Total MT"])} MT<span>needs {mt_fmt(need)} MT</span>')
        else:
            gift = f' · ₹{inr(r["Gift Value"])}' if admin else ""
            right = (f'{mt_fmt(r["Total MT"])} MT'
                     f'<span>{inr(r["Points"])} pts{gift}</span>')
        out.append(
            f'<div class="row">{rank}'
            f'<div class="info"><div class="name">{html.escape(r["Dealer"])}</div>'
            f'<div class="sub">{html.escape(r["Distributor"])} · {html.escape(r["State"])}</div></div>'
            f'<div class="num">{right}</div>'
            f'<div class="dot" style="background:{color}"></div></div>'
        )
    return "".join(out)


def dealer_detail(r, admin: bool):
    color, label = status_of(r)
    bcls = {GREEN: "b-green", AMBER: "b-amber", RED: "b-red", NAVY: "b-amber"}[color]
    st.markdown(
        f'<div class="card"><h2>{html.escape(r["Dealer"])}</h2>'
        f'<div class="csub">{html.escape(r["Distributor"])} · {html.escape(r["State"])} · {r["Zone"]}</div>'
        f'<span class="badge {bcls}">{label}</span></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3 if admin else 2)
    cols[0].metric("Total MT", mt_fmt(r["Total MT"]))
    cols[1].metric("Points", inr(r["Points"]))
    if admin:
        cols[2].metric("Gift Value", "₹" + inr(r["Gift Value"]))

    if not r["Qualified"]:
        need = MIN_MT - r["Total MT"]
        st.warning(f"Needs **{mt_fmt(need)} more MT** to reach the {MIN_MT} MT qualifying minimum.")
    else:
        tier, remaining = next_milestone(r["Total MT"])
        if tier is not None:
            pct = min(r["Total MT"] / tier, 1.0) * 100
            mult = EB_MULT if r["Early Bird"] else 1.0
            tier_pts = tier * POINTS_PER_MT * mult
            gift_note = f' (₹{inr(tier_pts * GIFT_PER_POINT)})' if admin else ""
            st.markdown(
                f'<div class="pbar"><div style="width:{pct:.0f}%"></div></div>'
                f'<div class="ptext"><b>{mt_fmt(remaining)} MT</b> more to the '
                f'<b>{tier} MT</b> milestone → ~{inr(tier_pts)} pts{gift_note}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.success("🏆 Top milestone (100 MT) reached!")

    # early-bird note
    if r["Early Bird"]:
        st.caption(f"⚡ Early-bird secured: {mt_fmt(r['MT_eb'])} MT billed by {EB_DATE.strftime('%d %b')}.")
    elif r["Qualified"]:
        st.caption(f"No early-bird bonus (only {mt_fmt(r['MT_eb'])} MT billed by {EB_DATE.strftime('%d %b')}; needs ≥{MIN_MT} MT).")

    # qualified gift — admin only
    if admin and r["Qualified"]:
        g = gift_for(r["Total MT"], gifts)
        if g is not None:
            alt = (f' <i>or</i> {html.escape(str(g["AltGift"]))}'
                   if str(g.get("AltGift", "")).strip() else "")
            st.markdown(
                f'<div class="gift">🎁 <b>Qualified gift</b> · {int(g["MT"])} MT tier<br>'
                f'{html.escape(str(g["Gift"]))}{alt}'
                f'<span class="gcost">gift cost ₹{inr(g["Cost"])}</span></div>',
                unsafe_allow_html=True,
            )
        ng, need = next_gift(r["Total MT"], gifts)
        if ng is not None:
            st.caption(f"➕ {mt_fmt(need)} MT more unlocks the {int(ng['MT'])} MT gift: {ng['Gift']}.")

    # billing history (May date-wise + June month-to-date)
    may = load_may(mtime)
    jun = load_june(mtime)
    sel = lambda d: ((d["Distributor"] == r["Distributor"]) & (d["Dealer"] == r["Dealer"])
                     & (d["State"] == r["State"]))
    hist = []
    for _, x in may[sel(may)].sort_values("Date").iterrows():
        win = ("≤ 20 May (early bird)" if pd.notna(x["Date"]) and x["Date"] <= pd.Timestamp(EB_DATE)
               else "after 20 May")
        hist.append({"Date": x["Date"].strftime("%d %b %Y") if pd.notna(x["Date"]) else "—",
                     "MT": x["MT"], "Window": win})
    jmt = jun[sel(jun)]["MT"].sum() if not jun.empty else 0.0
    if jmt > 0:
        hist.append({"Date": "June (month-to-date)", "MT": round(jmt, 2), "Window": "after 20 May"})
    hist = pd.DataFrame(hist)
    with st.expander(f"Billing history ({len(hist)} entries)"):
        st.dataframe(hist, hide_index=True, width="stretch")


# ----------------------------------------------------------------------------
# Body: dealer detail OR overview
# ----------------------------------------------------------------------------
if len(scope) == 1:
    dealer_detail(scope.iloc[0], admin)
else:
    kpi_band(scope, admin)
    tab_lead, tab_push, tab_all = st.tabs(["🏆 Leaderboard", "🎯 Push list", "📋 All dealers"])

    with tab_lead:
        top = scope.sort_values(["Points", "Total MT"], ascending=False).head(15)
        st.markdown(dealer_rows(top, admin, ranked=True), unsafe_allow_html=True)
        st.caption("Top 15 by points. 🟢 early bird · 🔵 qualified · 🟠 almost (8–12 MT) · 🔴 not qualified")

    with tab_push:
        push = scope[(scope["Total MT"] >= 8) & (scope["Total MT"] < MIN_MT)] \
            .sort_values("Total MT", ascending=False)
        if push.empty:
            st.info("No dealers in the 8–12 MT push range for this scope. 🎉")
        else:
            st.markdown(f"**{len(push)} dealers** are 8–12 MT — one push gets them qualified:")
            st.markdown(dealer_rows(push, admin, ranked=False, note_mode="push"), unsafe_allow_html=True)

    with tab_all:
        show = scope.copy()
        show["Status"] = show.apply(lambda r: status_of(r)[1], axis=1)
        show["Points"] = show["Points"].apply(inr)
        cols = ["Dealer", "Distributor", "State", "Total MT", "Points"]
        if admin:
            show["Qualified Gift"] = show["Total MT"].apply(
                lambda t: (gift_for(t, gifts)["Gift"] if gift_for(t, gifts) is not None else "—"))
            show["Gift Value"] = show["Gift Value"].apply(lambda x: "₹" + inr(x))
            cols += ["Qualified Gift", "Gift Value"]
        cols.append("Status")
        st.dataframe(show[cols], hide_index=True, width="stretch")
        st.caption("Tip: pick a Dealer in the filter above for full details and billing history.")
