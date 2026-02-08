#!/usr/bin/env python3
"""
Import NBA 2K26 data from JSON files into PostgreSQL database (v2 with UUIDs)
"""

import json
from pathlib import Path
import db_config
import re
from difflib import SequenceMatcher

# OCR error corrections mapping
OCR_CORRECTIONS = {
    'itmberwolves': 'Timberwolves',
    'timberwolved': 'Timberwolves',
    'fimberwolves': 'Timberwolves',
    'fimberwolved': 'Timberwolves',
    'fimberwolvey': 'Timberwolves',
    '6efrs': '76ers',
    '760s': '76ers',
    'bucks': 'Milwaukee Bucks',
    'chppers': 'Clippers',
    'clppers': 'Clippers',
    'saazz': 'Jazz',
    'jazz': 'Utah Jazz',
    'deze': 'Jazz',
    'daze': 'Jazz',
    'grizzies': 'Grizzlies',
    'griezies': 'Grizzlies',
    'grizzlies': 'Memphis Grizzlies',
    'wizeras': 'Wizards',
    'wizards': 'Washington Wizards',
    'wasriors': 'Warriors',
    'warriors': 'Golden State Warriors',
    'nucoes': 'Nuggets',
    'nusoets': 'Nuggets',
    'nugoets': 'Nuggets',
    'nuggets': 'Denver Nuggets',
    'patcans': 'Pelicans',
    'peiicans': 'Pelicans',
    'pelicans': 'New Orleans Pelicans',
    'macc': 'Magic',
    'macic': 'Magic',
    'magic': 'Orlando Magic',
    'haws': 'Hawks',
    'hews': 'Hawks',
    'hawks': 'Atlanta Hawks',
    'cots': 'Celtics',
    'cottcs': 'Celtics',
    'celtics': 'Boston Celtics',
    'peat': 'Heat',
    'heat': 'Miami Heat',
    'rockes': 'Rockets',
    'rockets': 'Houston Rockets',
    'aus': 'Bulls',
    'euis': 'Bulls',
    'euls': 'Bulls',
    'euiis': 'Bulls',
    'eulis': 'Bulls',
    'bulls': 'Chicago Bulls',
    'cates': 'Cavaliers',
    'cavaliers': 'Cleveland Cavaliers',
    'cattios': 'Raptors',
    'aptors': 'Raptors',
    'raptors': 'Toronto Raptors',
    'wares': 'Wizards',
    'res': '76ers',
    # Prefixed versions (F/J/P prefix before team name)
    'f nucoes': 'Nuggets',
    'f patcans': 'Pelicans',
    'j macic': 'Magic',
    'p griezies': 'Grizzlies',
    'j hews': 'Hawks',
    'p macc': 'Magic',
    'f cates': 'Cavaliers',
    'j haws': 'Hawks',
}

