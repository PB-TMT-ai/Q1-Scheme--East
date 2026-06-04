"""Scheme definitions. Each zone-scheme is pure config; the dashboard renders any of them."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DATA = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Scheme:
    key: str
    title: str                 # hero title
    region: str                # e.g. "East" / "North & Central"
    points_per_mt: float
    gift_per_point: float
    min_mt: float
    early_bird: bool
    data_dir: Path
    dated_files: tuple = ()     # CSVs with a Date column (for the early-bird split)
    agg_files: tuple = ()       # CSVs without dates (one row per dealer, counted post-cutoff)
    gifts_file: str = "gifts.csv"
    eb_mult: float = 1.25
    eb_date: date | None = None  # early-bird cutoff (only if early_bird)

    def paths(self, names) -> tuple:
        return tuple(str(self.data_dir / n) for n in names)


EAST = Scheme(
    key="east",
    title="⚡ Q1 Scheme · East",
    region="East",
    points_per_mt=50,
    gift_per_point=12,
    min_mt=12,
    early_bird=True,
    eb_date=date(2026, 5, 20),
    data_dir=DATA / "east",
    dated_files=("may_transactions.csv",),
    agg_files=("june_secondary.csv",),
)

NORTH_CENTRAL = Scheme(
    key="north_central",
    title="⚡ Q1 Scheme · North & Central",
    region="North & Central",
    points_per_mt=35,
    gift_per_point=10,
    min_mt=12,
    early_bird=False,
    data_dir=DATA / "north_central",
    dated_files=(),
    agg_files=("secondary.csv",),
)
