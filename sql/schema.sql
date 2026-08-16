-- Spacecraft Propulsion Systems 2025 -- schema
--
-- Three tables, because three different things are being recorded:
--   propulsion_system  what is being compared     (15 rows, one per engine)
--   source             where figures came from    (one row per document)
--   measurement        one published figure       (many rows per system)
--
-- Project 1 used a single long-format table because IPEDS is one authoritative
-- source. Here, several sources publish different numbers for the same engine,
-- so the schema has to keep "what was measured" separate from "who said so".
--
-- NAMING NOTE: the natural name for the middle table is `system`, but SYSTEM is
-- a reserved word in MySQL 8.0 and later. Using it requires backtick-quoting in
-- every query forever, including inside Power BI. Renaming the table once is
-- cheaper than escaping it everywhere.

DROP TABLE IF EXISTS measurement;
DROP TABLE IF EXISTS propulsion_system;
DROP TABLE IF EXISTS source;


-- Bibliography. source_type records how far the source can be trusted:
-- tier 1 is peer-reviewed or agency-published, tier 2 is a manufacturer
-- datasheet (primary, but promotional). Aggregators such as Wikipedia are
-- never cited here -- they are used only to locate a tier 1/2 source.
CREATE TABLE source (
    source_id    INT PRIMARY KEY,
    citation     VARCHAR(500) NOT NULL,
    authors      VARCHAR(300),
    year         SMALLINT,
    publisher    VARCHAR(200),
    source_type  ENUM('tier1_peer_reviewed', 'tier1_agency', 'tier2_vendor') NOT NULL,
    url          VARCHAR(500),
    local_file   VARCHAR(200)
);


-- The 15 systems being compared.
--
-- maturity is assigned, not measured, which is why it lives here rather than in
-- measurement -- it carries no citation of its own.
--   proven      hardware built and fired; figures are measured
--   prototype   funded, hardware not yet complete; figures are design targets
--   theoretical physics estimate only, no hardware
--
-- flown is separate from maturity because 'proven' deliberately merges
-- flight-proven and ground-tested hardware. Both have measured data and belong
-- on a chart together, but only one has flight heritage. No nuclear system in
-- this dataset has ever flown.
CREATE TABLE propulsion_system (
    system_id    INT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    category     ENUM('chemical', 'electric', 'nuclear') NOT NULL,
    subtype      VARCHAR(60) NOT NULL,
    role         VARCHAR(60) NOT NULL,
    propellant   VARCHAR(60),
    maturity     ENUM('proven', 'prototype', 'theoretical') NOT NULL,
    flown        BOOLEAN NOT NULL DEFAULT FALSE
);


-- One row per published figure.
--
-- value_low and value_high rather than a single value: sources publish ranges,
-- and collapsing a range to its maximum is the exact defect that corrupted the
-- original dataset. A single-valued source is stored with low = high.
--
-- page and quoted_text make every number defensible -- any cell can be traced
-- back to the sentence it came from.
CREATE TABLE measurement (
    measurement_id INT PRIMARY KEY,
    system_id      INT NOT NULL,
    metric         ENUM('isp', 'thrust', 'engine_mass', 'input_power') NOT NULL,
    value_low      DOUBLE NOT NULL,
    value_high     DOUBLE NOT NULL,
    unit           VARCHAR(20) NOT NULL,
    source_id      INT NOT NULL,
    -- page holds locations like "441-442, Table 9-9" and quoted_text holds whole
    -- table rows, so both need real room. note carries the adjudication reasoning
    -- - which operating point was chosen, which variant, what was excluded and
    -- why - and that runs long by design. Sized from the data, not guessed:
    -- MySQL in strict mode REJECTS an over-length row rather than truncating it,
    -- so an undersized column loses data silently at import time.
    page           VARCHAR(60),
    quoted_text    VARCHAR(1000),
    note           VARCHAR(1000),
    CONSTRAINT fk_meas_system FOREIGN KEY (system_id)
        REFERENCES propulsion_system(system_id),
    CONSTRAINT fk_meas_source FOREIGN KEY (source_id)
        REFERENCES source(source_id),
    CONSTRAINT chk_range CHECK (value_low <= value_high)
);

CREATE INDEX idx_meas_system_metric ON measurement (system_id, metric);
