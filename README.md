# Spacecraft Propulsion Systems 2025

**Which mission role is each category of spacecraft propulsion best suited for?**

A comparison of 15 propulsion systems — chemical, electric, and nuclear — on specific impulse,
thrust, input power, and thrust-to-weight ratio, distinguishing flight-proven hardware from
prototype and theoretical concepts.

Every figure in the dataset carries its own citation, page number, and a verbatim quote of the
sentence it came from.

---

## Findings

**Nothing is best in the abstract. Only best for a job.**

| Category | Best suited to | Evidence |
|---|---|---|
| **Chemical** | Launch and high-thrust roles — which nothing else can perform at all | The only category with thrust-to-weight above 1 |
| **Electric** | Station-keeping and long-duration deep-space work, where time is available | Beats every chemical engine on efficiency; produces at most a quarter of a newton |
| **Nuclear** | A high-efficiency, high-thrust middle that would suit upper stages — on paper | Nothing in the category has ever flown |

Four results worth stating separately:

**Ranking on specific impulse alone is misleading, and that was the original project's method.**
The two highest-Isp systems in the dataset have never been built. The theoretical maximum is
**2,370 times** the best figure achieved by any hardware ever fired.

**"Chemical wins launch" is too coarse.** The MR-103J is a flight-proven chemical thruster with a
thrust-to-weight ratio of 0.05–0.33 — it cannot lift its own weight. Chemical propulsion is the
only category that *can* launch, but only part of it does.

**Thrust-to-weight is computable for just 8 of 15 systems.** Twelve have a citable thrust; only
eight have a citable engine mass. The metric that answers "can this leave the ground" is the one
the literature is least willing to supply.

**No nuclear system in this dataset has ever flown**, and DRACO — the only one that was being
built to fly — was cancelled in 2025 without publishing a single performance figure at any source
tier. Its empty row is part of the answer.

---

## Charts

| | |
|---|---|
| `output/charts/01_all_systems_isp.png` | Specific impulse, all 15 systems, coloured by maturity — reproduces the original comparison |
| `output/charts/02_chemical_tw.png` | Chemical thrust-to-weight against the T/W = 1 threshold |
| `output/charts/03_electric_power_thrust.png` | Electric propulsion: power against thrust |
| `output/charts/04_nuclear_thrust_isp.png` | Nuclear, split by what was built and what was not |

---

## Data-quality findings

Two of these are results in their own right.

### A unit error in the primary source

The original class project drew its figures from Frisbee (2003), *Advanced Space Propulsion for
the 21st Century* (Journal of Propulsion and Power 19(6)). Its Table 3 gives antimatter
annihilation an exhaust velocity of 10⁸ km/s — **333 times the speed of light**.

The table's own conversion factor holds for its first three rows and fails for the last three, all
by exactly 1000×. The paper's own body text gives the correct figure — 10⁴ km/s, with the author's
own check that this is "3% of the speed of light" — so the paper contradicts itself, and the prose
is right.

**The original transcription was faithful. The error is upstream, in a peer-reviewed paper.** This
rebuild sidesteps it by reading specific impulse from the table's other column, which is
internally consistent.

It is also why `src/clean.py` asserts that no exhaust velocity exceeds *c*. A correctly quoted
figure from a reputable source can still be wrong, and no amount of provenance checking will
catch it — only physics will.

### Sources that disagree

Recorded rather than resolved by preference:

- **RS-25 dry mass** differs by 10% between NASA's own technical report (7,748 lb) and secondary
  sources (7,004 lb). The NASA figure is used, which moves the engine's thrust-to-weight from the
  commonly quoted ~73 to 61–66.
- **BHT-600 input power** has two citable and different ranges — 200–800 W in a NASA/Busek paper,
  300–800 W on Busek's datasheet. Both are stored, as two rows against two sources.
- **PPS-1350 nominal power** is given as 1500 W in a table and 1.35 kW in the facing body text of
  *the same book*. Neither was used; the in-flight throttle range, corroborated by an independent
  ESA/AIAA source, was.

Full detail in [`docs/data-collection.md`](docs/data-collection.md).

---

## Sources

There is no IPEDS equivalent for propulsion — no single authority publishing every figure on a
schedule. The substitute is a documented hierarchy plus a citation on every individual value.

| Tier | What it is | Citable as primary? |
|---|---|---|
| **1 — Authoritative** | Peer-reviewed papers; NASA/JPL/ESA technical reports (NTRS, TM, CR); Los Alamos reports | Yes |
| **2 — Primary vendor** | Manufacturer datasheets (Aerojet Rocketdyne / L3Harris, Busek, SpaceX) | Yes, recorded as vendor-sourced |
| **3 — Aggregator** | Wikipedia, Encyclopedia Astronautica, AI-generated encyclopedias | **No.** Used only to *locate* a Tier 1/2 source, which is then read and cited directly |

**40 cited figures from 15 documents:** 10 Tier 1 (8 agency, 2 peer-reviewed) and 5 Tier 2 vendor.

`sources.csv` declares 22 documents rather than 15. The other seven were read during collection
but no figure ultimately rests on them — in each case another source was cited for the same
system. They are kept rather than deleted: what was read and *not* used is part of the audit
trail, and deleting it would make the collection look tidier than it was. All seven are Tier 1,
and six carry a DOI or NTRS link.

