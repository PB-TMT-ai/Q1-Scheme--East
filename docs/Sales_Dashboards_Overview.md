# JSW One — Sales Dashboards: Overview, Usage & Benefits

*Internal document · Private Brand (PB) · prepared for the sales leadership & field teams*

---

## 1. What we are doing — the purpose

We have built a small suite of **lightweight, mobile-first dashboards** that put the
numbers a sales person needs **in their pocket** — accessible from any phone browser, with
**no app to install and no spreadsheets to dig through**. Each dashboard turns raw
business data into a clear, live picture the team can act on at the dealer counter.

The goal is simple: **help the field team sell more, with facts, in real time** — while
keeping the underlying data **secure and access-controlled**.

---

## 2. The dashboards

| # | Dashboard | Link | What it shows |
|---|-----------|------|---------------|
| 1 | **Power Play (Q1) Scheme — East** | https://powerplayq1schemeeast.streamlit.app/ | Live status of every East dealer on the Q1 volume scheme — MT done, points earned, exact gap to qualify (12 MT), milestones and gifts. |
| 2 | **Power Play (Q1) Scheme — North & Central** | https://powerplayq1schemenandc.streamlit.app/ | The same, for North & Central dealers, on their own scheme (35 pts/MT, no early-bird), with a Zone filter for the two regions. |
| 3 | **Price Calculator (PB)** | https://price-calculator-pb.streamlit.app/ | A quick on-the-spot pricing tool, so reps can compute and quote the correct PB product price at the counter without manual errors. *(description to be tailored)* |
| 4 | **Influencers Performance (FY 26)** | https://influencers-performance--fy-26-f2ksnglyfoctsn4iln8jpg.streamlit.app/ | Tracks influencer (e.g. mason / contractor) engagement and performance through FY 26, so the team can see who is active and where to focus. *(description to be tailored)* |

> Dashboards 1 and 2 are described in full below; lines marked *“to be tailored”* for 3
> and 4 can be refined to match exactly how those tools work.

---

## 3. How we use it

**Data in → dashboard out.** For the scheme dashboards, the flow each cycle is:

1. The latest **secondary-sales data** (per dealer, all zones) is provided.
2. It is processed — routed to the correct region, dealer records matched and de-duplicated,
   volumes consolidated.
3. The dashboards update automatically and the **same shared link** always shows the
   latest position — **no new link, no resend**.

**Cadence:** scheme data is refreshed **daily** (status “updated till yesterday / T-1”),
so what the team sees before a counter visit is current.

**On the ground, a rep simply:**
- Opens their zone’s link (bookmarked on the phone home screen),
- Filters **Zone → State → Distributor → Dealer**,
- Reads the dealer’s status in seconds.

---

## 4. How it is beneficial to the sales team

- **Sell with facts at the counter** — show the dealer exactly where they stand and the
  reward within reach, instead of vague reminders.
- **Know who to push** — a **“push list”** flags dealers who are *one order away* from
  qualifying (8–12 MT), turning the scheme into clear, actionable targets.
- **See the leaders** — a leaderboard ranks dealers by points, sparking healthy competition.
- **Plan the day better** — quickly scan a distributor or state to decide where to spend time.
- **Quote correctly** — the Price Calculator removes pricing guesswork and manual mistakes.
- **Track influencers** — visibility into influencer activity helps direct effort where it pays.
- **Zero friction** — works in any mobile browser, no install, no login hassle beyond a
  simple password, always up to date.

The core message to the field: **open it before every counter visit, and keep dealer
sales updated daily** — the dashboard is only as accurate as the data fed in.

---

## 5. How we have kept these dashboards secure (password-protected)

Data security and privacy are built into how these dashboards work:

- **Login required — no open access.** A visitor must enter a **valid username and
  password** before anything is shown. Without it, the dashboard reveals nothing.
- **Role-based access.** On the scheme dashboards there are **two levels**:
  - *Sales view* — volume and points only.
  - *Admin view* — additionally unlocks costing (gift values, programme cost). **All cost
    figures stay hidden from the general sales view.**
- **Credentials are not stored in the code.** Passwords are kept in the platform’s
  protected **secrets** store, separate from the application, and can be changed centrally
  at any time.
- **Encrypted in transit.** All access is over **HTTPS/TLS**, so logins and data are
  encrypted between the phone and the server.
- **Instant kill-switch.** Either dashboard can be taken **fully offline** on demand — it
  then shows only an “offline” screen with no data, no login — and brought back when needed.
- **Confidential by instruction.** Credentials are shared only with the intended team and
  are not to be circulated in open groups.

> This gives **need-to-know access**: the right people see the right data, costing is
> shielded from the field, and access can be locked down immediately if ever required.

---

## 6. Keeping it running

- **One shared codebase** drives the scheme dashboards, with each region as simple
  configuration — so a new zone or scheme can be added quickly and consistently.
- **Routine refresh:** new data is processed and published on a regular cadence; the
  links never change.
- **Lightweight & low-cost:** hosted as web apps, opened from a link — nothing to deploy
  on anyone’s phone.

---

*For access, data updates, or changes to any of these dashboards, contact the dashboard
administrator.*
