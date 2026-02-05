# Database Setup Guide for NBA 2K26 Tool

## Prerequisites

1. **Install PostgreSQL**
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Or use chocolatey: `choco install postgresql`
   - Default port: 5432
   - Remember the password you set for the postgres user

2. **Install Python PostgreSQL driver**
   ```bash
   .venv\Scripts\pip install psycopg2-binary
   ```

## Setup Steps

### 1. Start PostgreSQL Service (if not running)
```powershell
# Check if running
Get-Service postgresql*

# Start if needed
Start-Service postgresql-x64-15  # Adjust version number
```

### 2. Create Database
```powershell
# Option A: Using createdb command
createdb -U postgres nba2k26

# Option B: Using psql
psql -U postgres -c "CREATE DATABASE nba2k26;"
```

### 3. Configure Database Connection (Optional)
If you're not using default settings, set environment variables:
```powershell
$env:NBA2K_DB_HOST = "localhost"
$env:NBA2K_DB_PORT = "5432"
$env:NBA2K_DB_NAME = "nba2k26"
$env:NBA2K_DB_USER = "postgres"
$env:NBA2K_DB_PASSWORD = "your_password"
```

### 4. Initialize Database Schema
```bash
python init_database.py
```

This will:
- Check if database exists (create if needed)
- Create all tables (roster_players, contracts, draft_picks, standings)
- Create views for common queries
- Verify everything is set up correctly

### 5. Import Existing Data
```bash
python import_to_database.py
```

This will:
- Import roster_players.json → roster_players table
- Import contracts.json → contracts table
- Import draft_picks.json → draft_picks table
- Import standings.json → standings table

## Database Schema

### Tables

**roster_players**
- Player roster information (name, team, position, age, overall rating, injury)

**contracts**
- Contract details (player, team, salary, options, extensions, NTC)

**draft_picks**
- Future draft picks (team, year, round, pick number, protection, origin)

**standings**
- Current standings (team, conference, rank, wins, losses, win percentage)

**extraction_sources**
- Tracks which screenshots have been processed

### Views

**player_complete_info**
- Combined roster and contract information for each player

**team_salary_summary**
- Salary cap summary by team (total, average, max, min)

**draft_picks_inventory**
- Draft picks grouped by team and year with protection details

**standings_detailed**
- Standings with calculated stats (games played, games remaining)

## Usage Examples

### Query using psql
```bash
# Connect to database
psql -U postgres -d nba2k26

# Example queries
SELECT * FROM team_salary_summary ORDER BY total_salary DESC;
SELECT * FROM player_complete_info WHERE team = 'Los Angeles Lakers';
SELECT * FROM draft_picks_inventory WHERE team = 'Knicks';
SELECT * FROM standings_detailed ORDER BY conference, conference_rank;
```

### Query using Python
```python
import db_config

conn = db_config.get_connection()
cur = conn.cursor()

# Get top 10 highest paid players
cur.execute("""
    SELECT player_name, team, salary, salary_numeric 
    FROM contracts 
    WHERE salary_numeric IS NOT NULL 
    ORDER BY salary_numeric DESC 
    LIMIT 10
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
```

## Troubleshooting

**"Could not connect to PostgreSQL"**
- Check if PostgreSQL is running: `Get-Service postgresql*`
- Verify port 5432 is not blocked
- Check username/password

**"Database does not exist"**
- Run: `createdb -U postgres nba2k26`
- Or let init_database.py create it automatically

**"Permission denied"**
- Make sure postgres user has appropriate permissions
- Or create a new user: `createuser -U postgres -P nba2k26user`

**"psycopg2 not found"**
- Install: `.venv\Scripts\pip install psycopg2-binary`

## Next Steps

After setting up the database:

1. **Update extractors** to optionally write directly to database
2. **Create reports** using SQL queries or Python scripts
3. **Build web interface** (optional) to view and manage data
4. **Set up automatic backups** for the database
5. **Create more views** for specific analysis needs