The rule that does the real work is simpler than the hierarchy: **no verbatim quote, no row.** A
figure that cannot be traced to a sentence does not enter the dataset. That rule is enforced in
code by `src/verify_sources.py`, which refuses to run if any measurement lacks a quote or a
location.

---

## Verification

Most of this collection was performed by an AI, which cannot verify its own claims. Four
independent checks exist because of that:

| Check | Catches |
|---|---|
| [`output/verification_checklist.md`](output/verification_checklist.md) — every figure with its quote and page, grouped by source | Misquotation, wrong page, fabrication |
| Independent re-extraction by a different model family, prompted cold | Misread table, wrong row or column |
| Physics bounds in `src/clean.py` | **Unit errors** — which a citation check cannot catch, because the number really was published |
| Row-count assertions at every stage | Silent partial loads |

**Result of the cross-check:** all 5 figures drawn from local PDFs were confirmed exactly. It also
surfaced evidence the first pass had missed — the body-text passage proving the Frisbee table
error. **35 of 40 figures are hand-check-only** and are marked as such in the checklist; they
should not inherit the confidence of the cross-checked rows.

That last row of the table earned its place. Six measurements were silently rejected during the
database import for exceeding a column width — MySQL rejects an over-length row rather than
truncating it, and reports nothing. Only a row-count assertion caught it. Had it not, the analysis
would have run on 34 of 40 figures and produced entirely plausible, wrong results.

---

## Method

```
collect → clean → load → analyze → viz → excel_report
```

Collection is **manual and auditable**, not automated. `data/raw/measurements.csv` is hand-built,
one row per cited figure. The scripts validate and load; the collection is the research. That is
stated plainly rather than dressed up.

**Schema.** Three tables, because sources disagree and every figure needs its own citation:

```
propulsion_system   15 rows — what is being compared
source              22 rows — where figures came from
measurement         40 rows — one published figure, with page and quote
```

Values are stored as `value_low`/`value_high` ranges, never single numbers. Collapsing a published
range to its maximum is the defect that corrupted the original dataset, and the schema makes
repeating it impossible.

**Derived metrics** (thrust-to-weight) are computed in pandas and never stored, so every row in
`measurement` remains something a source actually published.

---

## Reproducing

Requires Python 3.14, MySQL 8.0+, and the packages in `requirements.txt`.

```bash
python src/clean.py            # validate raw CSVs, write import files
python src/verify_sources.py   # check traceability, write the checklist
```

Then create the database and import the three CSVs from `data/processed/import/` following
[`docs/workbench-import.md`](docs/workbench-import.md), and:

```bash
python src/verify_load.py      # confirm the import
python src/analyze.py          # findings and analysis.csv
python src/viz.py              # the four charts
python src/excel_report.py     # the workbook
python -m pytest tests/ -v     # 26 tests
```

---

## Limitations

- **Nuclear and chemical specific impulses rest on different bases.** Pewee's 865–901 s is *ideal
  vacuum* — calculated assuming infinite nozzle expansion and no losses. The RS-25's 452 s is
  delivered performance. The nuclear advantage is real; these numbers overstate it.
- **Frisbee (2003) is 22 years old**, and is still the only source for the theoretical concepts.
  Nothing more recent publishes comparable figures for them.
- **Vendor datasheets are promotional documents.** They are recorded as Tier 2 and flagged in the
  data.
- **Theoretical systems have one number and no engineering.** They appear on the specific-impulse
  chart and nowhere else, which is the honest treatment.
- **Electric thruster mass excludes the power processing unit**, solar arrays, and radiators, which
  dominate a real electric system. Electric thrust-to-weight is therefore flattered — though it is
  of order 10⁻⁴ either way, so no conclusion depends on it.
- **35 of 40 figures have not been independently re-extracted** and rest on a single reading of a
  single source.

---

## Documentation

| | |
|---|---|
| [`docs/data-collection.md`](docs/data-collection.md) | Source hierarchy, every judgement call, conflicts and how they were resolved |
| [`docs/sql-primer.md`](docs/sql-primer.md) | Foreign keys, joins, `LEFT JOIN`, `HAVING`, self-joins — worked on this schema |
| [`docs/mysql-setup.md`](docs/mysql-setup.md) | Database, scoped user, and the errors actually hit |
| [`docs/workbench-import.md`](docs/workbench-import.md) | Importing by hand, including a deliberate foreign-key failure |
| [`docs/pandas-walkthrough.md`](docs/pandas-walkthrough.md) | Long-to-wide, range arithmetic, why derived metrics are not stored |
| [`docs/powerbi-walkthrough.md`](docs/powerbi-walkthrough.md) | The dashboard |

---

## Background

This rebuilds a Database Management Systems class project that compared 30 propulsion methods on
specific impulse. The original dataset was lost; only a list of methods and figures survived,
which was traced back to a single 2003 paper with each published range collapsed to its maximum.

The reconstruction changes the question. The original statement asked for the "most cost-effective"
system — but no per-system cost figure exists in any consulted source, and none exists publicly
for the theoretical concepts. Rather than answer that badly, the study asks what each category is
*for*. See `Project Statement.txt`.
