# Q1 Scheme · Dealer Status Dashboards (East / North & Central)

Mobile-friendly dashboards so each zone's sales team can check, on their phones, where
every dealer stands on the Q1 FY27 volume scheme — MT done, points earned, and what's
left to qualify. One codebase, **scheme-driven**: each zone is pure config.

## Live links

| Zone | Entry file | URL |
|---|---|---|
| East | `app.py` | https://q1-scheme--east-twhgn52coprhjw4ffsps4u.streamlit.app/ |
| North & Central | `app_north_central.py` | https://q1-scheme--east-evsh2qyag3uhjx46llltsv.streamlit.app/ |

Both deploy from this one repo; each data push refreshes the matching link automatically.

## Schemes

| | **East** | **North & Central** |
|---|---|---|
| Points / MT | 50 | 35 |
| Gift value / point | ₹12 | ₹10 |
| Early bird | +25% on volume by 20 May 2026 (if that slice ≥ 12 MT) | none |
| Qualify min | 12 MT | 12 MT |
| Gift tiers (MT) | 12/24/36/48/60/80/100 | 12/30/60/90/120/150/200 |
| Zones | East | North + Central (combined, with a Zone filter) |

Full scheme definitions live in [`docs/SCHEME.md`](docs/SCHEME.md); original workbooks in
[`docs/`](docs/). Points are **linear**; **gifts are tier-based** (a dealer earns the gift
of the highest MT tier reached).

## Code layout

- `dashboard.py` — the shared, scheme-aware UI + calculation engine (`render(scheme)`).
- `schemes.py` — the `Scheme` config objects (`EAST`, `NORTH_CENTRAL`).
- `app.py` — **East** entry (`render(EAST)`).
- `app_north_central.py` — **North & Central** entry (`render(NORTH_CENTRAL)`).

Adding another zone = one `Scheme` entry + a data folder + a 3-line entry file. No engine
changes.

## Data

Per scheme, under `data/<scheme>/`:

- **East** (`data/east/`):
  - `may_transactions.csv` — May, date-wise (frozen): `Zone,State,Distributor,Dealer,Date,MT`.
  - `june_secondary.csv` — June month-to-date aggregate: `Zone,State,Distributor,Dealer,MT`.
  - `gifts.csv` — gift catalog per MT tier.
- **North & Central** (`data/north_central/`) — no dates / no early bird, so each file is
  a per-dealer aggregate that the app **sums**:
  - `may_secondary.csv` — May totals (frozen). `Zone,State,Distributor,Dealer,MT,SF_Id`.
  - `june_secondary.csv` — June month-to-date (replaced on each refresh). Same columns.
  - `gifts.csv` — gift catalog per MT tier.
  - `SF_Id` is carried only to align a dealer's June row to its May attributes (so the two
    months sum to one dealer); the app ignores the column otherwise.

### Updating the data
Send Claude the latest secondary-sales export (columns `Zone, SF Id, Company Name,
Secondary Sales in <Month>'26, State Name, Corrected Distributor Name`). Claude scopes by
**Zone** (East, or North + Central), normalizes names, and **replaces** the relevant
aggregate file wholesale — so re-feeding (e.g. daily) never double-counts. East's May file
is frozen; revisit only for corrections.

Streamlit Cloud redeploys each app within a minute of a push.

## Deploy (one app per zone → one link each)

On **https://share.streamlit.io** (sign in with GitHub), create **two** apps from this
same repo:

1. East → main file `app.py` → e.g. `https://q1-scheme-east.streamlit.app`
2. North & Central → main file `app_north_central.py` → e.g. `https://q1-scheme-north-central.streamlit.app`

Share each link with the matching team. They open it in any mobile browser — no login.

## Access & login

**One login page decides the role from the password entered:**

- **Team password** → **Sales UI** (MT + points only).
- **Admin password** (with any username) → **Admin UI** directly — gift names, gift value
  (₹) and the Summary tab. No separate unlock step.

Nothing is visible until a valid login. Role + log-out show in the sidebar.

Set credentials via Streamlit secrets (do **not** commit them) — on **each** app:
**Settings → Secrets**:

```toml
# admin unlock (costing)
admin_password = "your-admin-secret"

# team login — option A: one shared login
app_username = "sales"
app_password = "your-team-secret"

# team login — option B: multiple logins (overrides option A)
[users]
east_team = "pass1"
nc_team   = "pass2"
```

Locally, put the same in `.streamlit/secrets.toml` (git-ignored). Fallbacks if unset:
team `sales` / `powerplay2026`, admin `east-admin-2026` — **change these before sharing.**

> Note: this is shared-password protection (good for a field team), not enterprise SSO.
> Sessions don't persist a cookie, so users log in again when they reopen/refresh the link.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py                  # East
streamlit run app_north_central.py    # North & Central
```

## Using a dashboard

Filter **(Zone →) State → Distributor → Dealer**. Pick a single dealer for metric cards
(MT, Points, and — admin — Gift Value + qualified gift), progress to the next milestone,
and billing detail. Leave filters on "All" for the KPI band, leaderboard, push list
(8–12 MT) and the full dealer table.
