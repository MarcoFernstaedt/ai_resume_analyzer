CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    remote_type TEXT,
    url TEXT NOT NULL,
    description TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    posted_date TEXT,
    scraped_at TEXT DEFAULT (datetime('now')),
    relevance_score REAL DEFAULT 0,
    status TEXT DEFAULT 'new',
    easy_apply INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cover_letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id),
    version INTEGER DEFAULT 1,
    content TEXT NOT NULL,
    generated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS application_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id),
    applied_at TEXT DEFAULT (datetime('now')),
    method TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_cover_letters_job ON cover_letters(job_id);
CREATE INDEX IF NOT EXISTS idx_applog_job ON application_log(job_id);
