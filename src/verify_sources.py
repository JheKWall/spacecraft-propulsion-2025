"""Generate the human verification checklist, and refuse to ship untraceable figures.

An AI performed the bulk of this collection and cannot verify its own claims.
This script exists because of that, not in spite of it. It does two things:

  1. Fails loudly on any figure that cannot be checked at all - no verbatim
     quote, or no page/URL to find it in. Such a row does not belong in the
     dataset, and no amount of downstream care compensates for it.

  2. Emits output/verification_checklist.md: every figure with its quote and
     location, grouped by source so a reader opens each document once rather
     than once per figure.

It also runs physics bounds, which catch what a citation check cannot. A
correctly quoted number in the wrong unit passes provenance and is still wrong.
"""
import pandas as pd

from config import (G0, OUTPUT_DIR, PROCESSED_DIR, RAW_DIR, SANITY_BOUNDS,
                    SPEED_OF_LIGHT)


class UntraceableFigure(Exception):
    """A measurement that cannot be checked against its source."""


def check_traceable(measurements, sources):
    """Every figure must have a quote and a way to find it."""
    by_key = sources.set_index("source_key")
    problems = []

    for i, row in measurements.iterrows():
        where = f"row {i} ({row['system_name']}/{row['metric']})"
        src = by_key.loc[row["source_key"]]

        quote = row.get("quoted_text")
        if pd.isna(quote) or not str(quote).strip():
            problems.append(f"{where}: no verbatim quote")

        has_local = not pd.isna(src["local_file"]) and str(src["local_file"]).strip()
        has_url = not pd.isna(src["url"]) and str(src["url"]).strip()
        has_page = not pd.isna(row["page"]) and str(row["page"]).strip()

        if has_local and not has_page:
            problems.append(f"{where}: local PDF source with no page number")
        if not has_local and not has_url:
            problems.append(f"{where}: no local file and no URL - unfindable")

    if problems:
        raise UntraceableFigure(
            "figures that cannot be verified:\n  " + "\n  ".join(problems))


def check_physics(measurements, systems):
    """Bounds that hold regardless of what any source says."""
    categories = dict(zip(systems["name"], systems["category"]))
    problems = []

    for i, row in measurements.iterrows():
        where = f"row {i} ({row['system_name']}/{row['metric']})"

        if row["metric"] == "isp":
            if row["value_high"] * G0 > SPEED_OF_LIGHT:
                problems.append(f"{where}: exhaust velocity exceeds c")
            bounds = SANITY_BOUNDS.get((categories[row["system_name"]], "isp"))
            if bounds and not (bounds[0] <= row["value_low"] <= bounds[1]):
                problems.append(
                    f"{where}: {row['value_low']} outside plausible {bounds}")

    if problems:
        raise UntraceableFigure(
            "physics checks failed:\n  " + "\n  ".join(problems))


def build_checklist(measurements, sources):
    by_key = sources.set_index("source_key")
    lines = [
        "# Verification Checklist",
        "",
        "Every figure in this dataset, with the sentence it came from and where to find it.",
        "",
        "**An AI performed the bulk of this collection and cannot verify its own claims.**",
        "This checklist exists so a human can. Figures are grouped by source, so each",
        "document is opened once rather than once per figure.",
        "",
        "Tick a box once you have seen the quoted text in the source with your own eyes.",
        "Anything left unticked is an unverified number.",
        "",
        "## What to look for",
        "",
        "The realistic failure mode is not invention. It is a figure that is correctly",
        "quoted but describes something slightly different: a sea-level value where the",
        "dataset expects vacuum, one end of a range recorded as though it were the whole,",
        "a different engine variant, or a different operating point. Five such near-misses",
        "were caught during collection and are listed in `docs/data-collection.md` section 6.",
        "",
        "---",
        "",
    ]

    total = 0
    for source_key, group in measurements.groupby("source_key", sort=True):
        src = by_key.loc[source_key]
        has_local = not pd.isna(src["local_file"]) and str(src["local_file"]).strip()

        lines.append(f"## {src['citation']}")
        lines.append("")
        lines.append(f"- **Tier:** `{src['source_type']}`")
        if has_local:
            lines.append(f"- **Local file:** `{src['local_file']}`")
            lines.append("- **Cross-checked independently:** yes — this document was "
                         "re-read by a different model family, cold (see "
                         "`docs/data-collection.md` §9)")
        else:
            lines.append(f"- **URL:** {src['url']}")
            lines.append("- **Cross-checked independently:** **no — hand-check only.** "
                         "Externally sourced; not covered by the independent "
                         "re-extraction, so it must not inherit its confidence.")
        lines.append("")

        for _, r in group.iterrows():
            total += 1
            value = (f"{r['value_low']:g}" if r["value_low"] == r["value_high"]
                     else f"{r['value_low']:g} – {r['value_high']:g}")
            lines.append(f"- [ ] **{r['system_name']} · {r['metric']}** = "
                         f"{value} {r['unit']}")
            page = "" if pd.isna(r["page"]) else str(r["page"])
            if page:
                lines.append(f"  - Location: p. {page}")
            lines.append(f"  - Quote: *\"{r['quoted_text']}\"*")
            if not pd.isna(r["note"]) and str(r["note"]).strip():
                lines.append(f"  - Note: {r['note']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(f"**{total} figures across "
                 f"{measurements['source_key'].nunique()} sources.**")
    lines.append("")
    return "\n".join(lines)


def main():
    measurements = pd.read_csv(RAW_DIR / "measurements.csv", index_col=False)
    sources = pd.read_csv(RAW_DIR / "sources.csv", index_col=False)
    systems = pd.read_csv(RAW_DIR / "systems.csv", index_col=False)

    check_traceable(measurements, sources)
    check_physics(measurements, systems)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / "verification_checklist.md"
    target.write_text(build_checklist(measurements, sources), encoding="utf-8")

    local = sources[sources["local_file"].notna()
                    & (sources["local_file"].astype(str).str.strip() != "")]
    n_local = measurements["source_key"].isin(local["source_key"]).sum()

    print(f"  all {len(measurements)} figures are traceable and pass physics bounds")
    print(f"  {n_local} from local PDFs (independently cross-checked)")
    print(f"  {len(measurements) - n_local} externally sourced (hand-check only)")
    print(f"  wrote {target}")


if __name__ == "__main__":
    main()
