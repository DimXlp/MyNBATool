#!/usr/bin/env python3
"""
Export NBA 2K26 league state to multiple organized text files
Each file contains a specific category of data for easier ChatGPT consumption
"""

import db_config
from pathlib import Path

def export_standings(output_dir):
    """Export current standings"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - CURRENT STANDINGS")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT conference, conference_rank, team, wins, losses, win_percentage, games_played, games_remaining
        FROM standings_detailed
        ORDER BY conference, conference_rank
    """)
    
    current_conf = None
    for row in cur.fetchall():
        conf, rank, team, wins, losses, pct, played, remaining = row
        if conf != current_conf:
            output.append(f"\n{conf} Conference:")
            output.append("-" * 70)
            current_conf = conf
        output.append(f"{rank:2}. {team:25} {wins:2}-{losses:2} ({pct:.3f})  [{played} played, {remaining} remaining]")
    
    filename = output_dir / "1_standings.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_salary_cap(output_dir):
    """Export salary cap summary"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - TEAM SALARY CAP SUMMARY")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT team, team_abbr, player_count, total_salary, avg_salary, max_salary, min_salary
        FROM team_salary_summary
        ORDER BY total_salary DESC
    """)
    
    output.append(f"{'Team':30} {'Abbr':4} {'Players':7} {'Total $':10} {'Avg $':10} {'Max $':10} {'Min $':10}")
    output.append("-" * 90)
    for row in cur.fetchall():
        team, abbr, count, total, avg, max_sal, min_sal = row
        output.append(f"{team:30} {abbr:4} {count:7} ${total:9.2f}M ${avg:9.2f}M ${max_sal:9.2f}M ${min_sal:9.2f}M")
    
    filename = output_dir / "2_salary_cap.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_all_rosters(output_dir):
    """Export all team rosters with contracts"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - ALL TEAM ROSTERS & CONTRACTS")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("SELECT team_name, abbreviation FROM teams ORDER BY team_name")
    teams = cur.fetchall()
    
    for team_name, abbr in teams:
        output.append("")
        output.append("=" * 80)
        output.append(f"{team_name} ({abbr})")
        output.append("=" * 80)
        
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
            output.append(f"  {'Player':20} {'Pos':3} {'Age':3} {'OVR':3} {'Inj':10} {'Salary':10} {'Option':12} {'Status':15} {'Extension':20} {'NTC':3}")
            output.append("  " + "-" * 110)
            
            for p in players:
                name, pos, age, ovr, delta, delta_str, salary, opt, sign, ext, ntc = p
                inj = delta_str if delta_str else (f"{delta:+d}" if delta else "-")
                salary_str = salary if salary else "-"
                opt_str = opt if opt else "-"
                sign_str = sign if sign else "-"
                ext_str = ext if ext else "-"
                ntc_str = "YES" if ntc else "NO"
                
                output.append(f"  {name:20} {pos or '-':3} {age or '-':3} {ovr or '-':3} {inj:10} {salary_str:10} {opt_str:12} {sign_str:15} {ext_str:20} {ntc_str:3}")
    
    filename = output_dir / "3_all_rosters.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_draft_picks(output_dir):
    """Export all draft picks by team"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - DRAFT PICKS BY TEAM")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("SELECT team_name FROM teams ORDER BY team_name")
    teams = cur.fetchall()
    
    for (team_name,) in teams:
        cur.execute("""
            SELECT draft_year, total_picks, first_round_picks, second_round_picks, pick_details
            FROM draft_picks_inventory
            WHERE team = %s
            ORDER BY draft_year
        """, (team_name,))
        
        picks = cur.fetchall()
        
        if picks:
            output.append(f"\n{team_name}:")
            output.append("-" * 70)
            for year, total, first, second, details in picks:
                output.append(f"  {year}: {total} picks ({first} 1st, {second} 2nd)")
                output.append(f"       {details}")
        else:
            output.append(f"\n{team_name}:")
            output.append("-" * 70)
            output.append("  (No draft picks data)")
    
    output.append("")
    output.append("")
    output.append("=" * 80)
    output.append("DRAFT PICKS BY YEAR")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT draft_year, team, origin_team, round, pick_number, protection
        FROM draft_picks
        ORDER BY draft_year, round, pick_number NULLS LAST
    """)
    
    current_year = None
    for row in cur.fetchall():
        year, team, origin, round_num, pick_num, protection = row
        if year != current_year:
            output.append(f"\n{year} Draft:")
            output.append("-" * 70)
            current_year = year
        
        round_str = "1st" if round_num == 1 else "2nd"
        pick_str = f"#{pick_num}" if pick_num else "#?"
        prot_str = f" ({protection})" if protection else ""
        output.append(f"  {team:25} owns {round_str} {pick_str:5} from {origin:20}{prot_str}")
    
    filename = output_dir / "4_draft_picks.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_free_agents(output_dir):
    """Export expiring contracts and potential free agents"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - EXPIRING CONTRACTS / POTENTIAL FREE AGENTS")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("""
        SELECT team, name, position, age, overall_rating, salary, signing_status, contract_option
        FROM player_complete_info
        WHERE signing_status LIKE '%1+1%' OR signing_status LIKE '%Expiring%'
        ORDER BY overall_rating DESC NULLS LAST
    """)
    
    expiring = cur.fetchall()
    
    if expiring:
        output.append(f"{'Team':25} {'Player':20} {'Pos':3} {'Age':3} {'OVR':3} {'Salary':10} {'Status':15} {'Option':12}")
        output.append("-" * 100)
        for team, name, pos, age, ovr, salary, status, option in expiring:
            output.append(f"{team:25} {name:20} {pos or '-':3} {age or '-':3} {ovr or '-':3} {salary or '-':10} {status or '-':15} {option or '-':12}")
    else:
        output.append("  (No expiring contracts found)")
    
    filename = output_dir / "5_free_agents.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_trade_assets(output_dir):
    """Export top trade assets by team"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("NBA 2K26 - TOP TRADE ASSETS BY TEAM")
    output.append("=" * 80)
    output.append("")
    
    cur.execute("SELECT team_name FROM teams ORDER BY team_name")
    
    for (team_name,) in cur.fetchall():
        cur.execute("""
            SELECT name, position, age, overall_rating, salary, no_trade_clause
            FROM player_complete_info
            WHERE team = %s
            ORDER BY overall_rating DESC NULLS LAST
            LIMIT 5
        """, (team_name,))
        
        top_players = cur.fetchall()
        
        cur.execute("""
            SELECT COUNT(*) FROM draft_picks 
            WHERE team_id = (SELECT team_id FROM teams WHERE team_name = %s)
            AND round = 1
        """, (team_name,))
        first_round_count = cur.fetchone()[0]
        
        if top_players:
            output.append(f"\n{team_name}:")
            output.append("-" * 70)
            output.append("  Top Players:")
            for name, pos, age, ovr, salary, ntc in top_players:
                ntc_str = " [NTC]" if ntc else ""
                output.append(f"    {name:20} {pos or '-':3} Age:{age or '-':3} OVR:{ovr or '-':3} {salary or '-':10}{ntc_str}")
            output.append(f"  Draft Capital: {first_round_count} first round picks")
    
    filename = output_dir / "6_trade_assets.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def export_specific_team(team_name, output_dir):
    """Export detailed info for a specific team"""
    conn = db_config.get_connection()
    cur = conn.cursor()
    
    # Normalize team name
    cur.execute("""
        SELECT team_name, abbreviation FROM teams 
        WHERE team_name ILIKE %s OR abbreviation ILIKE %s
    """, (f"%{team_name}%", team_name))
    
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return None
    
    full_team_name, abbr = result
    
    output = []
    output.append("=" * 80)
    output.append(f"{full_team_name} ({abbr}) - COMPLETE TEAM REPORT")
    output.append("=" * 80)
    output.append("")
    
    # Standings
    output.append("STANDINGS:")
    output.append("-" * 70)
    cur.execute("""
        SELECT conference_rank, wins, losses, win_percentage, conference
        FROM standings_detailed
        WHERE team = %s
    """, (full_team_name,))
    
    standing = cur.fetchone()
    if standing:
        rank, wins, losses, pct, conf = standing
        output.append(f"  {conf} Conference: #{rank}")
        output.append(f"  Record: {wins}-{losses} ({pct:.3f})")
    
    output.append("")
    
    # Roster
    output.append("ROSTER:")
    output.append("-" * 70)
    cur.execute("""
        SELECT name, position, age, overall_rating, delta, delta_string,
               salary, contract_option, signing_status, extension_status, no_trade_clause
        FROM player_complete_info
        WHERE team = %s
        ORDER BY overall_rating DESC NULLS LAST
    """, (full_team_name,))
    
    output.append(f"  {'Player':20} {'Pos':3} {'Age':3} {'OVR':3} {'Inj':10} {'Salary':10} {'Option':12} {'Status':15} {'Extension':20} {'NTC':3}")
    output.append("  " + "-" * 110)
    for p in cur.fetchall():
        name, pos, age, ovr, delta, delta_str, salary, opt, sign, ext, ntc = p
        inj = delta_str if delta_str else (f"{delta:+d}" if delta else "-")
        output.append(f"  {name:20} {pos or '-':3} {age or '-':3} {ovr or '-':3} {inj:10} {salary or '-':10} {opt or '-':12} {sign or '-':15} {ext or '-':20} {'YES' if ntc else 'NO':3}")
    
    output.append("")
    
    # Salary Cap
    output.append("SALARY CAP:")
    output.append("-" * 70)
    cur.execute("""
        SELECT player_count, total_salary, avg_salary, max_salary, min_salary
        FROM team_salary_summary
        WHERE team = %s
    """, (full_team_name,))
    
    sal = cur.fetchone()
    if sal:
        count, total, avg, max_sal, min_sal = sal
        output.append(f"  Players: {count}")
        output.append(f"  Total Salary: ${total:.2f}M")
        output.append(f"  Average Salary: ${avg:.2f}M")
        output.append(f"  Highest Paid: ${max_sal:.2f}M")
        output.append(f"  Lowest Paid: ${min_sal:.2f}M")
    
    output.append("")
    
    # Draft Picks
    output.append("DRAFT PICKS:")
    output.append("-" * 70)
    cur.execute("""
        SELECT draft_year, total_picks, first_round_picks, second_round_picks, pick_details
        FROM draft_picks_inventory
        WHERE team = %s
        ORDER BY draft_year
    """, (full_team_name,))
    
    picks = cur.fetchall()
    if picks:
        for year, total, first, second, details in picks:
            output.append(f"  {year}: {total} picks ({first} 1st, {second} 2nd)")
            output.append(f"       {details}")
    else:
        output.append("  (No draft picks data)")
    
    filename = output_dir / f"TEAM_{abbr}_{full_team_name.replace(' ', '_')}.txt"
    filename.write_text("\n".join(output), encoding='utf-8')
    cur.close()
    conn.close()
    return filename

def main():
    """Main export function"""
    print("=" * 70)
    print("NBA 2K26 League State Export - Multiple Files")
    print("=" * 70)
    print()
    
    # Create output directory
    output_dir = Path("league_exports")
    output_dir.mkdir(exist_ok=True)
    
    try:
        print("Exporting league data...")
        print()
        
        files = []
        
        print("  📊 Exporting standings...")
        files.append(export_standings(output_dir))
        
        print("  💰 Exporting salary cap...")
        files.append(export_salary_cap(output_dir))
        
        print("  👥 Exporting all rosters...")
        files.append(export_all_rosters(output_dir))
        
        print("  🎯 Exporting draft picks...")
        files.append(export_draft_picks(output_dir))
        
        print("  🆓 Exporting free agents...")
        files.append(export_free_agents(output_dir))
        
        print("  🔄 Exporting trade assets...")
        files.append(export_trade_assets(output_dir))
        
        print()
        print("✓ Export complete!")
        print()
        print("=" * 70)
        print("FILES CREATED:")
        print("=" * 70)
        for f in files:
            size = f.stat().st_size
            print(f"  {f.name:30} ({size:,} bytes)")
        
        print()
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print()
        print("Files are in the 'league_exports' folder.")
        print()
        print("To use with ChatGPT:")
        print("  1. Copy the relevant files based on what you need")
        print("  2. Paste into ChatGPT with:")
        print()
        print('     "You are the GM of the New York Knicks.')
        print('      Here is the current league data:')
        print('      [paste file contents]')
        print()
        print('      Suggest trades to improve our team."')
        print()
        
        # Ask if user wants specific team exports
        print("=" * 70)
        print("Generate specific team report? (e.g., 'Knicks', 'Lakers', or 'skip')")
        team = input("Team name: ").strip()
        
        if team and team.lower() != 'skip':
            print(f"\n  📋 Generating {team} team report...")
            team_file = export_specific_team(team, output_dir)
            if team_file:
                print(f"  ✓ Created: {team_file.name}")
            else:
                print(f"  ✗ Team '{team}' not found")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
