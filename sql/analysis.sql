-- Spacecraft Propulsion Systems 2025 -- analysis queries
--
-- These are kept as readable SQL rather than being buried in Python because they
-- are part of the argument, not just plumbing. docs/sql-primer.md walks through
-- each one. src/analyze.py runs them and writes the results to output/queries/.


-- 1. PROVENANCE VIEW
-- Every measurement with the engine it describes and the document it came from.
-- This is the query that makes the dataset defensible: any number on any chart
-- can be traced from here to a page and a quoted sentence.
--
-- Three tables need two joins. In general, joining n tables takes n-1 joins.
SELECT s.name, s.category, s.maturity, m.metric,
       m.value_low, m.value_high, m.unit,
       src.citation, m.page, m.quoted_text
FROM measurement m
JOIN propulsion_system s ON s.system_id = m.system_id
JOIN source src          ON src.source_id = m.source_id
ORDER BY s.category, s.name, m.metric;


-- 2. SPECIFIC IMPULSE, ALL SYSTEMS  (output page 1)
-- The only metric present for every system -- which is exactly why the original
-- project ranked on it, and exactly why that ranking misleads. Maturity is
-- selected here so the chart can colour by it: this list must never be read as
-- a straight ranking.
SELECT s.name, s.category, s.maturity, s.flown,
       MIN(m.value_low)  AS isp_low,
       MAX(m.value_high) AS isp_high
FROM propulsion_system s
JOIN measurement m ON m.system_id = s.system_id
WHERE m.metric = 'isp'
GROUP BY s.name, s.category, s.maturity, s.flown
ORDER BY isp_high DESC;


-- 3. WHERE SOURCES DISAGREE
-- More than one published figure for the same system and metric. This is a
-- finding, not an error: the schema was built to represent disagreement rather
-- than force a choice. HAVING filters on the aggregate, which is why it cannot
-- be written as WHERE -- WHERE runs before grouping, HAVING after.
SELECT s.name, m.metric,
       COUNT(*)          AS n_sources,
       MIN(m.value_low)  AS lowest,
       MAX(m.value_high) AS highest
FROM measurement m
JOIN propulsion_system s ON s.system_id = m.system_id
GROUP BY s.name, m.metric
HAVING COUNT(*) > 1
ORDER BY s.name, m.metric;


-- 4. COVERAGE -- which systems lack which metrics, and why
-- LEFT JOIN is essential here. A plain JOIN returns only rows matching on both
-- sides, so any system with no measurements at all would vanish -- and those are
-- precisely the rows this query exists to find. DRACO should appear with zeros.
SELECT s.name, s.category, s.maturity,
       SUM(m.metric = 'isp')         AS has_isp,
       SUM(m.metric = 'thrust')      AS has_thrust,
       SUM(m.metric = 'engine_mass') AS has_mass,
       SUM(m.metric = 'input_power') AS has_power
FROM propulsion_system s
LEFT JOIN measurement m ON m.system_id = s.system_id
GROUP BY s.name, s.category, s.maturity
ORDER BY s.category, s.name;


-- 5. THRUST-TO-WEIGHT  (output page 2)
-- A self-join: the same table joined to itself twice under different aliases, to
-- put thrust and mass -- stored as separate rows -- side by side in one row.
--
-- Note how the bounds pair inversely. The worst case is the LEAST thrust over the
-- GREATEST mass, so tw_low divides t.value_low by m.value_high. Pairing low with
-- low would understate the spread.
--
-- Only systems having BOTH thrust and mass appear. The join does the filtering:
-- a system missing either simply produces no row. That is 6 of 15 systems.
SELECT s.name, s.category, s.maturity,
       t.value_low  / (m.value_high * 9.80665) AS tw_low,
       t.value_high / (m.value_low  * 9.80665) AS tw_high,
       CASE WHEN t.value_low / (m.value_high * 9.80665) > 1
            THEN 'can lift off Earth'
            ELSE 'cannot lift off Earth' END   AS launch_capable
FROM propulsion_system s
JOIN measurement t ON t.system_id = s.system_id AND t.metric = 'thrust'
JOIN measurement m ON m.system_id = s.system_id AND m.metric = 'engine_mass'
ORDER BY tw_high DESC;


-- 6. ELECTRIC: POWER AGAINST THRUST  (output page 3)
-- Electric propulsion's real constraint is available power, not efficiency.
SELECT s.name,
       p.value_low  AS power_low_kw,
       p.value_high AS power_high_kw,
       t.value_low  AS thrust_low_n,
       t.value_high AS thrust_high_n
FROM propulsion_system s
JOIN measurement p ON p.system_id = s.system_id AND p.metric = 'input_power'
JOIN measurement t ON t.system_id = s.system_id AND t.metric = 'thrust'
WHERE s.category = 'electric'
ORDER BY p.value_high;


-- 7. CATEGORY SUMMARY -- the shape of the answer
-- What each category spans on specific impulse, and how much of it is real.
SELECT s.category,
       COUNT(DISTINCT s.system_id)                      AS n_systems,
       SUM(s.flown = 1) / COUNT(DISTINCT s.system_id)   AS share_flown,
       MIN(m.value_low)                                 AS isp_low,
       MAX(m.value_high)                                AS isp_high
FROM propulsion_system s
LEFT JOIN measurement m ON m.system_id = s.system_id AND m.metric = 'isp'
GROUP BY s.category
ORDER BY s.category;
