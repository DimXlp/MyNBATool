-- NBA 2K26 Database Schema
-- PostgreSQL Database for storing extracted game data

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS draft_picks CASCADE;
DROP TABLE IF EXISTS contracts CASCADE;
DROP TABLE IF EXISTS roster_players CASCADE;
DROP TABLE IF EXISTS standings CASCADE;
DROP TABLE IF EXISTS extraction_sources CASCADE;

-- Extraction sources table (track which screenshots we've processed)
CREATE TABLE extraction_sources (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    file_type VARCHAR(50) NOT NULL, -- 'roster', 'contract', 'draft_picks', 'standings'
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Roster players table
CREATE TABLE roster_players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team VARCHAR(50) NOT NULL,
    position VARCHAR(5),
    age INTEGER,
    overall_rating INTEGER,
    injury_delta INTEGER,
    injury_string VARCHAR(20),
    source_filename VARCHAR(255),
    source_y0 INTEGER,
    source_y1 INTEGER,
    name_confidence FLOAT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_position CHECK (position IN ('PG', 'SG', 'SF', 'PF', 'C')),
    CONSTRAINT valid_rating CHECK (overall_rating IS NULL OR (overall_rating >= 0 AND overall_rating <= 99))
);

-- Contracts table
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    team VARCHAR(50) NOT NULL,
    salary VARCHAR(20),
    salary_numeric DECIMAL(10, 2), -- Parsed numeric value in millions
    contract_option VARCHAR(50), -- 'Player', 'Team', '2 Yr Team', etc.
    signing_status VARCHAR(50), -- '1+1', '4 yrs', etc.
    extension_status VARCHAR(50), -- 'Will Resign', 'Not Eligible', etc.
    no_trade_clause BOOLEAN,
    source_filename VARCHAR(255),
    source_y0 INTEGER,
    source_y1 INTEGER,
    name_confidence FLOAT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Draft picks table
CREATE TABLE draft_picks (
    id SERIAL PRIMARY KEY,
    team VARCHAR(50) NOT NULL,
    draft_year INTEGER NOT NULL,
    round INTEGER NOT NULL, -- 1 or 2
    pick_number INTEGER, -- Specific pick number if known
    protection VARCHAR(100), -- 'Lottery Protected', 'Top 10 Protected', etc.
    origin_team VARCHAR(50) NOT NULL, -- Which team originally owned this pick
    source_filename VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_round CHECK (round IN (1, 2)),
    CONSTRAINT valid_pick_number CHECK (pick_number IS NULL OR (pick_number >= 1 AND pick_number <= 60)),
    CONSTRAINT valid_year CHECK (draft_year >= 2026 AND draft_year <= 2040)
);

-- Standings table
CREATE TABLE standings (
    id SERIAL PRIMARY KEY,
    team VARCHAR(50) NOT NULL,
    conference VARCHAR(10) NOT NULL,
    conference_rank INTEGER,
    power_rank INTEGER,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    win_percentage DECIMAL(5, 3) GENERATED ALWAYS AS (
        CASE WHEN (wins + losses) > 0 
        THEN CAST(wins AS DECIMAL) / (wins + losses)
        ELSE 0 END
    ) STORED,
    source_filename VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    season VARCHAR(20) DEFAULT '2026-27', -- e.g., '2026-27'
    CONSTRAINT valid_conference CHECK (conference IN ('Eastern', 'Western')),
    CONSTRAINT valid_rank CHECK (conference_rank IS NULL OR (conference_rank >= 1 AND conference_rank <= 15))
);

-- Create indexes for common queries
CREATE INDEX idx_roster_team ON roster_players(team);
CREATE INDEX idx_roster_name ON roster_players(name);
CREATE INDEX idx_roster_position ON roster_players(position);
CREATE INDEX idx_roster_rating ON roster_players(overall_rating);

CREATE INDEX idx_contracts_team ON contracts(team);
CREATE INDEX idx_contracts_player ON contracts(player_name);
CREATE INDEX idx_contracts_salary_numeric ON contracts(salary_numeric);

CREATE INDEX idx_draft_picks_team ON draft_picks(team);
CREATE INDEX idx_draft_picks_year ON draft_picks(draft_year);
CREATE INDEX idx_draft_picks_origin ON draft_picks(origin_team);

CREATE INDEX idx_standings_team ON standings(team);
CREATE INDEX idx_standings_conference ON standings(conference);
CREATE INDEX idx_standings_rank ON standings(conference_rank);

-- Create view for combined roster and contract information
CREATE OR REPLACE VIEW player_complete_info AS
SELECT 
    r.name,
    r.team,
    r.position,
    r.age,
    r.overall_rating,
    r.injury_delta,
    r.injury_string,
    c.salary,
    c.salary_numeric,
    c.contract_option,
    c.signing_status,
    c.extension_status,
    c.no_trade_clause,
    r.updated_at as last_updated
FROM roster_players r
LEFT JOIN contracts c ON r.name = c.player_name AND r.team = c.team;

-- Create view for team salary summary
CREATE OR REPLACE VIEW team_salary_summary AS
SELECT 
    team,
    COUNT(*) as player_count,
    SUM(salary_numeric) as total_salary,
    AVG(salary_numeric) as avg_salary,
    MAX(salary_numeric) as max_salary,
    MIN(salary_numeric) as min_salary
FROM contracts
WHERE salary_numeric IS NOT NULL
GROUP BY team
ORDER BY total_salary DESC;

-- Create view for draft picks inventory
CREATE OR REPLACE VIEW draft_picks_inventory AS
SELECT 
    team,
    draft_year,
    COUNT(*) as total_picks,
    SUM(CASE WHEN round = 1 THEN 1 ELSE 0 END) as first_round_picks,
    SUM(CASE WHEN round = 2 THEN 1 ELSE 0 END) as second_round_picks,
    STRING_AGG(
        CASE 
            WHEN protection IS NOT NULL THEN origin_team || ' (' || protection || ')'
            ELSE origin_team 
        END, 
        ', ' 
        ORDER BY round, origin_team
    ) as pick_details
FROM draft_picks
GROUP BY team, draft_year
ORDER BY team, draft_year;

-- Create view for team standings with additional stats
CREATE OR REPLACE VIEW standings_detailed AS
SELECT 
    conference,
    conference_rank,
    team,
    wins,
    losses,
    win_percentage,
    wins + losses as games_played,
    82 - (wins + losses) as games_remaining,
    power_rank,
    season
FROM standings
ORDER BY conference, conference_rank;

COMMENT ON TABLE roster_players IS 'Player roster information extracted from NBA 2K26 screenshots';
COMMENT ON TABLE contracts IS 'Player contract details extracted from NBA 2K26 screenshots';
COMMENT ON TABLE draft_picks IS 'Future draft picks owned by teams';
COMMENT ON TABLE standings IS 'Current season standings for all teams';
COMMENT ON TABLE extraction_sources IS 'Tracks which screenshot files have been processed';

COMMENT ON VIEW player_complete_info IS 'Combined view of roster and contract information for all players';
COMMENT ON VIEW team_salary_summary IS 'Salary cap summary by team';
COMMENT ON VIEW draft_picks_inventory IS 'Draft picks inventory grouped by team and year';
COMMENT ON VIEW standings_detailed IS 'Standings with calculated statistics';
