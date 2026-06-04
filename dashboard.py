"""Scheme-driven dashboard renderer. `render(scheme)` draws the whole mobile UI for any
zone-scheme defined in schemes.py."""
import base64
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))  # report dates in India time


def _ordinal(n: int) -> str:
    suf = "th" if 11 <= (n % 100) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n:02d}{suf}"


def _till_date() -> str:
    """Yesterday (T-1) in IST, e.g. '03rd June 2026'."""
    y = (datetime.now(IST) - timedelta(days=1)).date()
    return f"{_ordinal(y.day)} {y.strftime('%B %Y')}"

import pandas as pd
import streamlit as st

from schemes import Scheme

KEYS = ["Zone", "State", "Distributor", "Dealer"]
NAVY, ACCENT, GREEN, AMBER, RED = "#003C71", "#F5A623", "#1E8E3E", "#F9A825", "#D93025"
ASSETS = Path(__file__).parent / "assets"
# First match wins: a real PNG/JPG logo takes priority over the SVG placeholder.
LOGO_CANDIDATES = ("jsw_logo.png", "jsw_logo.jpg", "jsw_logo.jpeg", "jsw_logo.svg")
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}


def _logo_img() -> str:
    """Return an <img> tag embedding the first logo file found in assets/, or ''."""
    for name in LOGO_CANDIDATES:
        p = ASSETS / name
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode()
            return f'<img class="logo" src="data:{_MIME[p.suffix.lower()]};base64,{b64}" alt="JSW One"/>'
    return ""


