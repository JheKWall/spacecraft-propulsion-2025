"""Read raw CSVs, validate them, write data/processed/ and the Workbench import files.

Validation is fail-loud by design. The lesson from project 1 was that a silent
data defect matched zero rows and nothing errored; every rule here raises rather
than warns, and none of them is caught anywhere in the pipeline.

There are two kinds of rule, and the distinction matters:

  validate_measurements  structural and referential - does this row point at real
                         things, is it internally coherent, can it be defended
  validate_physics       does this number make physical sense, independent of any
                         citation

The second exists because a correctly quoted figure from a peer-reviewed source
can still be wrong. Frisbee (2003) Table 3 is the worked example: its antimatter
entry is 333 times the speed of light, faithfully published and faithfully
transcribed for years. Provenance checking would never have caught it.
"""
import pandas as pd

from config import (CANONICAL_UNITS, COLUMN_LIMITS, IMPORT_DIR, PROCESSED_DIR,
                    RAW_DIR, SANITY_BOUNDS)
from metrics import exceeds_light_speed


class ValidationError(Exception):
    """Raised when raw data violates a rule. Never caught inside the pipeline."""


def validate_measurements(df, known_sources, known_systems):
    """Structural and referential rules. Raises on the first violation found."""
    for i, row in df.iterrows():
        where = f"row {i} ({row['system_name']}/{row['metric']})"

        if row["source_key"] not in known_sources:
            raise ValidationError(f"{where}: unknown source '{row['source_key']}'")

        if row["system_name"] not in known_systems:
            raise ValidationError(f"{where}: unknown system '{row['system_name']}'")

        if row["value_low"] > row["value_high"]:
            raise ValidationError(
                f"{where}: value_low > value_high "
                f"({row['value_low']} > {row['value_high']})"
            )

        expected_unit = CANONICAL_UNITS[row["metric"]]
        if row["unit"] != expected_unit:
            raise ValidationError(
                f"{where}: unit '{row['unit']}' is not the canonical "
                f"'{expected_unit}' for {row['metric']}"
            )

        quote = row.get("quoted_text")
        if quote is None or (isinstance(quote, float) and quote != quote) or not str(quote).strip():
            raise ValidationError(
                f"{where}: quoted_text is empty - a figure that cannot be traced "
                f"back to a sentence does not belong in this dataset"
            )

        if row["metric"] == "isp" and exceeds_light_speed(row["value_high"]):
            raise ValidationError(
                f"{where}: Isp {row['value_high']} s implies an exhaust velocity "
                f"above the speed of light"
            )

        validate_lengths(row, where)


def validate_lengths(row, where):
    """Check text fields fit their database columns.

    This rule exists because of a real failure. Six rows were silently dropped
    during a Workbench import: their `note` and `page` values had outgrown
    VARCHAR(500) and VARCHAR(20), and MySQL in strict mode rejects an over-length
    row rather than truncating it. No error appeared against any individual row -
    the total simply came out six short, and only a row-count assertion caught it.

    Every other rule in this module checks whether a value is *right*. This one
    checks whether it *fits*, which is a different failure and was the gap.
    """
    for column, limit in COLUMN_LIMITS.items():
        value = row.get(column)
        if value is None or (isinstance(value, float) and value != value):
            continue
        length = len(str(value))
        if length > limit:
            raise ValidationError(
                f"{where}: {column} is {length} characters, exceeding the "
                f"VARCHAR({limit}) column in sql/schema.sql. MySQL would reject "
                f"this row at import without reporting it. Shorten the value or "
                f"widen the column in both schema.sql and config.COLUMN_LIMITS."
            )


def validate_physics(measurements, systems):
    """Physics bounds, independent of any citation.

    Catches unit errors and transposition - the failure mode that passes a
    provenance check because the number really was published, just not in the
    unit it was recorded as.
    """
    categories = dict(zip(systems["name"], systems["category"]))

    for i, row in measurements.iterrows():
        category = categories.get(row["system_name"])
        bounds = SANITY_BOUNDS.get((category, row["metric"]))
        if bounds is None:
            continue

        lo, hi = bounds
        for bound_name, value in (("value_low", row["value_low"]),
                                  ("value_high", row["value_high"])):
            if not (lo <= value <= hi):
                raise ValidationError(
                    f"row {i} ({row['system_name']}/{row['metric']}): "
                    f"{bound_name}={value} is outside the plausible range "
                    f"{lo}-{hi} for {category} {row['metric']} - "
                    f"check for a unit error"
                )


def write_import_csvs(systems, sources, measurements):
    """Write CSVs whose columns exactly match the MySQL tables.

    IDs are assigned explicitly here rather than left to AUTO_INCREMENT so the
    measurement rows can carry real foreign keys, which is what allows the import
    to be done by hand in MySQL Workbench.

    The files are numbered because import order matters: measurement holds
    foreign keys into the other two, so importing it first fails.
    """
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)

    sources = sources.copy()
    sources.insert(0, "source_id", range(1, len(sources) + 1))
    source_ids = dict(zip(sources["source_key"], sources["source_id"]))

    systems = systems.copy()
    systems.insert(0, "system_id", range(1, len(systems) + 1))
    system_ids = dict(zip(systems["name"], systems["system_id"]))

    measurements = measurements.copy()
    measurements.insert(0, "measurement_id", range(1, len(measurements) + 1))
    measurements["system_id"] = measurements["system_name"].map(system_ids)
    measurements["source_id"] = measurements["source_key"].map(source_ids)

    sources.drop(columns=["source_key"]).to_csv(
        IMPORT_DIR / "1_source.csv", index=False)
    systems.to_csv(IMPORT_DIR / "2_propulsion_system.csv", index=False)
    measurements[[
        "measurement_id", "system_id", "metric", "value_low", "value_high",
        "unit", "source_id", "page", "quoted_text", "note",
    ]].to_csv(IMPORT_DIR / "3_measurement.csv", index=False)

    print(f"  import files written to {IMPORT_DIR.name}/ - import in numbered order")


def main():
    # index_col=False always: in project 1 a file with one more data field than
    # header fields caused pandas to silently promote column 0 to an index and
    # shift every column left. Nothing errored; the file just matched no rows.
    systems = pd.read_csv(RAW_DIR / "systems.csv", index_col=False)
    sources = pd.read_csv(RAW_DIR / "sources.csv", index_col=False)
    measurements = pd.read_csv(RAW_DIR / "measurements.csv", index_col=False)

    validate_measurements(
        measurements,
        known_sources=set(sources["source_key"]),
        known_systems=set(systems["name"]),
    )
    validate_physics(measurements, systems)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    systems.to_csv(PROCESSED_DIR / "systems.csv", index=False)
    sources.to_csv(PROCESSED_DIR / "sources.csv", index=False)
    measurements.to_csv(PROCESSED_DIR / "measurements.csv", index=False)

    write_import_csvs(systems, sources, measurements)

    print(f"  validated {len(measurements)} measurements across "
          f"{len(systems)} systems from {len(sources)} sources")

    covered = set(measurements["system_name"])
    missing = [n for n in systems["name"] if n not in covered]
    if missing:
        print(f"  no measurements yet for {len(missing)}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
