"""Shared configuration: paths, database settings, physical constants.

Every other module imports from here rather than hard-coding a path or a constant,
so there is exactly one place to change when something moves.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
IMPORT_DIR = PROCESSED_DIR / "import"
OUTPUT_DIR = PROJECT_ROOT / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"
QUERIES_DIR = OUTPUT_DIR / "queries"
SQL_DIR = PROJECT_ROOT / "sql"
SECRETS_DIR = PROJECT_ROOT / "secrets"
DOCS_DIR = PROJECT_ROOT / "docs"

# Physical constants
G0 = 9.80665                      # standard gravity, m/s^2
SPEED_OF_LIGHT = 299_792_458.0    # m/s

# Canonical units. Every measurement is converted to these at clean time, so the
# raw CSV can hold whatever the source actually printed.
CANONICAL_UNITS = {
    "isp": "s",
    "thrust": "N",
    "engine_mass": "kg",
    "input_power": "kW",
}

EXPECTED_SYSTEM_COUNT = 15

# Text column widths, mirroring sql/schema.sql. MySQL in strict mode REJECTS an
# over-length row rather than truncating it, so a value that outgrows its column
# disappears at import with no error on the row itself - the count simply comes
# out short. Checked at clean time so the failure surfaces here instead.
COLUMN_LIMITS = {
    "unit": 20,
    "page": 60,
    "quoted_text": 1000,
    "note": 1000,
}

# Physics sanity bounds, independent of any source. A correctly quoted number in
# the wrong unit passes a citation check and is still wrong; these catch that.
SANITY_BOUNDS = {
    ("chemical", "isp"): (150.0, 500.0),
    ("electric", "isp"): (300.0, 10_000.0),
    ("nuclear", "isp"): (700.0, 1.0e7),
}

DB = {
    "host": "localhost",   # NOT 127.0.0.1 - MySQL binds IPv6 on this machine
    "port": 3306,
    "database": "spacecraft_propulsion",
    "user": "propulsion_app",
}


def db_password() -> str:
    """Read the scoped app password. Never hard-code, print, or log this."""
    return (SECRETS_DIR / "mysql_app_password.txt").read_text(encoding="utf-8").strip()
