# edit_draft_picks.py
"""Interactive editor for draft pick data extracted from NBA 2K26 screenshots."""

import json
from pathlib import Path
from typing import Dict, Any, List

OUTPUT_DIR = Path("output")
DRAFT_PICKS_FILE = OUTPUT_DIR / "draft_picks.json"
TEAMS_DIR = OUTPUT_DIR / "teams_draft_picks"

def load_draft_picks() -> List[Dict[str, Any]]:
    """Load draft picks from JSON file."""
    if not DRAFT_PICKS_FILE.exists():
        print(f"ERROR: {DRAFT_PICKS_FILE} not found. Run extract_draft_picks.py first.")
        exit(1)
    
    return json.loads(DRAFT_PICKS_FILE.read_text(encoding="utf-8"))

def get_teams(picks: List[Dict[str, Any]]) -> List[str]:
    """Extract unique teams from draft picks."""
    teams = set()
    for pick in picks:
        team = pick.get("team", "Unknown")
        teams.add(team)
    return sorted(teams)

def filter_picks_by_team(picks: List[Dict[str, Any]], team_name: str) -> List[Dict[str, Any]]:
    """Filter picks to only show ones from a specific team."""
    return [p for p in picks if p.get("team", "Unknown") == team_name]

def save_draft_picks(picks: List[Dict[str, Any]]) -> None:
    """Save draft picks to JSON file."""
    DRAFT_PICKS_FILE.write_text(json.dumps(picks, indent=2), encoding="utf-8")
    
    # Also update per-team files
    TEAMS_DIR.mkdir(parents=True, exist_ok=True)
    picks_by_team = {}
    for pick in picks:
        team = pick.get("team", "Unknown")
        if team not in picks_by_team:
            picks_by_team[team] = []
        picks_by_team[team].append(pick)
    
    for team, team_picks in picks_by_team.items():
        team_file = TEAMS_DIR / f"{team}.json"
        team_file.write_text(json.dumps(team_picks, indent=2), encoding="utf-8")
    
    print(f"✓ Saved to {DRAFT_PICKS_FILE} and team files")

def display_pick(pick: Dict[str, Any], idx: int = None) -> None:
    """Display a single draft pick's details."""
    prefix = f"{idx}. " if idx is not None else ""
    year = pick.get('year', 'N/A')
    round_type = pick.get('round', 'N/A')
    pick_num = pick.get('pick', 'N/A')
    protection = pick.get('protection', 'None')
    origin = pick.get('origin', 'N/A')
    
    print(f"{prefix}{year} {round_type} {f'#{pick_num}' if pick_num else ''} - Origin: {origin} - Protection: {protection}")

def display_picks_table(picks: List[Dict[str, Any]]) -> None:
    """Display draft picks in a table format."""
    if not picks:
        print("No draft picks found.")
        return
    
    print(f"\n{'#':<4} {'Year':<6} {'Round':<6} {'Pick':<6} {'Protection':<30} {'Origin':<15}")
    print("=" * 75)
    
    for idx, pick in enumerate(picks, 1):
        year = pick.get('year', 'N/A')
        round_type = pick.get('round', 'N/A')
        pick_num = pick.get('pick') or '-'
        protection = pick.get('protection') or 'None'
        origin = pick.get('origin', 'N/A')
        
        # Truncate protection if too long
        if len(protection) > 28:
            protection = protection[:25] + "..."
        
        print(f"{idx:<4} {year:<6} {round_type:<6} {pick_num:<6} {protection:<30} {origin:<15}")

def search_picks(picks: List[Dict[str, Any]], query: str) -> List[int]:
    """Search for draft picks by year, round, origin, etc. Returns list of indices."""
    query_lower = query.lower()
    matches = []
    
    for i, pick in enumerate(picks):
        year = str(pick.get("year", "")).lower()
        round_type = str(pick.get("round", "")).lower()
        origin = str(pick.get("origin", "")).lower()
        protection = str(pick.get("protection", "")).lower()
        
        if (query_lower in year or query_lower in round_type or 
            query_lower in origin or query_lower in protection):
            matches.append(i)
    
    return matches

def edit_pick_field(pick: Dict[str, Any], field: str) -> None:
    """Edit a specific field of a draft pick."""
    current = pick.get(field, "N/A")
    print(f"Current {field}: {current}")
    
    if field == "year":
        print("Enter year (e.g., 2028):")
        new_value = input("> ").strip()
        pick[field] = new_value if new_value else None
    
    elif field == "round":
        print("Enter round (1st or 2nd):")
        new_value = input("> ").strip()
        pick[field] = new_value if new_value else None
    
    elif field == "pick":
        print("Enter pick number (leave empty if unknown):")
        new_value = input("> ").strip()
        pick[field] = int(new_value) if new_value.isdigit() else None
    
    elif field == "protection":
        print("Enter protection (e.g., 'Lottery Protected', 'Top 10 Protected', 'Swap Best with Lakers'):")
        print("Or leave empty for no protection:")
        new_value = input("> ").strip()
        pick[field] = new_value if new_value else None
    
    elif field == "origin":
        print("Enter origin team (which team originally owned this pick):")
        new_value = input("> ").strip()
        pick[field] = new_value if new_value else None
    
    else:
        print(f"Unknown field: {field}")