# ----------------------------------------------------------------------------
# Data loading (cached; keyed by file paths + newest mtime)
# ----------------------------------------------------------------------------
@st.cache_data
def _load_dated(paths: tuple, mtime: float, eb_iso: str | None) -> pd.DataFrame:
    frames = []
    for p in paths:
        if not Path(p).exists():
            continue
        df = pd.read_csv(p, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        for col in KEYS:
            df[col] = df[col].fillna("").astype(str).str.strip()
        raw = df["Date"].fillna("").astype(str).str.strip()
        iso = raw.str.match(r"^\d{4}[-/.]")
        d = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(raw[iso], errors="coerce", dayfirst=False)
        d[~iso] = pd.to_datetime(raw[~iso], errors="coerce", dayfirst=True)
        df["Date"] = d
        df["MT"] = pd.to_numeric(df["MT"], errors="coerce")
        frames.append(df[(df["Dealer"] != "") & df["MT"].notna()])
    if not frames:
        return pd.DataFrame(columns=KEYS + ["Date", "MT"])
    return pd.concat(frames, ignore_index=True)


@st.cache_data
def _load_agg(paths: tuple, mtime: float) -> pd.DataFrame:
    frames = []
    for p in paths:
        if not Path(p).exists():
            continue
        df = pd.read_csv(p, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        for col in KEYS:
            df[col] = df[col].fillna("").astype(str).str.strip()
        df["MT"] = pd.to_numeric(df["MT"], errors="coerce")
        frames.append(df[(df["Dealer"] != "") & df["MT"].notna()][KEYS + ["MT"]])
    if not frames:
        return pd.DataFrame(columns=KEYS + ["MT"])
    return pd.concat(frames, ignore_index=True)


@st.cache_data
def _load_gifts(path: str, mtime: float) -> pd.DataFrame:
    g = pd.read_csv(path)
    g.columns = [c.strip() for c in g.columns]
    return g.sort_values("MT").reset_index(drop=True)


def _aggregate(scheme: Scheme, dated: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    """One row per dealer. Early-bird volume = dated billings on/before the cutoff
    (only when the scheme has early bird); everything else is 'after'."""
    eb_cut = pd.Timestamp(scheme.eb_date) if scheme.early_bird and scheme.eb_date else None

    if eb_cut is not None and not dated.empty:
        eb = dated[dated["Date"] <= eb_cut].groupby(KEYS)["MT"].sum()
        after_d = dated[~(dated["Date"] <= eb_cut)].groupby(KEYS)["MT"].sum()
    else:
        eb = pd.Series(dtype=float)
        after_d = dated.groupby(KEYS)["MT"].sum() if not dated.empty else pd.Series(dtype=float)
    after_a = agg.groupby(KEYS)["MT"].sum() if not agg.empty else pd.Series(dtype=float)

    idx = eb.index.union(after_d.index).union(after_a.index)
    eb = eb.reindex(idx, fill_value=0.0)
    after = (after_d.reindex(idx, fill_value=0.0)
             .add(after_a.reindex(idx, fill_value=0.0), fill_value=0.0))

    rows = []
    for key_vals, v_eb, v_after in zip(idx, eb.values, after.values):
        total = v_eb + v_after
        qualified = total >= scheme.min_mt
        if not qualified:
            points, eb_applied = 0.0, False
        elif scheme.early_bird:
            eb_applied = v_eb >= scheme.min_mt
            points = (v_eb * scheme.points_per_mt * (scheme.eb_mult if eb_applied else 1.0)
                      + v_after * scheme.points_per_mt)
        else:
            eb_applied = False
            points = total * scheme.points_per_mt
        rows.append({
            "Zone": key_vals[0], "State": key_vals[1],
            "Distributor": key_vals[2], "Dealer": key_vals[3],
            "MT_eb": round(v_eb, 2), "MT_after": round(v_after, 2),
            "Total MT": round(total, 2), "Points": round(points, 0),
            "Gift Value": round(points * scheme.gift_per_point, 0),
            "Qualified": qualified, "Early Bird": eb_applied and qualified,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("Total MT", ascending=False).reset_index(drop=True)
    return out


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def inr(n: float) -> str:
    n = int(round(n)); s = str(abs(n))
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


def status_of(scheme: Scheme, r) -> tuple[str, str]:
    if not r["Qualified"]:
        return (AMBER, "Almost there") if r["Total MT"] >= 8 else (RED, "Not qualified")
    if scheme.early_bird and r["Early Bird"]:
        return GREEN, "Qualified · Early bird"
    return NAVY, "Qualified"


def gift_for(total_mt, gifts):
    elig = gifts[gifts["MT"] <= total_mt]
    return elig.iloc[-1] if not elig.empty else None


def next_gift(total_mt, gifts):
    nxt = gifts[gifts["MT"] > total_mt]
    return (nxt.iloc[0], nxt.iloc[0]["MT"] - total_mt) if not nxt.empty else (None, 0.0)


def _css():
    st.markdown(f"""
    <style>
      .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 760px; }}
      #MainMenu, footer {{ visibility: hidden; }}
      .hero {{ background: linear-gradient(135deg,{NAVY} 0%,#0A5BA0 100%); color:#fff;
               border-radius:16px; padding:16px 18px; margin-bottom:14px; }}
      .hero-row {{ display:flex; align-items:center; gap:12px; }}
      .hero-txt {{ min-width:0; }}
      .hero .logo {{ height:46px; width:auto; flex:0 0 auto; border-radius:8px;
                     box-shadow:0 1px 3px rgba(0,0,0,.18); }}
      .hero h1 {{ font-size:1.3rem; margin:0; font-weight:800; letter-spacing:.2px; }}
      .hero .sub {{ font-size:.82rem; opacity:.92; margin-top:4px; }}
      .hero .pill {{ display:inline-block; background:rgba(255,255,255,.18); border-radius:999px;
                     padding:2px 10px; font-size:.72rem; font-weight:700; margin-top:8px; }}
      .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
                   gap:10px; margin:6px 0 4px; }}
      .kpi {{ background:#fff; border-radius:14px; padding:13px 14px;
              box-shadow:0 1px 5px rgba(16,24,40,.08); border-left:4px solid {NAVY}; }}
      .kpi .v {{ font-size:1.45rem; font-weight:800; color:{NAVY}; line-height:1.05; }}
      .kpi .l {{ font-size:.70rem; color:#5f6b7a; text-transform:uppercase; letter-spacing:.04em;
                 margin-top:5px; font-weight:600; }}
      .kpi.accent {{ border-left-color:{ACCENT}; }} .kpi.accent .v {{ color:#B9770E; }}
      .kpi.green {{ border-left-color:{GREEN}; }} .kpi.green .v {{ color:{GREEN}; }}
      .row {{ display:flex; align-items:center; gap:10px; background:#fff; border-radius:12px;
              padding:10px 12px; margin-bottom:8px; box-shadow:0 1px 4px rgba(16,24,40,.07); }}
      .row .rank {{ font-weight:800; color:{NAVY}; width:26px; text-align:center; font-size:.95rem; }}
      .row .info {{ flex:1; min-width:0; }}
      .row .name {{ font-weight:700; font-size:.92rem; color:#1a2433; white-space:nowrap;
                    overflow:hidden; text-overflow:ellipsis; }}
      .row .sub {{ font-size:.72rem; color:#6b7686; white-space:nowrap; overflow:hidden;
                   text-overflow:ellipsis; }}
      .row .num {{ text-align:right; font-size:.88rem; font-weight:700; color:#1a2433; }}
      .row .num span {{ display:block; font-size:.70rem; font-weight:600; color:#6b7686; }}
      .dot {{ width:10px; height:10px; border-radius:50%; flex:0 0 10px; }}
      .badge {{ display:inline-block; border-radius:999px; padding:5px 12px; font-size:.8rem; font-weight:700; }}
      .b-green {{ background:#E6F4EA; color:{GREEN}; }}
      .b-amber {{ background:#FEF7E0; color:#9A6700; }}
      .b-red {{ background:#FCE8E6; color:{RED}; }}
      .card {{ background:#fff; border-radius:16px; padding:16px 16px 6px;
               box-shadow:0 2px 8px rgba(16,24,40,.10); margin-bottom:12px; }}
      .card h2 {{ margin:0; font-size:1.15rem; color:{NAVY}; font-weight:800; }}
      .card .csub {{ font-size:.78rem; color:#6b7686; margin:2px 0 10px; }}
      .pbar {{ background:#EAEEF3; border-radius:999px; height:10px; margin:8px 0 4px; overflow:hidden; }}
      .pbar > div {{ height:100%; background:linear-gradient(90deg,{NAVY},#0A5BA0); border-radius:999px; }}
      .ptext {{ font-size:.76rem; color:#6b7686; }}
      .gift {{ background:#FFF8E7; border:1px solid #F4D58B; border-radius:12px; padding:10px 12px;
               margin:10px 0 2px; font-size:.86rem; color:#5a4a1a; }}
      .gift .gcost {{ display:block; margin-top:4px; font-size:.74rem; color:#8a6d2f; font-weight:700; }}
    </style>""", unsafe_allow_html=True)


def _admin_password() -> str:
    try:
        return str(st.secrets["admin_password"])
    except Exception:
        return "east-admin-2026"


def _admin_gate() -> bool:
    st.session_state.setdefault("admin", False)
    with st.sidebar:
        st.markdown("### 🔒 Admin")
        if st.session_state.admin:
            st.success("Admin mode — costing visible")
            if st.button("Log out"):
                st.session_state.admin = False; st.rerun()
        else:
            st.caption("Sales team: leave this closed. Admins unlock gift names / costing.")
            pw = st.text_input("Admin password", type="password", key="pw")
            if st.button("Unlock"):
                if pw and pw == _admin_password():
                    st.session_state.admin = True; st.rerun()
                else:
                    st.error("Incorrect password")
    return st.session_state.admin


# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
def render(scheme: Scheme):
    st.set_page_config(page_title=f"Power Play (Q1) · {scheme.region}", page_icon="📊", layout="centered")
    _css()

    dated_paths = scheme.paths(scheme.dated_files)
    agg_paths = scheme.paths(scheme.agg_files)
    gifts_path = scheme.paths((scheme.gifts_file,))[0]
    all_paths = [p for p in (*dated_paths, *agg_paths, gifts_path) if Path(p).exists()]
    if not all_paths:
        st.error(f"No data files found for {scheme.region}."); st.stop()
    mtime = max(Path(p).stat().st_mtime for p in all_paths)
    eb_iso = scheme.eb_date.isoformat() if scheme.eb_date else None

    dated = _load_dated(dated_paths, mtime, eb_iso)
    agg = _load_agg(agg_paths, mtime)
    gifts = _load_gifts(gifts_path, mtime)
    dealers = _aggregate(scheme, dated, agg)
    last_updated = datetime.fromtimestamp(mtime).strftime("%d %b %Y")
    admin = _admin_gate()

    PPM, GPP, MIN = scheme.points_per_mt, scheme.gift_per_point, scheme.min_mt
    EB = scheme.early_bird

    # Hero
    rate = f"₹{int(GPP)}/pt · " if admin else ""
    eb_txt = (f"+25% early-bird by {scheme.eb_date.strftime('%d %b %Y')} · " if EB else "")
    st.markdown(
        f'<div class="hero"><div class="hero-row">{_logo_img()}'
        f'<div class="hero-txt"><h1>{scheme.title}</h1>'
        f'<div class="sub">{int(PPM)} pts/MT · {rate}{eb_txt}qualify at {int(MIN)} MT</div></div></div>'
        f'<span class="pill">Dealer qualifying status · updated till {_till_date()}</span></div>',
        unsafe_allow_html=True)

    if dealers.empty:
        st.info("No dealer data yet."); st.stop()

    # Filters: Zone (only if >1 zone) -> State -> Distributor -> Dealer
    def pick(label, frame, col):
        opts = ["All"] + sorted(frame[col].unique().tolist())
        choice = st.selectbox(label, opts, key=f"f_{col}")
        return frame if choice == "All" else frame[frame[col] == choice]

    multi_zone = dealers["Zone"].nunique() > 1
    fcols = st.columns(4 if multi_zone else 3)
    scope = dealers
    i = 0
    if multi_zone:
        with fcols[i]:
            scope = pick("Zone", scope, "Zone"); i += 1
    with fcols[i]:
        scope = pick("State", scope, "State"); i += 1
    with fcols[i]:
        scope = pick("Distributor", scope, "Distributor"); i += 1
    with fcols[i]:
        scope = pick("Dealer", scope, "Dealer")

    if len(scope) == 1:
        _dealer_detail(scheme, scope.iloc[0], admin, gifts, dated, agg)
    else:
        _kpi_band(scheme, scope, admin)
        labels = ["🏆 Leaderboard", "🎯 Push list", "📋 All dealers"]
        if admin:
            labels.append("💰 Summary")
        tabs = st.tabs(labels)
        with tabs[0]:
            top = scope.sort_values(["Points", "Total MT"], ascending=False).head(15)
            st.markdown(_rows(scheme, top, admin, ranked=True), unsafe_allow_html=True)
            eb_leg = "🟢 early bird · " if EB else ""
            st.caption(f"Top 15 by points. {eb_leg}🔵 qualified · 🟠 almost (8–12 MT) · 🔴 not qualified")
        with tabs[1]:
            push = scope[(scope["Total MT"] >= 8) & (scope["Total MT"] < MIN)] \
                .sort_values("Total MT", ascending=False)
            if push.empty:
                st.info("No dealers in the 8–12 MT push range for this scope. 🎉")
            else:
                st.markdown(f"**{len(push)} dealers** are 8–12 MT — one push gets them qualified:")
                st.markdown(_rows(scheme, push, admin, ranked=False, note="push"), unsafe_allow_html=True)
        with tabs[2]:
            show = scope.copy()
            show["Status"] = show.apply(lambda r: status_of(scheme, r)[1], axis=1)
            show["Points"] = show["Points"].apply(inr)
            cols = (["Zone"] if multi_zone else []) + ["Dealer", "Distributor", "State", "Total MT", "Points"]
            if admin:
                show["Qualified Gift"] = show["Total MT"].apply(
                    lambda t: (gift_for(t, gifts)["Gift"] if gift_for(t, gifts) is not None else "—"))
                show["Gift Value"] = show["Gift Value"].apply(lambda x: "₹" + inr(x))
                cols += ["Qualified Gift", "Gift Value"]
            cols.append("Status")
            st.dataframe(show[cols], hide_index=True, width="stretch")
            st.caption("Tip: pick a Dealer in the filter above for full details.")
        if admin:
            with tabs[3]:
                _summary(scheme, scope, gifts, multi_zone)


def _summary(scheme, scope, gifts, multi_zone):
    """Admin-only roll-up: totals + breakdown by State / Distributor / Gift,
    with estimated running gift cost (each qualified dealer at full catalogue value)."""
    df = scope.copy()
    tiers = gifts.sort_values("MT")
    cost_of = {int(r.MT): int(r.Cost) for _, r in tiers.iterrows()}
    name_of = {0: "No gift", **{int(r.MT): f"{int(r.MT)} MT · {r.Gift}" for _, r in tiers.iterrows()}}

    def tier_mt(t, q):
        g = gift_for(t, gifts) if q else None
        return int(g["MT"]) if g is not None else 0
    df["TierMT"] = [tier_mt(t, q) for t, q in zip(df["Total MT"], df["Qualified"])]
    df["GiftCost"] = df["TierMT"].map(lambda m: cost_of.get(m, 0))

    tot_d, tot_q = len(df), int(df["Qualified"].sum())
    tot_v = df["Total MT"].sum()
    qual_v = df.loc[df["Qualified"], "Total MT"].sum()
    run_cost = int(df["GiftCost"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Dealers (qual / total)", f"{tot_q} / {tot_d}")
    c2.metric("Total MT", mt_fmt(tot_v))
    c3.metric("Qualified MT", mt_fmt(qual_v))
    st.metric("Est. running gift cost (at max value)", "₹" + inr(run_cost),
              help="Each qualified dealer's tier gift at full catalogue cost (incl. TDS).")

    dim = st.radio("Break down by", ["State", "Distributor", "Gift"], horizontal=True)

    if dim == "Gift":
        grp = df.groupby("TierMT")
        out = pd.DataFrame({
            "Dealers": grp["Dealer"].count(),
            "Total MT": grp["Total MT"].sum(),
            "Est. Cost ₹": grp["GiftCost"].sum(),
        }).reset_index().sort_values("TierMT")
        out["Gift"] = out["TierMT"].map(name_of)
        out["Total MT"] = out["Total MT"].map(mt_fmt)
        out["Est. Cost ₹"] = out["Est. Cost ₹"].map(lambda x: "₹" + inr(x))
        st.dataframe(out[["Gift", "Dealers", "Total MT", "Est. Cost ₹"]],
                     hide_index=True, width="stretch")
        st.caption("Est. cost = dealers × gift catalogue cost (max value, incl. TDS). "
                   "'No gift' = below 12 MT.")
    else:
        col = dim
        grp = df.groupby(col)
        out = pd.DataFrame({
            "Dealers": grp["Dealer"].count(),
            "Qualified": grp["Qualified"].sum().astype(int),
            "Total MT": grp["Total MT"].sum(),
            "Est. Cost ₹": grp["GiftCost"].sum(),
        })
        out["Qual. MT"] = df[df["Qualified"]].groupby(col)["Total MT"].sum()
        out["Qual. MT"] = out["Qual. MT"].fillna(0)
        out = out.reset_index().sort_values("Total MT", ascending=False)
        out["Total MT"] = out["Total MT"].map(mt_fmt)
        out["Qual. MT"] = out["Qual. MT"].map(mt_fmt)
        out["Est. Cost ₹"] = out["Est. Cost ₹"].map(lambda x: "₹" + inr(x))
        st.dataframe(out[[col, "Dealers", "Qualified", "Total MT", "Qual. MT", "Est. Cost ₹"]],
                     hide_index=True, width="stretch")


def _kpi_band(scheme, df, admin):
    MIN = scheme.min_mt
    push = int(((df["Total MT"] >= 8) & (df["Total MT"] < MIN)).sum())
    cells = [("", "Active dealers", str(len(df))),
             ("", "Total MT", mt_fmt(df["Total MT"].sum()))]
    if scheme.early_bird:
        cells.append(("", f"MT by {scheme.eb_date.strftime('%d-%b')}", mt_fmt(df["MT_eb"].sum())))
    cells.append(("green", "Qualified ≥12 MT", str(int(df["Qualified"].sum()))))
    if scheme.early_bird:
        cells.append(("green", "Early bird", str(int(df["Early Bird"].sum()))))
    cells.append(("accent", "Push list (8–12)", str(push)))
    cells.append(("", "Total points", inr(df["Points"].sum())))
    if admin:
        cells.append(("accent", "Gift value", "₹" + inr(df["Gift Value"].sum())))
    html_cells = "".join(
        f'<div class="kpi {c}"><div class="v">{v}</div><div class="l">{l}</div></div>'
        for c, l, v in cells)
    st.markdown(f'<div class="kpi-grid">{html_cells}</div>', unsafe_allow_html=True)


def _rows(scheme, df, admin, ranked=True, note=None) -> str:
    out = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        color, _ = status_of(scheme, r)
        rank = f'<div class="rank">{i}</div>' if ranked else ""
        if note == "push":
            right = f'{mt_fmt(r["Total MT"])} MT<span>needs {mt_fmt(scheme.min_mt - r["Total MT"])} MT</span>'
        else:
            gift = f' · ₹{inr(r["Gift Value"])}' if admin else ""
            right = f'{mt_fmt(r["Total MT"])} MT<span>{inr(r["Points"])} pts{gift}</span>'
        sub = (f'{r["Zone"]} · ' if df["Zone"].nunique() > 1 else "") + \
              f'{html.escape(r["Distributor"])} · {html.escape(r["State"])}'
        out.append(
            f'<div class="row">{rank}<div class="info"><div class="name">{html.escape(r["Dealer"])}</div>'
            f'<div class="sub">{sub}</div></div><div class="num">{right}</div>'
            f'<div class="dot" style="background:{color}"></div></div>')
    return "".join(out)


def _dealer_detail(scheme, r, admin, gifts, dated, agg):
    MIN, PPM, GPP, EB = scheme.min_mt, scheme.points_per_mt, scheme.gift_per_point, scheme.early_bird
    color, label = status_of(scheme, r)
    bcls = {GREEN: "b-green", AMBER: "b-amber", RED: "b-red", NAVY: "b-amber"}[color]
    st.markdown(
        f'<div class="card"><h2>{html.escape(r["Dealer"])}</h2>'
        f'<div class="csub">{html.escape(r["Distributor"])} · {html.escape(r["State"])} · {r["Zone"]}</div>'
        f'<span class="badge {bcls}">{label}</span></div>', unsafe_allow_html=True)
    cols = st.columns(3 if admin else 2)
    cols[0].metric("Total MT", mt_fmt(r["Total MT"]))
    cols[1].metric("Points", inr(r["Points"]))
    if admin:
        cols[2].metric("Gift Value", "₹" + inr(r["Gift Value"]))

    if not r["Qualified"]:
        st.warning(f"Needs **{mt_fmt(MIN - r['Total MT'])} more MT** to reach the {int(MIN)} MT minimum.")
    else:
        ng, need = next_gift(r["Total MT"], gifts)
        if ng is not None:
            tier = ng["MT"]; pct = min(r["Total MT"] / tier, 1.0) * 100
            mult = scheme.eb_mult if (EB and r["Early Bird"]) else 1.0
            tier_pts = tier * PPM * mult
            gnote = f' (₹{inr(tier_pts * GPP)})' if admin else ""
            st.markdown(
                f'<div class="pbar"><div style="width:{pct:.0f}%"></div></div>'
                f'<div class="ptext"><b>{mt_fmt(need)} MT</b> more to the <b>{int(tier)} MT</b> '
                f'milestone → ~{inr(tier_pts)} pts{gnote}</div>', unsafe_allow_html=True)
        else:
            st.success("🏆 Top milestone reached!")

    if EB:
        if r["Early Bird"]:
            st.caption(f"⚡ Early-bird secured: {mt_fmt(r['MT_eb'])} MT by {scheme.eb_date.strftime('%d %b')}.")
        elif r["Qualified"]:
            st.caption(f"No early-bird bonus (only {mt_fmt(r['MT_eb'])} MT by "
                       f"{scheme.eb_date.strftime('%d %b')}; needs ≥{int(MIN)} MT).")

    # qualified gift — admin only
    if admin and r["Qualified"]:
        g = gift_for(r["Total MT"], gifts)
        if g is not None:
            alt = (f' <i>or</i> {html.escape(str(g["AltGift"]))}'
                   if str(g.get("AltGift", "")).strip() else "")
            st.markdown(
                f'<div class="gift">🎁 <b>Qualified gift</b> · {int(g["MT"])} MT tier<br>'
                f'{html.escape(str(g["Gift"]))}{alt}'
                f'<span class="gcost">gift cost ₹{inr(g["Cost"])}</span></div>', unsafe_allow_html=True)
        ng, need = next_gift(r["Total MT"], gifts)
        if ng is not None:
            st.caption(f"➕ {mt_fmt(need)} MT more unlocks the {int(ng['MT'])} MT gift: {ng['Gift']}.")

    # billing history
    sel = lambda d: ((d["Distributor"] == r["Distributor"]) & (d["Dealer"] == r["Dealer"])
                     & (d["State"] == r["State"]) & (d["Zone"] == r["Zone"]))
    hist = []
    if not dated.empty:
        for _, x in dated[sel(dated)].sort_values("Date").iterrows():
            win = ("≤ cutoff (early bird)" if EB and pd.notna(x["Date"]) and x["Date"] <= pd.Timestamp(scheme.eb_date)
                   else "after cutoff" if EB else "")
            hist.append({"Date": x["Date"].strftime("%d %b %Y") if pd.notna(x["Date"]) else "—",
                         "MT": x["MT"], **({"Window": win} if EB else {})})
    amt = agg[sel(agg)]["MT"].sum() if not agg.empty else 0.0
    if amt > 0:
        hist.append({"Date": "Secondary sales (to date)", "MT": round(amt, 2),
                     **({"Window": "after cutoff"} if EB else {})})
    if hist:
        with st.expander(f"Billing detail ({len(hist)} entries)"):
            st.dataframe(pd.DataFrame(hist), hide_index=True, width="stretch")
