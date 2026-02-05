#!/usr/bin/env python3
"""
Import NBA 2K26 data from JSON files into PostgreSQL database (v2 with UUIDs)
"""

import json
from pathlib import Path
import db_config
import re

def get_team_id(cur, team_name):
    """Get team_id from teams table, matching various name formats"""
    # Try exact match first
    cur.execute("SELECT team_id FROM teams WHERE team_name = %s", (team_name,))
    result = cur.fetchone()
    if result:
        return result[0]
    
    # Try abbreviation match
    cur.execute("SELECT team_id FROM teams WHERE abbreviation = %s", (team_name,))
    result = cur.fetchone()
    if result:
        return result[0]
    
    # Try partial match (for names like "Lakers" vs "Los Angeles Lakers")
    cur.execute("SELECT team_id FROM teams WHERE team_name LIKE %s", (f'%{team_name}%',))
    result = cur.fetchone()
    if result:
        return result[0]
    
    # If still not found, try reverse partial match
    cur.execute("SELECT team_id, team_name FROM teams")
    for row in cur.fetchall():
        if team_name in row[1] or row[1].split()[-1] == team_name.split()[-1]:
            return row[0]
    
    print(f"WARNING: Could not find team_id for '{team_name}' - skipping")
    return None

def parse_salary(salary_str):
    """Parse salary string like '$40.54M' to numeric 40.54"""
    if not salary_str or salary_str == 'N/A':
        return None
    # Remove everything except digits and decimal point
    numeric_str = re.sub(r'[^\d.]', '', salary_str)
    try:
        return float(numeric_str) if numeric_str else None
    except ValueError:
        return None

def parse_round(round_str):
    """Convert round string '1st' or '2nd' to integer 1 or 2"""
    if not round_str:
        return None
    if '1' in round_str:
        return 1
    elif '2' in round_str:
        return 2
    return None

def parse_record(record_str):
    """Parse record string like '20-11' to (wins=20, losses=11)"""
    if not record_str or '-' not in record_str:
        return None, None
    parts = record_str.split('-')
    try:
        wins = int(parts[0])
        losses = int(parts[1])
        return wins, losses
    except (ValueError, IndexError):
        return None, None

