-- ClinAssess database schema (SQLite).
--
-- The database is never written to disk in plaintext. It runs in memory
-- after login. On every commit it is serialized and written to
-- clinassess.db.enc, encrypted with AES-256-GCM under the data key (DEK).
-- See clinassess/database.py.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per client.
CREATE TABLE IF NOT EXISTS clients (
    id            INTEGER PRIMARY KEY,
    ref_code      TEXT NOT NULL UNIQUE,     -- random non-PHI reference (e.g. C-7F3A2B)
    last_name     TEXT NOT NULL,
    first_name    TEXT NOT NULL,
    dob           TEXT NOT NULL,            -- ISO 8601 date (YYYY-MM-DD)
    grade         TEXT,                     -- school grade, optional
    flow          TEXT NOT NULL CHECK (flow IN ('A', 'B')),
    asrs_enabled  INTEGER NOT NULL DEFAULT 0 CHECK (asrs_enabled IN (0, 1)),
    created_at    TEXT NOT NULL,
    created_by    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    updated_by    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients (last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_clients_dob  ON clients (dob);

-- One row per administered instrument (or interview-notes entry).
CREATE TABLE IF NOT EXISTS assessments (
    id               INTEGER PRIMARY KEY,
    client_id        INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    instrument       TEXT NOT NULL,          -- key from clinassess/instruments.py
    variant          TEXT NOT NULL DEFAULT '',  -- e.g. parent / teacher / self
    administered_on  TEXT NOT NULL,          -- ISO 8601 date
    responses_json   TEXT NOT NULL,          -- raw item responses or entered scores
    scores_json      TEXT NOT NULL,          -- computed result (see scoring/base.py)
    scoring_version  TEXT NOT NULL,          -- version of the scoring rule applied
    created_at       TEXT NOT NULL,
    created_by       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    updated_by       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assessments_client ON assessments (client_id);

-- Report drafts. Every save creates a new version; old versions are kept
-- so the history of edits is preserved and the auto-generated text can be
-- restored.
CREATE TABLE IF NOT EXISTS report_versions (
    id             INTEGER PRIMARY KEY,
    client_id      INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    version_no     INTEGER NOT NULL,
    template       TEXT NOT NULL CHECK (template IN ('child', 'adult')),
    source         TEXT NOT NULL CHECK (source IN ('auto', 'edited', 'reverted')),
    sections_json  TEXT NOT NULL,            -- {section_key: text}
    created_at     TEXT NOT NULL,
    created_by     TEXT NOT NULL,
    UNIQUE (client_id, version_no)
);

-- Audit trail (mirrors the encrypted audit.log.enc file, which also
-- records pre-login events such as failed logins).
-- details_json holds field NAMES that changed, never field values, so
-- deleted PHI does not survive in the audit trail.
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY,
    ts           TEXT NOT NULL,              -- UTC ISO 8601
    username     TEXT NOT NULL,
    action       TEXT NOT NULL,
    client_ref   TEXT,                       -- clients.ref_code (not a name)
    entity       TEXT,
    entity_id    INTEGER,
    details_json TEXT NOT NULL DEFAULT '{}',
    file_seq     INTEGER                     -- sequence number in audit.log.enc
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log (ts);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
