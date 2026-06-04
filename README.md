# Q1 Scheme – East · Dealer Status Dashboard

A mobile-friendly dashboard so the East sales team can check, on their phones, where
each dealer stands on the Q1 FY26 volume scheme — points earned, gift value, and
what's left to qualify.

## How the scheme is calculated

- **Region:** East · **50 points per MT** · **₹12 gift value per point**
- **Qualifying minimum:** a dealer must do **≥ 12 MT total** to earn any points.
- **Points:** linear — `MT × 50`.
- **Early-bird bonus (+25%):** the volume billed **on or before 20 May 2026** earns
  **×1.25** — *but only if that on-or-before-20-May volume is itself ≥ 12 MT*.
  Volume billed after 20 May always earns ×1.0.
- **Gift value (₹):** `points × 12`.

> Example: 30 MT on 10 May + 20 MT on 1 June → `30×62.5 + 20×50 = 2,875 pts` → **₹34,500**.

## The data

Volume lives in **two separate files** under `data/`, combined by the app per dealer:

- [`may_transactions.csv`](data/may_transactions.csv) — **May, date-wise (frozen).**
  `Zone,State,Distributor,Dealer,Date,MT`, one row per billing. The real dates keep the
  20-May early-bird split exact. Not touched again.
- [`june_secondary.csv`](data/june_secondary.csv) — **June month-to-date aggregate.**
  `Zone,State,Distributor,Dealer,MT`, one row per dealer (June is entirely after the
  20-May cutoff, so no dates needed).

The scheme gift catalog is in [`data/gifts.csv`](data/gifts.csv) (per MT tier); the full
scheme is preserved in [`docs/SCHEME.md`](docs/SCHEME.md) and
[`docs/Q1_scheme_East.xlsx`](docs/Q1_scheme_East.xlsx).

### Updating the data
- **June (daily):** send Claude the latest secondary-sales export (columns `Zone, SF Id,
  Company Name, Secondary Sales in <Month>'26, State Name, Corrected Distributor Name`).
  Claude filters `Zone = East`, normalizes the distributor names, and **replaces**
  `june_secondary.csv` wholesale — so re-feeding daily never double-counts.
- **May:** frozen; only revisit if a correction is needed.

Streamlit Cloud redeploys the same URL within a minute of each push.

> Note: the original May export ran through 2 June, so that early-June volume now lives in
> `june_secondary.csv`, not the May file.

## Deploy once (so the team gets a shareable link)

1. Push this repo to GitHub (already at `pb-tmt-ai/q1-scheme--east`).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. **New app** → pick repo `pb-tmt-ai/q1-scheme--east`, the working branch, main file
   `app.py` → **Deploy**.
4. Copy the resulting URL (e.g. `https://q1-scheme-east.streamlit.app`) and share it with
   the sales team. They open it in any mobile browser — no login, no install.

## Admin / costing access

The sales team sees only **volume (MT)** and **points** — all **gift names, gift value (₹)
and costing** are hidden. To reveal them (qualified gift per dealer, gift cost, next-gift
target), open the sidebar (☰ on mobile) → **Admin** → enter the password → **Unlock**.

Set the password via Streamlit secrets (do **not** commit it). On Streamlit Community
Cloud: app → **Settings → Secrets**, add:

```toml
admin_password = "your-secret-here"
```

Locally, create `.streamlit/secrets.toml` (already git-ignored) with the same line.
If no secret is set, the fallback password is `east-admin-2026` — change it before sharing.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Using the dashboard

- Filter **Zone → State → Distributor → Dealer**. Pick a single dealer to see metric
  cards (Total MT, Points, Gift Value), qualifying / early-bird status, progress to the
  next milestone, and full billing history.
- Leave filters on "All" to get a roll-up overview and a scannable dealer list.