def add_pick_interactive(team_name: str) -> Dict[str, Any]:
    """Interactively create a new draft pick."""
    print("\n=== Add New Draft Pick ===")
    
    year = input("Year (e.g., 2028): ").strip()
    round_type = input("Round (1st or 2nd): ").strip()
    pick_num = input("Pick number (leave empty if unknown): ").strip()
    protection = input("Protection (leave empty for none): ").strip()
    origin = input("Origin team (which team originally owned this): ").strip()
    
    return {
        "team": team_name,
        "year": year if year else None,
        "round": round_type if round_type else None,
        "pick": int(pick_num) if pick_num.isdigit() else None,
        "protection": protection if protection else None,
        "origin": origin if origin else None,
        "source": "manual_entry"
    }

def edit_pick_menu(picks: List[Dict[str, Any]], idx: int) -> bool:
    """Edit menu for a single draft pick. Returns True if pick was deleted."""
    if idx < 0 or idx >= len(picks):
        print("Invalid pick index.")
        return False
    
    pick = picks[idx]
    
    while True:
        print("\n" + "=" * 60)
        display_pick(pick)
        print("=" * 60)
        print("\nEdit options:")
        print("  1. Year")
        print("  2. Round")
        print("  3. Pick number")
        print("  4. Protection")
        print("  5. Origin")
        print("  d. Delete this pick")
        print("  b. Back to team menu")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == "1":
            edit_pick_field(pick, "year")
        elif choice == "2":
            edit_pick_field(pick, "round")
        elif choice == "3":
            edit_pick_field(pick, "pick")
        elif choice == "4":
            edit_pick_field(pick, "protection")
        elif choice == "5":
            edit_pick_field(pick, "origin")
        elif choice == "d":
            confirm = input("Delete this pick? (y/n): ").strip().lower()
            if confirm == "y":
                picks.remove(pick)
                print("✓ Pick deleted")
                return True
        elif choice == "b":
            return False
        else:
            print("Invalid choice.")

def team_menu(picks: List[Dict[str, Any]], team_name: str) -> None:
    """Menu for editing a specific team's draft picks."""
    while True:
        team_picks = filter_picks_by_team(picks, team_name)
        
        # Sort by year, then round
        team_picks.sort(key=lambda p: (
            p.get('year', '9999'),
            0 if p.get('round') == '1st' else 1
        ))
        
        print(f"\n{'=' * 60}")
        print(f"Team: {team_name} - {len(team_picks)} draft picks")
        print("=" * 60)
        
        display_picks_table(team_picks)
        
        print("\nOptions:")
        print("  [number] - Edit pick")
        print("  a - Add new pick")
        print("  s - Search picks")
        print("  sort - Sort by year")
        print("  save - Save changes")
        print("  b - Back to team selection")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(team_picks):
                # Find the actual index in the main picks list
                actual_idx = picks.index(team_picks[idx])
                edit_pick_menu(picks, actual_idx)
            else:
                print("Invalid pick number.")
        
        elif choice == "a":
            new_pick = add_pick_interactive(team_name)
            picks.append(new_pick)
            print("✓ Pick added")
        
        elif choice == "s":
            query = input("Search (year/round/origin/protection): ").strip()
            matches = search_picks(team_picks, query)
            if matches:
                print(f"\nFound {len(matches)} matches:")
                for i in matches:
                    display_pick(team_picks[i], i + 1)
            else:
                print("No matches found.")
        
        elif choice == "sort":
            print("✓ Sorted by year and round")
        
        elif choice == "save":
            save_draft_picks(picks)
        
        elif choice == "b":
            break
        
        else:
            print("Invalid choice.")

def main_menu() -> None:
    """Main menu for draft pick editor."""
    picks = load_draft_picks()
    teams = get_teams(picks)
    
    print("=" * 60)
    print("NBA 2K26 Draft Picks Editor")
    print("=" * 60)
    
    while True:
        print(f"\n{len(teams)} teams with draft picks:")
        for i, team in enumerate(teams, 1):
            team_picks = filter_picks_by_team(picks, team)
            print(f"  {i}. {team} ({len(team_picks)} picks)")
        
        print("\nOptions:")
        print("  [number] - Select team")
        print("  save - Save all changes")
        print("  q - Quit")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(teams):
                team_menu(picks, teams[idx])
            else:
                print("Invalid team number.")
        
        elif choice == "save":
            save_draft_picks(picks)
        
        elif choice == "q":
            save_prompt = input("Save changes before quitting? (y/n): ").strip().lower()
            if save_prompt == "y":
                save_draft_picks(picks)
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()