def similarity_ratio(a, b):
    """Calculate similarity ratio between two strings (0 to 1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_team_id(cur, team_name):
    """Get team_id from teams table, matching various name formats with OCR error correction"""
    if not team_name:
        return None
    
    # Clean up team name - remove extra spaces
    team_name = team_name.strip()
    
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
    
    # Try OCR correction mapping (with normalized spacing)
    normalized_name = ' '.join(team_name.lower().split())
    corrected_name = OCR_CORRECTIONS.get(normalized_name)
    if corrected_name:
        # Try the corrected name
        cur.execute("SELECT team_id FROM teams WHERE team_name = %s", (corrected_name,))
        result = cur.fetchone()
        if result:
            return result[0]
        # Try partial match with corrected name
        cur.execute("SELECT team_id FROM teams WHERE team_name LIKE %s", (f'%{corrected_name}%',))
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
    
    # Try fuzzy matching as last resort (similarity > 75%)
    cur.execute("SELECT team_id, team_name FROM teams")
    all_teams = cur.fetchall()
    best_match = None
    best_ratio = 0.75  # Minimum threshold
    
    for team_id, db_team_name in all_teams:
        # Compare with full name
        ratio = similarity_ratio(team_name, db_team_name)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = team_id
        
        # Compare with nickname (last word)
        nickname = db_team_name.split()[-1]
        ratio = similarity_ratio(team_name, nickname)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = team_id
    
    if best_match:
        return best_match
    
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
    """Import roster players with UUID generation - replaces data only for teams in the new JSON"""
    json_file = Path('output/roster_players.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting roster players from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    # Identify teams present in new data
    new_teams = set()
    for player in players:
        team_id = get_team_id(cur, player.get('team', ''))
        if team_id:
            new_teams.add(team_id)
    
    # Delete existing data ONLY for teams in the new screenshot batch
    # CASCADE will automatically delete contracts for these players
    if new_teams:
        cur.execute(
            "DELETE FROM roster_players WHERE team_id = ANY(%s)",
            (list(new_teams),)
        )
        cur.execute("SELECT team_name FROM teams WHERE team_id = ANY(%s)", (list(new_teams),))
        team_names = [row[0] for row in cur.fetchall()]
        print(f"✓ Cleared roster data for {len(new_teams)} team(s): {', '.join(team_names)}")
    else:
        print("⚠ No valid teams found in new data")
    
    imported = 0
    skipped = 0
    
    for player in players:
        team_id = get_team_id(cur, player.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Get the correct team name from database
        cur.execute("SELECT team_name FROM teams WHERE team_id = %s", (team_id,))
        correct_team_name = cur.fetchone()[0]
        
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
            correct_team_name,  # Use corrected name from database
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
    """Import contracts linked to players via UUID
    
    Note: Contracts are automatically deleted when roster_players are deleted (CASCADE),
    so we don't need separate deletion logic. Just insert contracts for existing players.
    """
    json_file = Path('output/contracts.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting contracts from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        contracts = json.load(f)
    
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
    """Import draft picks with team references - replaces data only for teams in the new JSON"""
    json_file = Path('output/draft_picks.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting draft picks from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        picks = json.load(f)
    
    # Identify teams present in new data
    new_teams = set()
    for pick in picks:
        team_id = get_team_id(cur, pick.get('team', ''))
        if team_id:
            new_teams.add(team_id)
    
    # Delete existing draft picks ONLY for teams in the new screenshot batch
    if new_teams:
        cur.execute(
            "DELETE FROM draft_picks WHERE team_id = ANY(%s)",
            (list(new_teams),)
        )
        cur.execute("SELECT team_name FROM teams WHERE team_id = ANY(%s)", (list(new_teams),))
        team_names = [row[0] for row in cur.fetchall()]
        print(f"✓ Cleared draft picks for {len(new_teams)} team(s): {', '.join(team_names)}")
    else:
        print("⚠ No valid teams found in new data")
    
    imported = 0
    skipped = 0
    
    for pick in picks:
        team_id = get_team_id(cur, pick.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Get the correct team name from database
        cur.execute("SELECT team_name FROM teams WHERE team_id = %s", (team_id,))
        correct_team_name = cur.fetchone()[0]
        
        origin_team_id = get_team_id(cur, pick.get('origin', '')) if pick.get('origin') else None
        correct_origin_name = None
        if origin_team_id:
            cur.execute("SELECT team_name FROM teams WHERE team_id = %s", (origin_team_id,))
            correct_origin_name = cur.fetchone()[0]
        
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
            correct_team_name,  # Use corrected name from database
            year,
            round_num,
            pick.get('pick'),
            pick.get('protection'),
            origin_team_id,
            correct_origin_name,  # Use corrected origin name from database
            pick.get('source')  # JSON uses 'source'
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported {imported} draft picks (skipped {skipped})")

def import_standings(conn, cur):
    """Import standings with team references - replaces data only for teams in the new JSON"""
    json_file = Path('output/standings.json')
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    print(f"\nImporting standings from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        standings = json.load(f)
    
    # Use the default season from schema
    current_season = '2025-26'
    
    imported = 0
    skipped = 0
    
    for standing in standings:
        team_id = get_team_id(cur, standing.get('team', ''))
        if not team_id:
            skipped += 1
            continue
        
        # Get the correct team name from database
        cur.execute("SELECT team_name FROM teams WHERE team_id = %s", (team_id,))
        correct_team_name = cur.fetchone()[0]
        
        # Parse record to wins/losses
        record = standing.get('record', '')
        wins, losses = parse_record(record)
        
        if wins is None or losses is None:
            skipped += 1
            continue
        
        cur.execute("""
            INSERT INTO standings (
                team_id, team, conference, conference_rank,
                power_rank, wins, losses, source_filename, season
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (team_id, season) 
            DO UPDATE SET
                team = EXCLUDED.team,
                conference = EXCLUDED.conference,
                conference_rank = EXCLUDED.conference_rank,
                power_rank = EXCLUDED.power_rank,
                wins = EXCLUDED.wins,
                losses = EXCLUDED.losses,
                source_filename = EXCLUDED.source_filename,
                extracted_at = CURRENT_TIMESTAMP
        """, (
            team_id,
            correct_team_name,  # Use corrected name from database
            standing.get('conference'),
            standing.get('rank'),  # JSON uses 'rank'
            standing.get('power_rank'),
            wins,
            losses,
            standing.get('source'),  # JSON uses 'source'
            current_season
        ))
        imported += 1
    
    conn.commit()
    print(f"✓ Imported/Updated {imported} standings for season {current_season} (skipped {skipped})")

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
        
        # Show final counts and team coverage
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
        
        # Show team coverage
        print("\n" + "=" * 60)
        print("Team Coverage:")
        print("=" * 60)
        
        # Teams with roster data
        cur.execute("""
            SELECT DISTINCT t.team_name 
            FROM teams t 
            INNER JOIN roster_players rp ON t.team_id = rp.team_id 
            ORDER BY t.team_name
        """)
        teams_with_data = [row[0] for row in cur.fetchall()]
        print(f"Teams in database: {len(teams_with_data)} of 30")
        
        if len(teams_with_data) < 30:
            # Show missing teams
            cur.execute("""
                SELECT team_name FROM teams 
                WHERE team_id NOT IN (SELECT DISTINCT team_id FROM roster_players)
                ORDER BY team_name
            """)
            missing_teams = [row[0] for row in cur.fetchall()]
            if missing_teams:
                print(f"Teams missing roster data: {', '.join(missing_teams)}")
        
        print("\n✓ Import completed successfully!")
        print("✓ Per-team replacement: Only teams in new screenshots were updated")
        
    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
