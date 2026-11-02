PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    records_found INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS truth_facts (
    fact_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    claim TEXT NOT NULL,
    value_json TEXT,
    evidence_sources_json TEXT NOT NULL,
    allowed_statement TEXT,
    forbidden_statements_json TEXT
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_key TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    path TEXT NOT NULL,
    exists_on_disk INTEGER NOT NULL,
    required INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    external_job_id TEXT,
    company TEXT NOT NULL,
    job_title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    location TEXT,
    country TEXT,
    work_mode TEXT,
    salary_min REAL,
    salary_max REAL,
    currency TEXT,
    job_url TEXT,
    source_url TEXT,
    date_found TEXT NOT NULL,
    date_posted TEXT,
    description TEXT,
    requirements_json TEXT,
    duplicate_hash TEXT NOT NULL,
    canonical_job_id INTEGER,
    is_canonical INTEGER NOT NULL DEFAULT 1,
    raw_json TEXT NOT NULL,
    FOREIGN KEY(canonical_job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS job_duplicates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    canonical_job_id INTEGER NOT NULL,
    duplicate_job_id INTEGER NOT NULL,
    duplicate_hash TEXT NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY(canonical_job_id) REFERENCES jobs(id),
    FOREIGN KEY(duplicate_job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS job_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    score_version TEXT NOT NULL,
    fit_score INTEGER NOT NULL,
    fit_category TEXT NOT NULL,
    rejected INTEGER NOT NULL,
    rejection_reason TEXT,
    factor_scores_json TEXT NOT NULL,
    explanation TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    resume_used TEXT,
    application_status TEXT NOT NULL,
    application_date TEXT,
    application_method TEXT NOT NULL,
    sponsorship_status TEXT,
    notes TEXT,
    strategy_json TEXT NOT NULL,
    submit_allowed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS screening_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    application_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    support_status TEXT NOT NULL,
    answer_text TEXT,
    safe_response TEXT,
    facts_used_json TEXT NOT NULL,
    evidence_sources_json TEXT NOT NULL,
    approval_required INTEGER NOT NULL,
    reason TEXT,
    FOREIGN KEY(application_id) REFERENCES applications(id),
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS approval_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    job_id INTEGER,
    application_id INTEGER,
    question TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL,
    metadata_json TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id),
    FOREIGN KEY(application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT
);

