-- BentWookie v2 Database Schema

-- Projects table
CREATE TABLE IF NOT EXISTS project (
    prjid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjname TEXT NOT NULL UNIQUE,
    prjversion TEXT DEFAULT 'poc',
    prjpriority INTEGER DEFAULT 5,
    prjphase TEXT DEFAULT 'dev',
    prjdesc TEXT,
    prjcodedir TEXT,
    prjprompt TEXT,
    prjclaudemd TEXT,
    prjmodel TEXT,
    prjcommitenabled INTEGER DEFAULT NULL,
    prjcommitbranchmode TEXT,
    prjcommitbranchname TEXT,
    prjtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migration for existing databases:
-- ALTER TABLE project ADD COLUMN prjcodedir TEXT;
-- ALTER TABLE project ADD COLUMN prjprompt TEXT;
-- ALTER TABLE project ADD COLUMN prjclaudemd TEXT;
-- ALTER TABLE project ADD COLUMN prjmodel TEXT;
-- ALTER TABLE project ADD COLUMN prjcommitenabled INTEGER DEFAULT NULL;
-- ALTER TABLE project ADD COLUMN prjcommitbranchmode TEXT;
-- ALTER TABLE project ADD COLUMN prjcommitbranchname TEXT;

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
    reqplanpath TEXT,
    reqtestplanpath TEXT,
    reqtestretries INTEGER DEFAULT 0,
    reqerror TEXT,
    reqcommitenabled INTEGER DEFAULT 1,
    reqcommitbranch TEXT,
    reqtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Migration for existing databases:
-- ALTER TABLE request ADD COLUMN reqplanpath TEXT;
-- ALTER TABLE request ADD COLUMN reqtestplanpath TEXT;
-- ALTER TABLE request ADD COLUMN reqtestretries INTEGER DEFAULT 0;
-- ALTER TABLE request ADD COLUMN reqerror TEXT;
-- ALTER TABLE request ADD COLUMN reqcommitenabled INTEGER DEFAULT 1;
-- ALTER TABLE request ADD COLUMN reqcommitbranch TEXT;

-- Infrastructure table (project-level)
CREATE TABLE IF NOT EXISTS infrastructure (
    infid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    infprovider TEXT DEFAULT 'local',
    inftype TEXT NOT NULL,
    infval TEXT,
    infnote TEXT,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Request infrastructure overrides (request-level)
CREATE TABLE IF NOT EXISTS request_infrastructure (
    rinfid INTEGER PRIMARY KEY AUTOINCREMENT,
    reqid INTEGER NOT NULL,
    inftype TEXT NOT NULL,
    infprovider TEXT DEFAULT 'local',
    infval TEXT,
    infnote TEXT,
    FOREIGN KEY (reqid) REFERENCES request(reqid)
);

-- Learnings table
CREATE TABLE IF NOT EXISTS learning (
    lrnid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    lrndesc TEXT NOT NULL,
    lrntouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid)
);

-- Infrastructure options table (wizard selectable options)
CREATE TABLE IF NOT EXISTS infra_option (
    optid INTEGER PRIMARY KEY AUTOINCREMENT,
    opttype TEXT NOT NULL,
    optname TEXT NOT NULL,
    optprovider TEXT DEFAULT 'local',
    optsortorder INTEGER DEFAULT 0,
    UNIQUE(opttype, optname)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_request_status ON request(reqstatus);
CREATE INDEX IF NOT EXISTS idx_request_phase ON request(reqphase);
CREATE INDEX IF NOT EXISTS idx_request_prjid ON request(prjid);
CREATE INDEX IF NOT EXISTS idx_infrastructure_prjid ON infrastructure(prjid);
CREATE INDEX IF NOT EXISTS idx_request_infrastructure_reqid ON request_infrastructure(reqid);
CREATE INDEX IF NOT EXISTS idx_learning_prjid ON learning(prjid);
