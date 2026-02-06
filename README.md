# NBA 2K26 League Management Tool

A comprehensive OCR-based tool for extracting and managing NBA 2K26 league data. Extract roster information, contracts, draft picks, and standings from game screenshots, store in PostgreSQL database, and export league state for AI-powered GM assistance.

## Features

### 🎮 Data Extraction
- **4 Extractor Types**: Rosters, Contracts, Draft Picks, Standings
- **Smart OCR**: Handles game UI with high accuracy
- **Auto-Classification**: Automatically identifies screenshot types
- **Clean Output**: Concise progress reporting across all extractors

### 💾 Database Management
- **PostgreSQL Integration**: Store league data with relational structure
- **UUID Player Tracking**: Unique identifiers for each player
- **Per-Team Updates**: Replace only teams present in new screenshots
- **Smart Merging**: Preserve data for teams not in current batch

### 📦 Auto-Archive
- **Organized Storage**: Screenshots archived by date and type
- **Prevents Duplicates**: Extractors skip already-processed files
- **Space Efficient**: Keep `input_screenshots/` clean

### 🤖 AI GM Integration
- **ChatGPT Export**: Generate text files with full league state
- **Team Context**: Rosters with contracts, cap space, draft picks
- **Decision Support**: Use AI as your virtual GM assistant

## Prerequisites

### Required Software

