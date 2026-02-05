#!/usr/bin/env python3
"""
Export complete NBA 2K26 league state for ChatGPT GM assistant
Generates separate files for standings, rosters, contracts, draft picks
"""

import db_config
from pathlib import Path

def export_league_state(output_dir='league_exports'):
    """Export complete league state to separate text files for ChatGPT"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    files_created = []
    
    files_created = []
    
    # ========================================================================
    # 1. STANDINGS
    # ========================================================================
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - CURRENT STANDINGS")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT conference, conference_rank, team, wins, losses, win_percentage
        FROM standings_detailed
        ORDER BY conference, conference_rank
    """)
    
    current_conf = None
    for row in cur.fetchall():
        conf, rank, team, wins, losses, pct = row
        if conf != current_conf:
            output.append(f"\n{conf} Conference:")
            output.append("-" * 60)
            current_conf = conf
        output.append(f"{rank:2}. {team:25} {wins:2}-{losses:2} ({pct:.3f})")
    
    output.append("")
    standings_file = output_path / "1_standings.txt"
    standings_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(standings_file)
    
    # ========================================================================
    # 2. SALARY CAP SUMMARY
    # ========================================================================
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - TEAM SALARY CAP SUMMARY")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT team, player_count, total_salary, avg_salary, max_salary
        FROM team_salary_summary
        ORDER BY total_salary DESC
    """)
    
    output.append(f"{'Team':30} {'Players':8} {'Total $':10} {'Avg $':10} {'Max $':10}")
    output.append("-" * 80)
    for row in cur.fetchall():
        team, count, total, avg, max_sal = row
        output.append(f"{team:30} {count:8} ${total:9.2f}M ${avg:9.2f}M ${max_sal:9.2f}M")
    
    output.append("")
    salary_file = output_path / "2_salary_cap.txt"
    salary_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(salary_file)
    
    salary_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(salary_file)
    
    # ========================================================================
    # 3. ALL TEAM ROSTERS
    # ========================================================================
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - ALL TEAM ROSTERS & CONTRACTS")
    output.append("=" * 80)
    output.append("")
    
    # Get all teams
    cur.execute("SELECT team_name, abbreviation FROM teams ORDER BY team_name")
    teams = cur.fetchall()
    
    for team_name, abbr in teams:
        output.append("")
        output.append("=" * 80)
        output.append(f"{team_name} ({abbr})")
        output.append("=" * 80)
        
        # Get roster
        cur.execute("""
            SELECT name, position, age, overall_rating, delta, delta_string,
                   salary, contract_option, signing_status, extension_status, no_trade_clause
            FROM player_complete_info
            WHERE team = %s
            ORDER BY overall_rating DESC NULLS LAST, name
        """, (team_name,))
        
        players = cur.fetchall()
        
        if not players:
            output.append("  (No roster data)")
        else:
            output.append(f"  {'Player':20} {'Pos':3} {'Age':3} {'OVR':3} {'Delta':10} {'Salary':10} {'Option':12} {'Status':15} {'Extension':20} {'NTC':3}")
            output.append("  " + "-" * 110)
            
            for p in players:
                name, pos, age, ovr, delta, delta_str, salary, opt, sign, ext, ntc = p
                delta_display = delta_str if delta_str else (f"{delta:+d}" if delta else "-")
                salary_str = salary if salary else "-"
                opt_str = opt if opt else "-"
                sign_str = sign if sign else "-"
                ext_str = ext if ext else "-"
                ntc_str = "YES" if ntc else "NO"
                
                output.append(f"  {name:20} {pos or '-':3} {age or '-':3} {ovr or '-':3} {delta_display:10} {salary_str:10} {opt_str:12} {sign_str:15} {ext_str:20} {ntc_str:3}")
    
    output.append("")
    rosters_file = output_path / "3_rosters.txt"
    rosters_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(rosters_file)
    
    rosters_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(rosters_file)
    
    # ========================================================================
    # 4. ALL DRAFT PICKS (AS SHOWN IN SCREENSHOTS)
    # ========================================================================
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - ALL TEAM DRAFT PICKS")
    output.append("=" * 80)
    output.append("")
    
    # Get all teams
    cur.execute("SELECT team_name, abbreviation FROM teams ORDER BY team_name")
    teams = cur.fetchall()
    
    for team_name, abbr in teams:
        output.append("")
        output.append("=" * 80)
        output.append(f"{team_name} ({abbr})")
        output.append("=" * 80)
        
        # Get team's draft picks - raw data as in screenshots
        cur.execute("""
            SELECT dp.draft_year, dp.round, dp.pick_number, dp.protection, ot.abbreviation as origin_abbr
            FROM draft_picks dp
            LEFT JOIN teams t ON dp.team_id = t.team_id
            LEFT JOIN teams ot ON dp.origin_team_id = ot.team_id
            WHERE t.team_name = %s
            ORDER BY dp.draft_year, dp.round, dp.pick_number NULLS LAST
        """, (team_name,))
        
        picks = cur.fetchall()
        
        if not picks:
            output.append("  (No draft picks)")
        else:
            output.append(f"  {'Year':6} {'Round':5} {'Pick':10} {'Protection':25} {'Origin':10}")
            output.append("  " + "-" * 65)
            
            for year, round_num, pick_num, protection, origin in picks:
                round_str = "1st" if round_num == 1 else "2nd"
                pick_str = f"#{pick_num}" if pick_num else "#?"
                prot_str = protection if protection else "-"
                origin_str = origin if origin else "-"
                
                output.append(f"  {year:<6} {round_str:<5} {pick_str:<10} {prot_str:<25} {origin_str:<10}")
        
        output.append("")
    
    output.append("")
    draft_file = output_path / "4_draft_picks.txt"
    draft_file.write_text("\n".join(output), encoding='utf-8')
    files_created.append(draft_file)
    
    cur.close()
    conn.close()
    
    return files_created

def main():
    """Main export function"""
    print("=" * 60)
    print("NBA 2K26 League State Export")
    print("=" * 60)
    print()
    print("Connecting to database...")
    
    try:
        files = export_league_state()
        
        print(f"✓ League state exported to {len(files)} files:")
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
        print("2. Copy files to ChatGPT:")
        print()
        print("   Example prompt:")
        print()
        print('   "You are the GM of the New York Knicks in NBA 2K26.')
        print()
        print('    STANDINGS:')
        print('    [paste 1_standings.txt]')
        print()
        print('    ALL ROSTERS:')
        print('    [paste 3_rosters.txt]')
        print()
        print('    ALL DRAFT PICKS:')
        print('    [paste 4_draft_picks.txt]')
        print()
        print('    Analyze our team and suggest moves."')
        print()
        print("Files:")
        print("  1_standings.txt   - Current standings")
        print("  2_salary_cap.txt  - Team salary summaries")
        print("  3_rosters.txt     - All team rosters & contracts")
        print("  4_draft_picks.txt - All team draft picks")
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
