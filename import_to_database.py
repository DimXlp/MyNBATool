# import_to_database.py
"""Import existing JSON data files into the PostgreSQL database."""

import json
from pathlib import Path
from typing import List, Dict, Any
import re
import db_config

OUTPUT_DIR = Path("output")

def parse_salary(salary_str: str) -> float:
    """Parse salary string like '$40.54M' to numeric value 40.54"""
    if not salary_str:
        return None
    
    # Remove $, M, and any other non-numeric characters except .
    numeric = re.sub(r'[^\d.]', '', salary_str)
    try:
        return float(numeric) if numeric else None
    except ValueError:
        return None

def parse_record(record_str: str) -> tuple:
    """Parse record string like '20-11' to (wins, losses)"""
    if not record_str or '-' not in record_str:
        return (0, 0)
    
    parts = record_str.split('-')
    try:
        wins = int(parts[0])
        losses = int(parts[1])
        return (wins, losses)
    except (ValueError, IndexError):
        return (0, 0)

def parse_round(round_str: str) -> int:
    """Parse round string like '1st' or '2nd' to integer"""
    if not round_str:
        return None
    
    if '1' in round_str:
        return 1
    elif '2' in round_str:
        return 2
    return None

def import_roster_players():
    """Import roster players from JSON."""
    roster_file = OUTPUT_DIR / "roster_players.json"
    if not roster_file.exists():
        print(f"  ⊘ {roster_file.name} not found, skipping")
        return 0
    
    data = json.loads(roster_file.read_text(encoding="utf-8"))
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM roster_players")
    
    count = 0
    for player in data:
        cur.execute(
            """
            INSERT INTO roster_players 
            (name, team, position, age, overall_rating, injury_delta, injury_string,
             source_filename, source_y0, source_y1, name_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                player.get("name"),
                player.get("team"),
                player.get("pos"),
                player.get("age"),
                player.get("ovr"),
                player.get("in_delta"),
                player.get("in_str"),
                player.get("source"),
                player.get("y0"),
                player.get("y1"),
                player.get("name_conf")
            )
        )
        count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"  ✓ Imported {count} roster players")
    return count

def import_contracts():
    """Import contracts from JSON."""
    contracts_file = OUTPUT_DIR / "contracts.json"
    if not contracts_file.exists():
        print(f"  ⊘ {contracts_file.name} not found, skipping")
        return 0
    
    data = json.loads(contracts_file.read_text(encoding="utf-8"))
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM contracts")
    
    count = 0
    for contract in data:
        salary_str = contract.get("salary")
        salary_numeric = parse_salary(salary_str)
        
        ntc = contract.get("ntc")
        ntc_bool = None
        if ntc:
            ntc_bool = ntc.lower() in ['yes', 'y', 'true']
        
        cur.execute(
            """
            INSERT INTO contracts 
            (player_name, team, salary, salary_numeric, contract_option, 
             signing_status, extension_status, no_trade_clause,
             source_filename, source_y0, source_y1, name_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                contract.get("name"),
                contract.get("team"),
                salary_str,
                salary_numeric,
                contract.get("option"),
                contract.get("sign"),
                contract.get("extension"),
                ntc_bool,
                contract.get("source"),
                contract.get("y0"),
                contract.get("y1"),
                contract.get("name_conf")
            )
        )
        count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"  ✓ Imported {count} contracts")
    return count

def import_draft_picks():
    """Import draft picks from JSON."""
    picks_file = OUTPUT_DIR / "draft_picks.json"
    if not picks_file.exists():
        print(f"  ⊘ {picks_file.name} not found, skipping")
        return 0
    
    data = json.loads(picks_file.read_text(encoding="utf-8"))
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM draft_picks")
    
    count = 0
    for pick in data:
        year_str = pick.get("year")
        try:
            year = int(year_str) if year_str else None
        except ValueError:
            year = None
        
        round_num = parse_round(pick.get("round"))
        
        if year and round_num:  # Only import if we have valid year and round
            cur.execute(
                """
                INSERT INTO draft_picks 
                (team, draft_year, round, pick_number, protection, origin_team, source_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    pick.get("team"),
                    year,
                    round_num,
                    pick.get("pick"),
                    pick.get("protection"),
                    pick.get("origin"),
                    pick.get("source")
                )
            )
            count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"  ✓ Imported {count} draft picks")
    return count

def import_standings():
    """Import standings from JSON."""
    standings_file = OUTPUT_DIR / "standings.json"
    if not standings_file.exists():
        print(f"  ⊘ {standings_file.name} not found, skipping")
        return 0
    
    data = json.loads(standings_file.read_text(encoding="utf-8"))
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM standings")
    
    count = 0
    for standing in data:
        wins, losses = parse_record(standing.get("record", "0-0"))
        
        cur.execute(
            """
            INSERT INTO standings 
            (team, conference, conference_rank, power_rank, wins, losses, source_filename)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                standing.get("team"),
                standing.get("conference"),
                standing.get("rank"),
                standing.get("power_rank"),
                wins,
                losses,
                standing.get("source")
            )
        )
        count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"  ✓ Imported {count} standings")
    return count

def main():
    """Main import function."""
    print("=" * 60)
    print("Importing JSON data to PostgreSQL")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing database connection...")
    if not db_config.test_connection():
        print("   Failed to connect. Run init_database.py first.")
        return
    
    # Import data
    print("\n2. Importing data...")
    
    total = 0
    total += import_roster_players()
    total += import_contracts()
    total += import_draft_picks()
    total += import_standings()
    
    print(f"\n{'=' * 60}")
    print(f"✓ Import complete! Total records: {total}")
    print("=" * 60)
    
    # Show summary
    print("\nDatabase summary:")
    tables = ["roster_players", "contracts", "draft_picks", "standings"]
    for table in tables:
        count = db_config.get_table_count(table)
        print(f"  {table:20} {count:5} rows")
    
    print("\nYou can now query the database:")
    print("  psql -d nba2k26 -c 'SELECT * FROM team_salary_summary;'")
    print("  psql -d nba2k26 -c 'SELECT * FROM player_complete_info LIMIT 10;'")

if __name__ == "__main__":
    main()
