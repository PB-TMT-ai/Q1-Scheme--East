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

All volume lives in [`data/transactions.csv`](data/transactions.csv), one row per
billing:

```
Zone,State,Distributor,Dealer,Date,MT
East,West Bengal,Kolkata Traders,Acme Hardware,2026-05-10,30
```

The repo currently has **sample rows** — replace them with real data. Dates can be
`DD-MM-YYYY` or `YYYY-MM-DD`. The dashboard adds up each dealer's billings and splits
them by the 20 May cutoff automatically.

### Updating the data
The dashboard reads one file, `data/transactions.csv` (`Zone, State, Distributor,
Dealer, Date, MT`), but volume arrives in two shapes:

- **May 2026 — date-wise (frozen).** Each billing is its own row with its real date, so
  the 20-May early-bird split is exact. These rows are not touched again.
- **June 2026 onward — monthly aggregate.** Source file columns: `Zone, SF Id, Company
  Name, Secondary Sales in <Month>'26, State Name, Corrected Distributor Name`. Claude
  filters `Zone = East`, maps each dealer to one row dated within that month (June is
  always after the 20-May cutoff, so an exact date isn't needed), and **replaces** that
  month's rows wholesale on every refresh — so re-sending an updated June file never
  double-counts.

Just send Claude the latest file (either shape) and it updates `data/transactions.csv`
and pushes. Streamlit Cloud redeploys the same URL within a minute.

> Note: the original May export ran through 2 June, so early June volume was already in
> the DB; the June aggregate file replaces those rows rather than adding to them.

## Deploy once (so the team gets a shareable link)

1. Push this repo to GitHub (already at `pb-tmt-ai/q1-scheme--east`).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. **New app** → pick repo `pb-tmt-ai/q1-scheme--east`, the working branch, main file
   `app.py` → **Deploy**.
4. Copy the resulting URL (e.g. `https://q1-scheme-east.streamlit.app`) and share it with
   the sales team. They open it in any mobile browser — no login, no install.

## Admin / costing access

The sales team sees only **volume (MT)** and **points** — all **gift value (₹) / costing**
is hidden. To reveal it, open the sidebar (☰ on mobile) → **Admin** → enter the password
→ **Unlock**.

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