def import_roster_players(conn, cur):
    """Import roster players with UUID generation"""
    json_file = Path('output/roster_players.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting roster players from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    # Clear existing data
    cur.execute("DELETE FROM roster_players")
    
    imported = 0
    skipped = 0
    
    for player in players:
        team_id = get_team_id(cur, player.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Insert with UUID auto-generation
        cur.execute("""
            INSERT INTO roster_players (
                name, team_id, team, position, age, overall_rating,
                delta, delta_string, source_filename,
                source_y0, source_y1, name_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            player.get('name'),
            team_id,
            player.get('team'),
            player.get('pos'),  # JSON uses 'pos'
            player.get('age'),
            player.get('ovr'),  # JSON uses 'ovr'
            player.get('in_delta'),  # JSON uses 'in_delta'
            player.get('in_str'),  # JSON uses 'in_str'
            player.get('source'),  # JSON uses 'source'
            player.get('y0'),
            player.get('y1'),
            player.get('name_conf')  # JSON uses 'name_conf'
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported {imported} players (skipped {skipped})")

def import_contracts(conn, cur):
    """Import contracts linked to players via UUID"""
    json_file = Path('output/contracts.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting contracts from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        contracts = json.load(f)
    
    # Clear existing data
    cur.execute("DELETE FROM contracts")
    
    imported = 0
    skipped = 0
    
    for contract in contracts:
        team_id = get_team_id(cur, contract.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Get player name - JSON uses 'name' not 'player_name'
        player_name = contract.get('name') or contract.get('player_name')
        
        if not player_name:
            skipped += 1
            continue
        
        # Find player_id by name and team
        cur.execute("""
            SELECT player_id FROM roster_players 
            WHERE name = %s AND team_id = %s
        """, (player_name, team_id))
        result = cur.fetchone()
        player_id = result[0] if result else None
        
        # Parse salary to numeric
        salary = contract.get('salary', '')
        salary_numeric = parse_salary(salary)
        
        # Convert NTC to boolean - JSON uses 'ntc'
        ntc_str = contract.get('ntc', '').strip().upper()
        no_trade_clause = ntc_str == 'YES'
        
        cur.execute("""
            INSERT INTO contracts (
                player_id, player_name, team_id, team, salary, salary_numeric,
                contract_option, signing_status, extension_status,
                no_trade_clause, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            player_id,  # May be NULL if player not in roster
            player_name,
            team_id,
            contract.get('team'),
            salary,
            salary_numeric,
            contract.get('option'),  # JSON uses 'option'
            contract.get('sign'),  # JSON uses 'sign'
            contract.get('extension'),  # JSON uses 'extension'
            no_trade_clause,
            contract.get('source')  # JSON uses 'source'
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported {imported} contracts (skipped {skipped})")

def import_draft_picks(conn, cur):
    """Import draft picks with team references"""
    json_file = Path('output/draft_picks.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting draft picks from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        picks = json.load(f)
    
    # Clear existing data
    cur.execute("DELETE FROM draft_picks")
    
    imported = 0
    skipped = 0
    
    for pick in picks:
        team_id = get_team_id(cur, pick.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        origin_team_id = get_team_id(cur, pick.get('origin', '')) if pick.get('origin') else None
        
        # Parse year to int
        try:
            year = int(pick.get('year', 0))
            if year < 2026:
                skipped += 1
                continue
        except (ValueError, TypeError):
            skipped += 1
            continue
        
        # Parse round to 1 or 2
        round_num = parse_round(pick.get('round', ''))
        if round_num is None:
            skipped += 1
            continue
        
        cur.execute("""
            INSERT INTO draft_picks (
                team_id, team, draft_year, round, pick_number,
                protection, origin_team_id, origin_team, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            team_id,
            pick.get('team'),
            year,
            round_num,
            pick.get('pick'),
            pick.get('protection'),
            origin_team_id,
            pick.get('origin'),
            pick.get('source')  # JSON uses 'source'
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported {imported} draft picks (skipped {skipped})")

def import_standings(conn, cur):
    """Import standings with team references"""
    json_file = Path('output/standings.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting standings from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        standings = json.load(f)
    
    # Clear existing data
    cur.execute("DELETE FROM standings")
    
    imported = 0
    skipped = 0
    
    for standing in standings:
        team_id = get_team_id(cur, standing.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Parse record to wins/losses
        record = standing.get('record', '')
        wins, losses = parse_record(record)
        
        if wins is None or losses is None:
            skipped += 1
            continue
        
        cur.execute("""
            INSERT INTO standings (
                team_id, team, conference, conference_rank,
                power_rank, wins, losses, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            team_id,
            standing.get('team'),
            standing.get('conference'),
            standing.get('rank'),  # JSON uses 'rank'
            standing.get('power_rank'),
            wins,
            losses,
            standing.get('source')  # JSON uses 'source'
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported {imported} standings (skipped {skipped})")

def main():
    """Main import workflow"""
    print("=" * 60)
    print("NBA 2K26 Data Import (v2 with UUIDs)")
    print("=" * 60)
    
    # Connect to database
    print("\nConnecting to database...")
    try:
        conn = db_config.get_connection()
        cur = conn.cursor()
        print("✓ Connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Import in order (roster first for player UUIDs)
        import_roster_players(conn, cur)
        import_contracts(conn, cur)
        import_draft_picks(conn, cur)
        import_standings(conn, cur)
        
        # Show final counts
        print("\n" + "=" * 60)
        print("Import Summary:")
        print("=" * 60)
        
        cur.execute("SELECT COUNT(*) FROM roster_players")
        print(f"Roster players: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM contracts")
        print(f"Contracts: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM draft_picks")
        print(f"Draft picks: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM standings")
        print(f"Standings: {cur.fetchone()[0]}")
        
        print("\n✓ Import completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