1. **Python 3.12+** (tested with 3.12.8)
2. **PostgreSQL 17+** 
   - Download from [postgresql.org](https://www.postgresql.org/download/)
   - Default setup: localhost:5432, database: `nba2k26`
3. **Tesseract OCR**
   - Windows: Download from [GitHub Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - Ensure `tesseract --version` works in terminal
   - If not in PATH, set `TESSERACT_CMD` in extractor scripts

### Python Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `opencv-python` - Image processing
- `pytesseract` - OCR interface
- `psycopg2-binary` - PostgreSQL driver
- `numpy` - Numerical operations

## Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/nba2k26-league-tool.git
   cd nba2k26-league-tool
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR** (see Prerequisites)

5. **Setup PostgreSQL Database**
   ```bash
   # Create database and initialize schema
   python init_database.py
   ```
   
   This creates:
   - Database: `nba2k26`
   - Tables: `teams`, `roster_players`, `contracts`, `draft_picks`, `standings`
   - Views: `player_complete_info`, `team_salary_summary`, `draft_picks_inventory`, `standings_detailed`

## Project Structure

```
MyNBATool/
├── Extractors (OCR Processing)
│   ├── classify_screens.py            # Auto-classify screenshot types
│   ├── extract_roster_names.py        # Extract player rosters
│   ├── extract_contracts.py           # Extract contract data
│   ├── extract_draft_picks.py         # Extract future draft picks
│   └── extract_standings.py           # Extract team standings
│
├── Editors (Manual Verification & Fixes)
│   ├── edit_roster.py                # Fix roster OCR errors
│   ├── edit_contracts.py             # Fix contract OCR errors
│   ├── edit_draft_picks.py           # Fix draft pick OCR errors
│   └── edit_standings.py             # Fix standings OCR errors
│
├── Database
│   ├── database/
│   │   └── schema_v2.sql             # PostgreSQL schema with UUIDs
│   ├── db_config.py                  # Database connection config
│   ├── init_database.py              # Initialize database
│   ├── import_to_database_v2.py      # Import JSON → PostgreSQL
│   └── export_league_state.py        # Export DB → TXT for ChatGPT
│
├── Input/Output
│   ├── input_screenshots/            # Place new screenshots here
│   ├── archived_screenshots/         # Auto-archived by date/type
│   │   └── YYYY-MM-DD/
│   │       ├── roster/
│   │       ├── contracts/
│   │       ├── draft_picks/
│   │       └── standings/
│   ├── output/                       # JSON extraction results
│   │   ├── manifest.json
│   │   ├── roster_players.json
│   │   ├── contracts.json
│   │   ├── draft_picks.json
│   │   └── standings.json
│   └── league_exports/               # ChatGPT-ready text files
│       ├── 1_standings.txt
│       ├── 2_salary_cap.txt
│       ├── 3_rosters.txt
│       └── 4_draft_picks.txt
│
├── README.md
└── requirements.txt
```

## Usage

### Complete Workflow

#### 1. Take Screenshots in NBA 2K26
- **Roster**: Team → Roster Viewer (capture each team's roster)
- **Contracts**: Team → Contract Extensions (capture contract details)
- **Draft Picks**: Team → Future Draft Picks (capture draft assets)
- **Standings**: League → Team Standings (capture conference standings)

Save all screenshots to `input_screenshots/`

#### 2. Classify Screenshots
```bash
python classify_screens.py
```
Automatically identifies screenshot types and creates `output/manifest.json`

#### 3. Extract Data (Choose What You Need)

Extract rosters:
```bash
python extract_roster_names.py
```

Extract contracts:
```bash
python extract_contracts.py
```

Extract draft picks:
```bash
python extract_draft_picks.py
```

Extract standings:
```bash
python extract_standings.py
```

**Output**: Each extractor shows clean summary:
```
Total screenshots processed: 6
Teams processed: 3
Saved: output\roster_players.json
Archived 6 screenshot(s) to archived_screenshots/2026-02-06/roster
```

#### 4. Verify and Fix OCR Errors (Optional but Recommended)

OCR isn't perfect! Use interactive editors to review and correct any mistakes:

**Edit Rosters**:
```bash
python edit_roster.py
```
- View all players by team
- Fix name misspellings (e.g., "J. Brunscn" → "J. Brunson")
- Correct positions, ages, ratings
- Add missing players

**Edit Contracts**:
```bash
python edit_contracts.py
```
- Review contract details by team
- Fix salary amounts
- Correct option types, signing status, extensions
- Verify NTC (No-Trade Clause) flags

**Edit Draft Picks**:
```bash
python edit_draft_picks.py
```
- Review draft pick inventory by team
- Fix years, rounds, pick numbers
- Correct protection clauses
- Update origin teams

**Edit Standings**:
```bash
python edit_standings.py
```
- Review conference standings
- Fix team records (W-L)
- Correct rankings
- Update conference assignments

All editors:
- Interactive menu-driven interface
- Save changes back to JSON
- No database required (edits happen before import)

#### 5. Import to Database
```bash
python import_to_database_v2.py
```

**Per-Team Replacement**: Only teams present in new screenshots are updated!
- Week 1: Import Knicks, Lakers, Magic → Database has 3 teams
- Week 3: Import Knicks, Celtics → Database updates Knicks, adds Celtics, **keeps Lakers and Magic unchanged**

Example output:
```
✓ Cleared roster data for 2 team(s): Boston Celtics, New York Knicks
✓ Imported 30 players
Teams in database: 4 of 30
✓ Per-team replacement: Only teams in new screenshots were updated
```

#### 6. Export for ChatGPT
```bash
python export_league_state.py
```

Generates 4 text files in `league_exports/`:
1. **1_standings.txt** - Conference rankings and records
2. **2_salary_cap.txt** - Team salary summaries
3. **3_rosters.txt** - Complete rosters with contracts merged
4. **4_draft_picks.txt** - Future draft pick assets

**Use Case**: Copy these files to ChatGPT and ask:
> "I'm the GM of the New York Knicks. Based on our roster, cap situation, and draft picks, what moves should I make?"

## Database Schema

### Tables

**teams** (30 NBA teams pre-populated)
- `team_id` (PK), `team_name`, `abbreviation`, `conference`, `division`

**roster_players** (Player rosters with UUIDs)
- `player_id` (UUID, PK auto-generated)
- `team_id` (FK → teams), `name`, `position`, `age`, `overall_rating`
- `delta`, `delta_string` (rating changes)
- OCR metadata: `source_filename`, `source_y0`, `source_y1`, `name_confidence`

**contracts** (Contract details linked to players)
- `contract_id` (PK), `player_id` (FK → roster_players, CASCADE DELETE)
- `team_id` (FK → teams), `player_name`, `salary`, `salary_numeric`
- `contract_option`, `signing_status`, `extension_status`, `no_trade_clause`

**draft_picks** (Future draft assets)
- `pick_id` (PK), `team_id` (FK → teams), `draft_year`, `round`, `pick_number`
- `protection`, `origin_team_id` (FK → teams), `origin_team`

**standings** (Conference standings)
- `standing_id` (PK), `team_id` (FK → teams), `conference`, `conference_rank`
- `power_rank`, `wins`, `losses`

### Views

**player_complete_info** - Joins roster + contracts (all player data in one view)
**team_salary_summary** - Aggregates salary cap info per team
**draft_picks_inventory** - Draft pick summaries by team/year
**standings_detailed** - Enhanced standings with team info

## Auto-Archive System

### How It Works

When extractors run, they automatically:
1. Process screenshots from `input_screenshots/`
2. Save JSON to `output/`
3. **Move** processed screenshots to `archived_screenshots/YYYY-MM-DD/[type]/`

### Benefits

- **No Duplicates**: Manifest tracks processed files, skips them on re-run
- **Clean Input Folder**: Only unprocessed screenshots remain
- **Organized History**: Find old screenshots by date and type
- **Space Management**: Compress old month folders to save 80-90% space

### Example

```bash
# Week 1: Extract new screenshots
python extract_roster_names.py
# → Moves to archived_screenshots/2026-02-06/roster/

# Week 3: Extract new screenshots  
python extract_roster_names.py
# → Moves to archived_screenshots/2026-02-20/roster/
# → input_screenshots/ stays clean
```

## Per-Team Replacement Strategy

### Problem Solved

In a long MyLeague, you don't screenshot all 30 teams every week. The database now intelligently:
- **Updates** only teams present in new screenshots
- **Preserves** data for teams not in the current batch

### Example Scenario

**Initial State**: Database has Lakers, Knicks, Magic (Week 1)

**New Screenshots**: Knicks + Celtics (Week 3)

**Import Result**:
- ✅ Knicks: **UPDATED** (replaced with new data)
- ✅ Celtics: **ADDED** (new team)
- ✅ Lakers: **PRESERVED** (unchanged from Week 1)
- ✅ Magic: **PRESERVED** (unchanged from Week 1)

This applies to:
- Rosters & Contracts (CASCADE delete maintains links)
- Draft Picks
- Standings

## Configuration

### Database Connection

Edit `db_config.py` or set environment variables:
```python
DB_HOST = "localhost"       # or NBA2K_DB_HOST env var
DB_PORT = 5432             # or NBA2K_DB_PORT env var
DB_NAME = "nba2k26"        # or NBA2K_DB_NAME env var
DB_USER = "postgres"       # or NBA2K_DB_USER env var
DB_PASSWORD = "your_pass"  # or NBA2K_DB_PASSWORD env var
```

### Adjusting Screenshot ROIs

If your game resolution differs, adjust ROI values in extractor scripts:

```python
# extract_roster_names.py (1920x1080 resolution)
NAME_COL_ROI = (78, 495, 254, 469)
POS_COL_ROI = (340, 495, 70, 469)
AGE_COL_ROI = (449, 495, 59, 469)
RATING_COL_ROI = (563, 495, 58, 469)
IN_COL_ROI = (620, 495, 50, 469)
```

**Finding Coordinates**: Run with `--debug` flag, measure in image viewer

## Data Flow

```
Screenshots (Game) 
    ↓
input_screenshots/
    ↓
[classify_screens.py] → manifest.json
    ↓
[extract_*.py] → JSON files + Archive
    ↓
output/*.json
    ↓
[import_to_database_v2.py] → PostgreSQL
    ↓
Database (per-team storage)
    ↓
[export_league_state.py] → Text files
    ↓
league_exports/*.txt → ChatGPT → GM Decisions
```

## Output Examples

### Roster Players JSON
```json
{
  "name": "J. Brunson",
  "team": "New York Knicks",
  "pos": "PG",
  "age": 28,
  "ovr": 85,
  "in_delta": 2,
  "in_str": "+2",
  "source": "screenshot_001.png",
  "name_conf": 92.5
}
```

### Exported League State (3_rosters.txt)
```
=== NEW YORK KNICKS ===
Roster & Contracts:

J. Brunson      PG  28  85  (+2)  | Salary: $24.96M  Option: None  Sign: 4 yrs  Ext: Signed
M. Bridges      SF  28  81  (0)   | Salary: $23.31M  Option: None  Sign: 5 yrs  Ext: No
K. Towns        C   29  91  (+1)  | Salary: $49.25M  Option: None  Sign: 4 yrs  Ext: No
...

Salary Cap: Total: $182.5M | Avg: $12.2M | Max: $49.3M | Min: $1.1M
```

## Troubleshooting

### Database Issues

**"Connection failed"**
- Verify PostgreSQL is running: `pg_ctl status`
- Check credentials in `db_config.py`
- Ensure database exists: `python init_database.py`

**"Could not find team_id"**
- Team name variations are handled automatically
- Check `teams` table has all 30 NBA teams
- Verify team names in JSON match abbreviations/partial names

### OCR Issues

**"Tesseract is not installed"**
- Install Tesseract OCR: [Download Link](https://github.com/UB-Mannheim/tesseract/wiki)
- Verify: `tesseract --version`
- Set path in scripts: `TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`

**Poor extraction accuracy**
- Use `--debug` flag to inspect processing images
- Verify screenshot resolution is 1920x1080
- Adjust ROI coordinates if UI differs
- Ensure screenshots are clear, not compressed

### Import/Export Issues

**"No teams found in new data"**
- Check JSON files in `output/` directory
- Verify classify_screens.py ran successfully
- Ensure extractors completed without errors

**"Teams missing roster data"**
- This is expected! Only screenshot teams you want to update
- Other teams preserve their previous data
- Use export to see which teams have data

## Advanced Usage

### Query Database Directly

```python
import db_config

conn = db_config.get_connection()
cur = conn.cursor()

# Get all Knicks players with contracts
cur.execute("""
    SELECT name, position, age, overall_rating, salary
    FROM player_complete_info
    WHERE team = 'New York Knicks'
    ORDER BY overall_rating DESC
""")

for row in cur.fetchall():
    print(row)
```

### Custom Exports

Modify `export_league_state.py` to create custom reports:
- Trade analysis (contracts expiring soon)
- Draft pick values by team
- Salary cap projections
- Player development tracking

### Batch Processing

Process multiple teams at once:
```bash
# Take screenshots of multiple teams
# Classify all at once
python classify_screens.py

# Extract all data types
python extract_roster_names.py
python extract_contracts.py
python extract_draft_picks.py
python extract_standings.py

# Import everything
python import_to_database_v2.py

# Export league state
python export_league_state.py
```

## Technical Details

### OCR Strategy by Data Type

**Roster Names**
- Multiple PSM modes with confidence scoring
- Name normalization (initials, suffixes, Roman numerals)
- Icon detection and filtering (injury, G-League, two-way)
- OCR error corrections for common mistakes

**Contracts**
- Salary parsing: "$24.96M" → 24.96
- Multi-value extraction (option, signing status, extension, NTC)
- Year parsing: "4 yrs" → "4"

**Draft Picks**
- Column-based extraction (Year, Round, Pick, Protection, Origin)
- Round markers: "1st"/"2nd" → 1/2
- Protection text normalization ("Lottery Protected", "Top 10", etc.)
- Y-position based round detection for merged cells

**Standings**
- Conference detection (Eastern/Western)
- Record parsing: "20-11" → wins=20, losses=11
- Rank extraction with validation (1-30 range)

### Database Design

**UUID Implementation**
- Players: Auto-generated UUID primary keys
- Enables player tracking across roster changes
- Foreign key: contracts → players (ON DELETE CASCADE)

**Per-Team Updates**
- Extract teams from new JSON
- `DELETE WHERE team_id IN (new_teams)`
- Insert only new team data
- Preserves untouched teams

**View Benefits**
- `player_complete_info`: Join roster + contracts in one query
- `team_salary_summary`: Pre-calculated cap space
- Simplifies export queries

### Archive Strategy

**File Movement**
- `shutil.move()` - moves files, doesn't copy
- Organized: `archived_screenshots/YYYY-MM-DD/[type]/`
- Manifest tracks processed files
- Prevents re-processing duplicates

### ChatGPT Export Format

**Design Goals**
- Human-readable text tables
- Team-by-team organization
- Complete context for AI decisions
- Compact for token efficiency

**File Structure**
1. Standings: Quick league overview
2. Salary Cap: Financial constraints
3. Rosters: Player details + contracts merged
4. Draft Picks: Future assets

## Use Cases

### 1. Weekly League Updates
- Screenshot your team after each sim
- Extract + import to database
- Historical tracking of player development

### 2. Trade Analysis
- Export league state before trade deadline
- Ask ChatGPT: "What trades should I make?"
- Analyze cap space, draft compensation, roster fit

### 3. Draft Preparation
- Export draft picks inventory
- Identify teams with extra picks
- Trade scenarios for moving up/down

### 4. Salary Cap Management
- Query: Teams over luxury tax
- Find expiring contracts
- Plan extension timelines

### 5. Multi-Season Tracking
- Keep database across seasons
- Track player progression (rating changes)
- Identify development patterns

## Contributing

Contributions welcome! Areas for improvement:

- **Additional Extractors**: Free agents, trade finder, player awards
- **UI Development**: Web interface for database queries
- **Analytics**: Advanced stats, trade recommendations
- **Export Formats**: Excel, CSV, custom report templates
- **Mobile Support**: Screenshot capture from console/PC via phone

## Roadmap

- [ ] Web UI for viewing league data
- [ ] Automated screenshot capture via game API (if available)
- [ ] Historical trend analysis (player ratings over time)
- [ ] Trade simulator using database data
- [ ] Export to other formats (Excel, PDF reports)
- [ ] Multi-league support (track multiple MyLeague saves)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Text recognition engine
- [OpenCV](https://opencv.org/) - Computer vision and image processing
- [pytesseract](https://github.com/madmaze/pytesseract) - Python wrapper for Tesseract
- [PostgreSQL](https://www.postgresql.org/) - Relational database system
- [psycopg2](https://www.psycopg.org/) - PostgreSQL adapter for Python

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Include screenshot samples and error messages

---

**Built for NBA 2K26 MyLeague managers who want data-driven decision making** 🏀📊
