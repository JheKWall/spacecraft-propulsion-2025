"""Read from MySQL, derive metrics, and produce the findings.

Handling of multiple sources for one figure
-------------------------------------------
A system can have more than one published value for the same metric - the BHT-600
has two input_power ranges from two citable sources. For charting, this module
takes the UNION of the published ranges (lowest low, highest high) and flags the
system as disputed, rather than picking a winner.

The reasoning: choosing one source would hide a real disagreement, and averaging
would invent a figure nobody published. The union is the honest statement -
"published values span this range" - and the disputed flag keeps the fact of the
disagreement visible instead of dissolving it into the number.
"""
import mysql.connector
import pandas as pd

from config import DB, PROCESSED_DIR, QUERIES_DIR, db_password
from metrics import thrust_to_weight

METRICS = ["isp", "thrust", "engine_mass", "input_power"]


def query(conn, sql):
    """Run SQL and return a DataFrame.

    Built from a cursor rather than pd.read_sql because pandas only formally
    supports SQLAlchemy connectables and warns on a raw mysql-connector object.
    The query works either way; this just keeps the output clean.
    """
    cur = conn.cursor()
    cur.execute(sql)
    columns = [c[0] for c in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=columns)


def fetch(conn):
    """One row per measurement, joined to its system and source."""
    return query(conn, """
        SELECT s.name, s.category, s.subtype, s.role, s.maturity, s.flown,
               m.metric, m.value_low, m.value_high, m.unit,
               src.citation, src.source_type, m.page, m.quoted_text, m.note
        FROM measurement m
        JOIN propulsion_system s ON s.system_id = m.system_id
        JOIN source src          ON src.source_id = m.source_id
    """)


def build_analysis(measurements, systems):
    """One row per system, metrics pivoted to columns, T/W derived."""
    # Union across sources: lowest low, highest high, plus a count so a
    # disagreement stays visible rather than being absorbed into the range.
    agg = (measurements
           .groupby(["name", "metric"])
           .agg(low=("value_low", "min"),
                high=("value_high", "max"),
                n_sources=("citation", "nunique"))
           .reset_index())

    rows = []
    for _, sysrow in systems.iterrows():
        name = sysrow["name"]
        sub = agg[agg["name"] == name].set_index("metric")

        row = {
            "name": name,
            "category": sysrow["category"],
            "subtype": sysrow["subtype"],
            "role": sysrow["role"],
            "maturity": sysrow["maturity"],
            "flown": bool(sysrow["flown"]),
        }

        for metric in METRICS:
            if metric in sub.index:
                row[f"{metric}_low"] = sub.loc[metric, "low"]
                row[f"{metric}_high"] = sub.loc[metric, "high"]
                row[f"{metric}_n_sources"] = int(sub.loc[metric, "n_sources"])
                row[f"{metric}_disputed"] = sub.loc[metric, "n_sources"] > 1
            else:
                row[f"{metric}_low"] = None
                row[f"{metric}_high"] = None
                row[f"{metric}_n_sources"] = 0
                row[f"{metric}_disputed"] = False

        tw_low, tw_high = thrust_to_weight(
            row["thrust_low"], row["thrust_high"],
            row["engine_mass_low"], row["engine_mass_high"])
        row["tw_low"] = tw_low
        row["tw_high"] = tw_high
        row["launch_capable"] = None if tw_low is None else bool(tw_low > 1.0)

        rows.append(row)

    return pd.DataFrame(rows)


def report(analysis, measurements):
    """Print the findings that feed the writeup."""
    line = "=" * 72

    print(f"\n{line}\nFINDING 1 -- who can leave the ground\n{line}")
    computable = analysis[analysis["tw_low"].notna()]
    print(f"  Thrust-to-weight is computable for {len(computable)} of "
          f"{len(analysis)} systems.")
    print(f"  The limiting factor is engine mass: {analysis['thrust_low'].notna().sum()} "
          f"systems have thrust, only {analysis['engine_mass_low'].notna().sum()} "
          f"have a citable mass.\n")
    for _, r in computable.sort_values("tw_high", ascending=False).iterrows():
        verdict = "CAN lift off Earth" if r["launch_capable"] else "cannot lift off"
        print(f"    {r['name']:<24} {r['category']:<9} "
              f"T/W {r['tw_low']:>10.4f} - {r['tw_high']:<10.4f} {verdict}")

    print(f"\n{line}\nFINDING 2 -- specific impulse alone is a misleading ranking\n{line}")
    top = analysis[analysis["isp_high"].notna()].sort_values(
        "isp_high", ascending=False).head(4)
    for _, r in top.iterrows():
        print(f"    {r['name']:<24} Isp up to {r['isp_high']:>12,.0f} s   "
              f"({r['maturity']}, {'flown' if r['flown'] else 'never flown'})")
    theoretical_top = analysis[analysis["maturity"] == "theoretical"]["isp_high"].max()
    proven_top = analysis[analysis["maturity"] == "proven"]["isp_high"].max()
    print(f"\n  The highest Isp belongs to hardware that does not exist: "
          f"{theoretical_top:,.0f} s theoretical")
    print(f"  against {proven_top:,.0f} s for anything ever built -- a factor of "
          f"{theoretical_top / proven_top:,.0f}.")

    print(f"\n{line}\nFINDING 3 -- maturity and flight heritage\n{line}")
    for category in ["chemical", "electric", "nuclear"]:
        sub = analysis[analysis["category"] == category]
        print(f"    {category:<9} {len(sub)} systems   "
              f"{sub['flown'].sum()} flown   "
              f"{(sub['maturity'] == 'theoretical').sum()} theoretical")
    never_flown = analysis[~analysis["flown"]]
    print(f"\n  {len(never_flown)} of {len(analysis)} systems have never flown, "
          f"and every one of them is nuclear.")

    print(f"\n{line}\nFINDING 4 -- where sources disagree\n{line}")
    disputed = False
    for metric in METRICS:
        col = f"{metric}_disputed"
        for _, r in analysis[analysis[col]].iterrows():
            disputed = True
            print(f"    {r['name']} / {metric}: {r[f'{metric}_n_sources']} sources, "
                  f"union {r[f'{metric}_low']:g} - {r[f'{metric}_high']:g}")
    if not disputed:
        print("    No system has conflicting published values for a metric.")

    print(f"\n{line}\nFINDING 5 -- source base\n{line}")
    by_type = measurements.groupby("source_type")["citation"].nunique()
    for source_type, n in by_type.items():
        print(f"    {source_type:<22} {n} documents")
    print(f"    {'':<22} {measurements['citation'].nunique()} total, "
          f"{len(measurements)} cited figures")
    print()


def main():
    conn = mysql.connector.connect(**DB, password=db_password())
    measurements = fetch(conn)
    systems = query(conn, "SELECT * FROM propulsion_system ORDER BY system_id")
    conn.close()

    analysis = build_analysis(measurements, systems)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    analysis.to_csv(PROCESSED_DIR / "analysis.csv", index=False)
    measurements.to_csv(QUERIES_DIR / "provenance.csv", index=False)

    if len(analysis) != len(systems):
        raise RuntimeError(
            f"analysis has {len(analysis)} rows, expected {len(systems)}")

    report(analysis, measurements)
    print(f"  wrote {PROCESSED_DIR / 'analysis.csv'} ({len(analysis)} rows)")


if __name__ == "__main__":
    main()
