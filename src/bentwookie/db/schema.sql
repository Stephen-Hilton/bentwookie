-- BentWookie v2 Database Schema

-- Projects table
CREATE TABLE IF NOT EXISTS project (
    prjid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjname TEXT NOT NULL UNIQUE,
    prjversion TEXT DEFAULT 'poc',
    prjpriority INTEGER DEFAULT 5,
    prjphase TEXT DEFAULT 'dev',
    prjdesc TEXT,
    prjtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Requests table
CREATE TABLE IF NOT EXISTS request (
    reqid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    reqname TEXT NOT NULL,
    reqtype TEXT DEFAULT 'new_feature',
    reqstatus TEXT DEFAULT 'tbd',
    reqphase TEXT DEFAULT 'plan',
    reqprompt TEXT NOT NULL,
    reqpriority INTEGER DEFAULT 5,
    reqcodedir TEXT,
    reqdocpath TEXT,
    reqtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Infrastructure table
CREATE TABLE IF NOT EXISTS infrastructure (
    infid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    infprovider TEXT DEFAULT 'local',
    inftype TEXT NOT NULL,
    infval TEXT,
    infnote TEXT,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Learnings table
CREATE TABLE IF NOT EXISTS learning (
    lrnid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    lrndesc TEXT NOT NULL,
    lrntouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_request_status ON request(reqstatus);
CREATE INDEX IF NOT EXISTS idx_request_phase ON request(reqphase);
CREATE INDEX IF NOT EXISTS idx_request_prjid ON request(prjid);
CREATE INDEX IF NOT EXISTS idx_infrastructure_prjid ON infrastructure(prjid);
CREATE INDEX IF NOT EXISTS idx_learning_prjid ON learning(prjid);
