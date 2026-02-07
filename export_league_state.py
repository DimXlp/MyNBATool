#!/usr/bin/env python3
"""
Export complete NBA 2K26 league state for ChatGPT GM assistant
Generates CSV files for faster parsing (standings, rosters, contracts, draft picks)
"""

import db_config
import csv
from pathlib import Path

def export_league_state(output_dir='league_exports'):
    """Export complete league state to CSV files for ChatGPT"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    files_created = []
    
    # ========================================================================
    # 1. STANDINGS
    # ========================================================================
    standings_file = output_path / "1_standings.csv"
    with open(standings_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Conference', 'Rank', 'Team', 'Wins', 'Losses', 'Win_Pct'])
        
        cur.execute("""
            SELECT conference, conference_rank, team, wins, losses, win_percentage
            FROM standings_detailed
            ORDER BY conference, conference_rank
        """)
        
        writer.writerows(cur.fetchall())
    
    files_created.append(standings_file)
    
    # ========================================================================
    # 2. SALARY CAP SUMMARY
    # ========================================================================
    salary_file = output_path / "2_salary_cap.csv"
    with open(salary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'Player_Count', 'Total_Salary_M', 'Avg_Salary_M', 'Max_Salary_M'])
        
        cur.execute("""
            SELECT team, player_count, total_salary, avg_salary, max_salary
            FROM team_salary_summary
            ORDER BY total_salary DESC
        """)
        
        writer.writerows(cur.fetchall())
    
    files_created.append(salary_file)
    
    # ========================================================================
    # 3. ALL TEAM ROSTERS WITH CONTRACTS
    # ========================================================================
    rosters_file = output_path / "3_rosters.csv"
    with open(rosters_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'Team_Abbr', 'Player', 'Position', 'Age', 'OVR', 'Delta', 
                        'Salary', 'Contract_Option', 'Signing_Status', 'Extension_Status', 'No_Trade_Clause'])
        
        # Get all teams
        cur.execute("SELECT team_name, abbreviation FROM teams ORDER BY team_name")
        teams = cur.fetchall()
        
        for team_name, abbr in teams:
            # Get roster
            cur.execute("""
                SELECT name, position, age, overall_rating, delta, delta_string,
                       salary, contract_option, signing_status, extension_status, no_trade_clause
                FROM player_complete_info
                WHERE team = %s
                ORDER BY overall_rating DESC NULLS LAST, name
            """, (team_name,))
            
            players = cur.fetchall()
            
            for p in players:
                name, pos, age, ovr, delta, delta_str, salary, opt, sign, ext, ntc = p
                delta_display = delta_str if delta_str else (f"{delta:+d}" if delta else "")
                ntc_value = "YES" if ntc else "NO"
                
                writer.writerow([
                    team_name, abbr, name, pos or '', age or '', ovr or '', delta_display,
                    salary or '', opt or '', sign or '', ext or '', ntc_value
                ])
    
    files_created.append(rosters_file)
    
    # ========================================================================
    # 4. ALL DRAFT PICKS
    # ========================================================================
    draft_file = output_path / "4_draft_picks.csv"
    with open(draft_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'Team_Abbr', 'Year', 'Round', 'Pick_Number', 'Protection', 'Origin_Team'])
        
        # Get all teams
        cur.execute("SELECT team_name, abbreviation FROM teams ORDER BY team_name")
        teams = cur.fetchall()
        
        for team_name, abbr in teams:
            # Get team's draft picks
            cur.execute("""
                SELECT dp.draft_year, dp.round, dp.pick_number, dp.protection, ot.abbreviation as origin_abbr
                FROM draft_picks dp
                LEFT JOIN teams t ON dp.team_id = t.team_id
                LEFT JOIN teams ot ON dp.origin_team_id = ot.team_id
                WHERE t.team_name = %s
                ORDER BY dp.draft_year, dp.round, dp.pick_number NULLS LAST
            """, (team_name,))
            
            picks = cur.fetchall()
            
            for year, round_num, pick_num, protection, origin in picks:
                round_str = "1st" if round_num == 1 else "2nd"
                
                writer.writerow([
                    team_name, abbr, year, round_str, pick_num or '', 
                    protection or '', origin or ''
                ])
    
    files_created.append(draft_file)
    
    cur.close()
    conn.close()
    
    return files_created

def main():
    """Main export function"""
    print("=" * 60)
    print("NBA 2K26 League State Export (CSV Format)")
    print("=" * 60)
    print()
    print("Connecting to database...")
    
    try:
        files = export_league_state()
        
        print(f"✓ League state exported to {len(files)} CSV files:")
        print()
        for f in files:
            size = f.stat().st_size
            print(f"  - {f.name:30} ({size:,} bytes)")
        
        print()
        print("=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print()
        print("1. Open league_exports/ folder")
        print("2. Copy CSV files to ChatGPT (faster parsing than TXT):")
        print()
        print("   Example prompt:")
        print()
        print('   "You are the GM of the New York Knicks in NBA 2K26.')
        print()
        print('    STANDINGS (CSV):')
        print('    [paste 1_standings.csv contents]')
        print()
        print('    ALL ROSTERS (CSV):')
        print('    [paste 3_rosters.csv contents]')
        print()
        print('    ALL DRAFT PICKS (CSV):')
        print('    [paste 4_draft_picks.csv contents]')
        print()
        print('    Analyze our team and suggest moves."')
        print()
        print("Files:")
        print("  1_standings.csv   - Current standings")
        print("  2_salary_cap.csv  - Team salary summaries")
        print("  3_rosters.csv     - All team rosters & contracts")
        print("  4_draft_picks.csv - All team draft picks")
        print()
        print("Benefits of CSV format:")
        print("  - Faster parsing by ChatGPT/Claude")
        print("  - No decorative separators")
        print("  - Clean delimited data")
        print("  - Easy to open in Excel/Google Sheets")
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
