# NBA 2K26 Tool - PostgreSQL Database Setup

## What's Been Created

I've set up a complete PostgreSQL database system for your NBA 2K26 tool:

### 📁 Files Created

1. **database/schema.sql** - Complete database schema with:
   - 5 tables: roster_players, contracts, draft_picks, standings, extraction_sources
   - 4 views: player_complete_info, team_salary_summary, draft_picks_inventory, standings_detailed
   - Indexes for fast queries
   - Constraints for data integrity

2. **db_config.py** - Database connection management
   - Connection pooling
   - Environment variable support
   - Helper functions for common operations

3. **init_database.py** - Database initialization script
   - Creates database if it doesn't exist
   - Creates all tables and views
   - Verifies setup

4. **import_to_database.py** - Data import script
   - Imports all existing JSON files into database
   - Parses and normalizes data (salaries, records, rounds)
   - Shows import summary

5. **check_postgres.py** - PostgreSQL installation checker
   - Verifies PostgreSQL is installed and running
   - Checks if psql command is available

6. **database/README.md** - Complete setup guide with examples

### 📊 Database Schema

**roster_players** (44 rows ready to import)
- name, team, position, age, overall_rating, injury info
- Source tracking (filename, Y coordinates, confidence)

**contracts** (same players)
- player_name, team, salary (text + numeric), options
- signing_status, extension_status, no_trade_clause
- Source tracking

**draft_picks** (28 picks ready to import)
- team, draft_year, round (1 or 2), pick_number
- protection, origin_team
- Source tracking

**standings** (ready to import)
- team, conference, ranks, wins, losses
- Calculated: win_percentage, games_played, games_remaining

**extraction_sources**
- Tracks which screenshots have been processed
- Prevents duplicate imports

### 🎯 Useful Views

**player_complete_info** - One-stop player info
```sql
SELECT * FROM player_complete_info WHERE team = 'Los Angeles Lakers';
```

**team_salary_summary** - Salary cap analysis
```sql
SELECT * FROM team_salary_summary ORDER BY total_salary DESC;
```

**draft_picks_inventory** - Future picks by team/year
```sql
SELECT * FROM draft_picks_inventory WHERE team = 'Knicks';
```

**standings_detailed** - Full standings with stats
```sql
SELECT * FROM standings_detailed ORDER BY conference, conference_rank;
```

## Installation Steps

### 1. Install PostgreSQL

**Option A: Official Installer (Recommended)**
1. Download from: https://www.postgresql.org/download/windows/
2. Run installer (PostgreSQL 15 or later recommended)
3. During installation:
   - Remember the password for 'postgres' user
   - Default port 5432 is fine
   - Install pgAdmin (optional GUI tool)

**Option B: Chocolatey**
```powershell
choco install postgresql
```

### 2. Verify Installation
```bash
python check_postgres.py
```

Should show:
- ✓ PostgreSQL service is running
- ✓ psql is available

### 3. Initialize Database
```bash
python init_database.py
```

This will:
- Create 'nba2k26' database
- Create all tables and views
- Verify setup

### 4. Import Your Data
```bash
python import_to_database.py
```

This will import:
- 44 roster players
- 44 contracts
- 28 draft picks
- Standings (all teams)

## Usage Examples

### Command Line Queries

```bash
# Connect to database
psql -U postgres -d nba2k26

# Top 10 highest paid players
SELECT player_name, team, salary 
FROM contracts 
ORDER BY salary_numeric DESC 
LIMIT 10;

# Lakers roster with salaries
SELECT name, position, age, overall_rating, salary
FROM player_complete_info
WHERE team = 'Los Angeles Lakers'
ORDER BY overall_rating DESC;

# Draft picks summary
SELECT * FROM draft_picks_inventory 
WHERE team IN ('Knicks', 'Lakers', 'Magic')
ORDER BY team, draft_year;

# Team salary totals
SELECT * FROM team_salary_summary
ORDER BY total_salary DESC;
```

### Python Queries

```python
import db_config

conn = db_config.get_connection()
cur = conn.cursor()

# Get all Knicks players
cur.execute("""
    SELECT name, position, age, overall_rating 
    FROM roster_players 
    WHERE team = 'New York Knicks'
    ORDER BY overall_rating DESC
""")

for row in cur.fetchall():
    print(f"{row[0]:20} {row[1]:3} Age {row[2]:2} OVR {row[3]}")

cur.close()
conn.close()
```

## Benefits of Using Database

✅ **Better Performance** - Indexed queries are much faster than searching JSON
✅ **Complex Queries** - Join tables, aggregate data, filter efficiently
✅ **Data Integrity** - Constraints prevent invalid data
✅ **Concurrent Access** - Multiple tools can read/write simultaneously
✅ **Historical Data** - Track changes over time (can add versioning)
✅ **Reporting** - Easy to generate reports and statistics
✅ **Backup/Restore** - Standard database backup tools

## Next Steps

After setting up the database:

1. **Query your data** - Try the example queries above
2. **Update extractors** - Optionally modify extract_*.py to write directly to DB
3. **Create reports** - Build Python scripts for specific analysis
4. **Build web interface** (optional) - Flask/Django app to view data
5. **Add more features**:
   - Historical tracking (track player rating changes over time)
   - Trade analysis (compare before/after trades)
   - Cap space projections
   - Draft pick value calculator

## Troubleshooting

**Connection Issues:**
- Check service: `Get-Service postgresql*`
- Start service: `Start-Service postgresql-x64-15`
- Verify password in db_config.py or set environment variable

**Import Issues:**
- Make sure JSON files exist in output/ directory
- Run extractors first if needed
- Check for data validation errors in output

**Need Help:**
The database/README.md file has more detailed troubleshooting steps.
