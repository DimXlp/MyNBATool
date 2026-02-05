-- NBA 2K26 Database Schema v2
-- PostgreSQL Database with UUID support and team reference table

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS draft_picks CASCADE;
DROP TABLE IF EXISTS contracts CASCADE;
DROP TABLE IF EXISTS roster_players CASCADE;
DROP TABLE IF EXISTS standings CASCADE;
DROP TABLE IF EXISTS extraction_sources CASCADE;
DROP TABLE IF EXISTS teams CASCADE;

-- ==============================================================================
-- REFERENCE TABLE: teams
-- ==============================================================================
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(50) UNIQUE NOT NULL,
    abbreviation VARCHAR(3) UNIQUE NOT NULL,
    conference VARCHAR(10) NOT NULL CHECK (conference IN ('Eastern', 'Western')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert all 30 NBA teams
INSERT INTO teams (team_name, abbreviation, conference) VALUES
    ('Atlanta Hawks', 'ATL', 'Eastern'),
    ('Boston Celtics', 'BOS', 'Eastern'),
    ('Brooklyn Nets', 'BKN', 'Eastern'),
    ('Charlotte Hornets', 'CHA', 'Eastern'),
    ('Chicago Bulls', 'CHI', 'Eastern'),
    ('Cleveland Cavaliers', 'CLE', 'Eastern'),
    ('Detroit Pistons', 'DET', 'Eastern'),
    ('Indiana Pacers', 'IND', 'Eastern'),
    ('Miami Heat', 'MIA', 'Eastern'),
    ('Milwaukee Bucks', 'MIL', 'Eastern'),
    ('New York Knicks', 'NYK', 'Eastern'),
    ('Orlando Magic', 'ORL', 'Eastern'),
    ('Philadelphia 76ers', 'PHI', 'Eastern'),
    ('Toronto Raptors', 'TOR', 'Eastern'),
    ('Washington Wizards', 'WAS', 'Eastern'),
    ('Dallas Mavericks', 'DAL', 'Western'),
    ('Denver Nuggets', 'DEN', 'Western'),
    ('Golden State Warriors', 'GSW', 'Western'),
    ('Houston Rockets', 'HOU', 'Western'),
    ('Los Angeles Clippers', 'LAC', 'Western'),
    ('Los Angeles Lakers', 'LAL', 'Western'),
    ('Memphis Grizzlies', 'MEM', 'Western'),
    ('Minnesota Timberwolves', 'MIN', 'Western'),
    ('New Orleans Pelicans', 'NOP', 'Western'),
    ('Oklahoma City Thunder', 'OKC', 'Western'),
    ('Phoenix Suns', 'PHX', 'Western'),
    ('Portland Trail Blazers', 'POR', 'Western'),
    ('Sacramento Kings', 'SAC', 'Western'),
    ('San Antonio Spurs', 'SAS', 'Western'),
    ('Utah Jazz', 'UTA', 'Western');

-- ==============================================================================
-- TABLE: extraction_sources
-- ==============================================================================
CREATE TABLE extraction_sources (
    source_id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    file_type VARCHAR(50) NOT NULL, -- 'roster', 'contract', 'draft_picks', 'standings'
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ==============================================================================
-- TABLE: roster_players
-- ==============================================================================
CREATE TABLE roster_players (
    player_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team VARCHAR(50) NOT NULL, -- Kept for backward compatibility/quick queries
    position VARCHAR(5),
    age INTEGER,
    overall_rating INTEGER,
    delta INTEGER, -- Rating change (injury impact)
    delta_string VARCHAR(20), -- Injury description
    source_filename VARCHAR(255), -- Screenshot file this was extracted from
    source_y0 INTEGER, -- Top Y coordinate in screenshot (OCR bounding box)
    source_y1 INTEGER, -- Bottom Y coordinate in screenshot (OCR bounding box)
    name_confidence FLOAT, -- OCR confidence score for player name (0.0-1.0)
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_position CHECK (position IN ('PG', 'SG', 'SF', 'PF', 'C')),
    CONSTRAINT valid_rating CHECK (overall_rating IS NULL OR (overall_rating >= 0 AND overall_rating <= 99)),
    UNIQUE(name, team_id)  -- Prevent duplicate player entries for same team
);

-- ==============================================================================
-- TABLE: contracts
-- ==============================================================================
CREATE TABLE contracts (
    contract_id SERIAL PRIMARY KEY,
    player_id UUID REFERENCES roster_players(player_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team VARCHAR(50) NOT NULL, -- Kept for backward compatibility
    salary VARCHAR(20),
    salary_numeric DECIMAL(10, 2), -- Parsed numeric value in millions
    contract_option VARCHAR(50), -- 'Player', 'Team', '2 Yr Team', etc.
    signing_status VARCHAR(50), -- '1+1', '4 yrs', etc.
    extension_status VARCHAR(50), -- 'Will Resign', 'Not Eligible', etc.
    no_trade_clause BOOLEAN,
    source_filename VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, team_id)  -- One contract per player per team
);

-- ==============================================================================
-- TABLE: draft_picks
-- ==============================================================================
CREATE TABLE draft_picks (
    pick_id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team VARCHAR(50) NOT NULL, -- Kept for backward compatibility
    draft_year INTEGER NOT NULL CHECK (draft_year BETWEEN 2026 AND 2040),
    round INTEGER NOT NULL CHECK (round IN (1, 2)),
    pick_number INTEGER CHECK (pick_number BETWEEN 1 AND 60),
    protection VARCHAR(100),
    origin_team_id INTEGER REFERENCES teams(team_id),
    origin_team VARCHAR(50), -- Kept for backward compatibility
    source_filename VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- TABLE: standings
-- ==============================================================================
CREATE TABLE standings (
    standing_id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    team VARCHAR(50) NOT NULL, -- Kept for backward compatibility
    conference VARCHAR(10) CHECK (conference IN ('Eastern', 'Western')),
    conference_rank INTEGER,
    power_rank INTEGER,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    win_percentage DECIMAL(5, 3) GENERATED ALWAYS AS (
        CASE 
            WHEN (wins + losses) = 0 THEN 0
            ELSE ROUND(wins::numeric / (wins + losses), 3)
        END
    ) STORED,
    source_filename VARCHAR(255),
    season VARCHAR(20) DEFAULT '2025-26',
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, season)  -- One entry per team per season
);

-- ==============================================================================
-- INDEXES
-- ==============================================================================

-- Roster indexes
CREATE INDEX idx_roster_team_id ON roster_players(team_id);
CREATE INDEX idx_roster_team ON roster_players(team);
CREATE INDEX idx_roster_name ON roster_players(name);
CREATE INDEX idx_roster_position ON roster_players(position);
CREATE INDEX idx_roster_rating ON roster_players(overall_rating);

-- Contract indexes
CREATE INDEX idx_contracts_player_id ON contracts(player_id);
CREATE INDEX idx_contracts_team_id ON contracts(team_id);
CREATE INDEX idx_contracts_team ON contracts(team);
CREATE INDEX idx_contracts_player ON contracts(player_name);
CREATE INDEX idx_contracts_salary_numeric ON contracts(salary_numeric);

-- Draft picks indexes
CREATE INDEX idx_draft_picks_team_id ON draft_picks(team_id);
CREATE INDEX idx_draft_picks_origin_team_id ON draft_picks(origin_team_id);
CREATE INDEX idx_draft_picks_team ON draft_picks(team);
CREATE INDEX idx_draft_picks_year ON draft_picks(draft_year);
CREATE INDEX idx_draft_picks_origin ON draft_picks(origin_team);

-- Standings indexes
CREATE INDEX idx_standings_team_id ON standings(team_id);
CREATE INDEX idx_standings_team ON standings(team);
CREATE INDEX idx_standings_conference ON standings(conference);
CREATE INDEX idx_standings_conf_rank ON standings(conference_rank);
CREATE INDEX idx_standings_power_rank ON standings(power_rank);

-- ==============================================================================
-- VIEWS
-- ==============================================================================

-- View: player_complete_info
-- Combines roster and contract information with team details
CREATE OR REPLACE VIEW player_complete_info AS
SELECT 
    r.player_id,
    r.name,
    t.team_name as team,
    t.abbreviation as team_abbr,
    r.position,
    r.age,
    r.overall_rating,
    r.delta,
    r.delta_string,
    c.salary,
    c.salary_numeric,
    c.contract_option,
    c.signing_status,
    c.extension_status,
    c.no_trade_clause,
    r.source_filename,
    r.extracted_at
FROM roster_players r
LEFT JOIN teams t ON r.team_id = t.team_id
LEFT JOIN contracts c ON r.player_id = c.player_id;

-- View: team_salary_summary
-- Aggregates salary information by team
CREATE OR REPLACE VIEW team_salary_summary AS
SELECT 
    t.team_name as team,
    t.abbreviation as team_abbr,
    COUNT(*) as player_count,
    ROUND(SUM(c.salary_numeric), 2) as total_salary,
    ROUND(AVG(c.salary_numeric), 2) as avg_salary,
    ROUND(MAX(c.salary_numeric), 2) as max_salary,
    ROUND(MIN(c.salary_numeric), 2) as min_salary
FROM contracts c
JOIN teams t ON c.team_id = t.team_id
GROUP BY t.team_name, t.abbreviation;

-- View: draft_picks_inventory
-- Shows draft picks organized by team and year
CREATE OR REPLACE VIEW draft_picks_inventory AS
SELECT 
    t.team_name as team,
    t.abbreviation as team_abbr,
    dp.draft_year,
    COUNT(*) as total_picks,
    SUM(CASE WHEN dp.round = 1 THEN 1 ELSE 0 END) as first_round_picks,
    SUM(CASE WHEN dp.round = 2 THEN 1 ELSE 0 END) as second_round_picks,
    STRING_AGG(
        CASE 
            WHEN dp.round = 1 THEN CONCAT('1st-', COALESCE(dp.pick_number::text, '?'), ' (', ot.abbreviation, ')')
            WHEN dp.round = 2 THEN CONCAT('2nd-', COALESCE(dp.pick_number::text, '?'), ' (', ot.abbreviation, ')')
        END, 
        ', ' 
        ORDER BY dp.round, dp.pick_number
    ) as pick_details
FROM draft_picks dp
JOIN teams t ON dp.team_id = t.team_id
LEFT JOIN teams ot ON dp.origin_team_id = ot.team_id
GROUP BY t.team_name, t.abbreviation, dp.draft_year
ORDER BY t.team_name, dp.draft_year;

-- View: standings_detailed
-- Standings with calculated fields and team details
CREATE OR REPLACE VIEW standings_detailed AS
SELECT 
    t.team_name as team,
    t.abbreviation as team_abbr,
    s.conference,
    s.conference_rank,
    s.power_rank,
    s.wins,
    s.losses,
    s.win_percentage,
    (s.wins + s.losses) as games_played,
    (82 - (s.wins + s.losses)) as games_remaining,
    s.season,
    s.extracted_at
FROM standings s
JOIN teams t ON s.team_id = t.team_id
ORDER BY s.conference, s.conference_rank;

-- ==============================================================================
-- COMMENTS / DOCUMENTATION
-- ==============================================================================

COMMENT ON TABLE teams IS 'Reference table for all 30 NBA teams with IDs';
COMMENT ON TABLE roster_players IS 'Player roster information from NBA 2K26 with UUID primary keys. source_y0/y1 are OCR bounding box coordinates, name_confidence is OCR accuracy (0-1)';
COMMENT ON TABLE contracts IS 'Player contract details including salary and options';
COMMENT ON TABLE draft_picks IS 'Future draft picks ownership and details';
COMMENT ON TABLE standings IS 'Team standings and records';
COMMENT ON TABLE extraction_sources IS 'Tracks processed screenshot files';

COMMENT ON VIEW player_complete_info IS 'Complete player information combining roster and contracts';
COMMENT ON VIEW team_salary_summary IS 'Salary cap summary by team';
COMMENT ON VIEW draft_picks_inventory IS 'Draft picks grouped by team and year';
COMMENT ON VIEW standings_detailed IS 'Team standings with calculated statistics';
