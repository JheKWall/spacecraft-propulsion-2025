"""Verify a hand-performed Workbench import.

Read-only - this script never writes to the database. It is the automated safety
net around the manual import, not a replacement for it: the import is done by
hand deliberately, and this checks the hand did what it meant to.

The checks mirror the failure modes that are plausible here. A column mapping
slip in the import wizard produces wrong values, not an error, so row counts
alone are not enough; orphan checks confirm the foreign keys held, and the range
check confirms no low/high pair was swapped in transit.
"""
import mysql.connector
import pandas as pd

from config import DB, EXPECTED_SYSTEM_COUNT, IMPORT_DIR, db_password

TABLES = [
    ("source", "1_source.csv"),
    ("propulsion_system", "2_propulsion_system.csv"),
    ("measurement", "3_measurement.csv"),
]


def main():
    conn = mysql.connector.connect(**DB, password=db_password())
    cur = conn.cursor()

    counts = []
    for table, filename in TABLES:
        expected = len(pd.read_csv(IMPORT_DIR / filename, index_col=False))
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        counts.append((table, expected, cur.fetchone()[0]))

    # Orphans should be impossible given the foreign keys. Assert anyway - a
    # constraint you never test is a constraint you are trusting on faith.
    cur.execute("""
        SELECT COUNT(*) FROM measurement m
        LEFT JOIN propulsion_system s ON s.system_id = m.system_id
        WHERE s.system_id IS NULL
    """)
    orphan_systems = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM measurement m
        LEFT JOIN source src ON src.source_id = m.source_id
        WHERE src.source_id IS NULL
    """)
    orphan_sources = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM measurement WHERE value_low > value_high")
    inverted = cur.fetchone()[0]

    # Systems with no measurements at all. Not an error - DRACO is expected here -
    # but it should be a deliberate list, not a surprise.
    cur.execute("""
        SELECT s.name FROM propulsion_system s
        LEFT JOIN measurement m ON m.system_id = s.system_id
        WHERE m.measurement_id IS NULL
        ORDER BY s.name
    """)
    empty = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()

    failures = []
    for table, expected, actual in counts:
        status = "OK" if expected == actual else "MISMATCH"
        print(f"  {table:<12} expected {expected:>4}   loaded {actual:>4}   {status}")
        if expected != actual:
            failures.append(f"{table}: expected {expected}, loaded {actual}")

    loaded = {t: a for t, _, a in counts}
    if loaded["propulsion_system"] != EXPECTED_SYSTEM_COUNT:
        failures.append(
            f"expected {EXPECTED_SYSTEM_COUNT} systems, "
            f"found {loaded['propulsion_system']}")
    if orphan_systems:
        failures.append(f"{orphan_systems} measurements reference a missing system")
    if orphan_sources:
        failures.append(f"{orphan_sources} measurements reference a missing source")
    if inverted:
        failures.append(f"{inverted} measurements have value_low > value_high")

    if empty:
        print(f"\n  systems with no measurements ({len(empty)}): {', '.join(empty)}")

    if failures:
        raise RuntimeError(
            "import verification FAILED:\n  " + "\n  ".join(failures)
            + "\n\nTwo causes worth checking, in this order:"
              "\n  1. FEWER ROWS THAN EXPECTED. MySQL in strict mode rejects a row"
              " whose value exceeds a column's width, rather than truncating it,"
              " and reports nothing against that row. Run `python src/clean.py` -"
              " it checks every text field against config.COLUMN_LIMITS and will"
              " name the offending row."
              "\n  2. RIGHT ROW COUNT, WRONG VALUES. That is a column mapping slip"
              " in the import wizard. Re-check the mapping screen."
        )

    print("\n  import verified: row counts match, no orphans, no inverted ranges")


if __name__ == "__main__":
    main()
