#!/usr/bin/env python3
"""Interactive editor for roster_players.json - fix OCR errors and add missing data."""

import json
from pathlib import Path

ROSTER_FILE = Path("output/roster_players.json")

def load_roster():
    """Load roster from JSON file."""
    if not ROSTER_FILE.exists():
        print(f"Error: {ROSTER_FILE} not found. Run extract_roster_names.py first.")
        return None
    return json.loads(ROSTER_FILE.read_text(encoding="utf-8"))

def save_roster(roster):
    """Save roster to JSON file."""
    ROSTER_FILE.write_text(json.dumps(roster, indent=2), encoding="utf-8")
    print(f"\n✓ Saved to {ROSTER_FILE}")

def get_teams(roster):
    """Extract unique teams from roster."""
    teams = set()
    for player in roster:
        team = player.get("team", "Unknown")
        teams.add(team)
    return sorted(teams)

def filter_roster_by_team(roster, team_name):
    """Filter roster to only show players from a specific team."""
    return [p for p in roster if p.get("team", "Unknown") == team_name]

def display_roster(roster, team_name=None):
    """Display current roster with all player data."""
    print("\n" + "="*80)
    if team_name:
        print(f"ROSTER - {team_name}")
    else:
        print("ROSTER")
    print("="*80)
    print(f"{'#':<3} {'Name':<25} {'Team':<20} {'POS':<6} {'AGE':<5} {'OVR':<5} {'Δ':<4}")
    print("-"*80)
    
    for i, player in enumerate(roster, 1):
        name = player.get("name", "???")
        team = player.get("team", "Unknown")
        pos = player.get("pos", "?")
        age = str(player.get("age", "?"))
        ovr = str(player.get("ovr", "?"))
        delta = player.get("in_delta")
        delta_str = f"+{delta}" if delta and delta > 0 else str(delta) if delta else ""
        
        print(f"{i:<3} {name:<25} {team:<20} {pos:<6} {age:<5} {ovr:<5} {delta_str:<4}")
    
    # Count complete players
    complete = sum(1 for p in roster if p.get("pos") and p.get("age") and p.get("ovr"))
    print("-"*80)
    print(f"Total players: {len(roster)} (Complete: {complete}/{len(roster)})")

def find_player(roster, query):
    """Find a player by partial name match."""
    query_lower = query.lower()
    matches = [p for p in roster if query_lower in p["name"].lower()]
    return matches

def edit_player_field(roster):
    """Edit a player's field."""
    player_name = input("\nEnter player name (or part of it): ").strip()
    if not player_name:
        return
    
    matches = find_player(roster, player_name)
    
    if not matches:
        print(f"No player found matching '{player_name}'")
        return
    
    if len(matches) > 1:
        print(f"\nFound {len(matches)} players:")
        for i, player in enumerate(matches, 1):
            print(f"{i}. {player['name']} - POS:{player.get('pos','?')} AGE:{player.get('age','?')} OVR:{player.get('ovr','?')}")
        choice = input("Select player number: ").strip()
        try:
            player = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    else:
        player = matches[0]
    
    print(f"\nEditing: {player['name']}")
    print(f"  Position: {player.get('pos', 'N/A')}")
    print(f"  Age: {player.get('age', 'N/A')}")
    print(f"  Overall: {player.get('ovr', 'N/A')}")
    print(f"  Delta: {player.get('in_delta', 'N/A')}")
    
    print("\nWhich field to edit?")
    print("  1. Name")
    print("  2. Position")
    print("  3. Age")
    print("  4. Overall rating")
    print("  5. Rating delta")
    
    field_choice = input("Select field (1-5): ").strip()
    
    if field_choice == "1":
        new_value = input("Enter new name: ").strip()
        if new_value:
            player["name"] = new_value
            print(f"✓ Updated name to {new_value}")
    elif field_choice == "2":
        new_value = input("Enter new position (e.g., PG, SG, SF, PF, C): ").strip().upper()
        if new_value:
            player["pos"] = new_value
            print(f"✓ Updated position to {new_value}")
    elif field_choice == "3":
        new_value = input("Enter new age (18-45): ").strip()
        try:
            age = int(new_value)
            if 18 <= age <= 45:
                player["age"] = age
                print(f"✓ Updated age to {age}")
            else:
                print("Age must be between 18 and 45")
        except ValueError:
            print("Invalid age")
    elif field_choice == "4":
        new_value = input("Enter new overall rating (60-99): ").strip()
        try:
            ovr = int(new_value)
            if 60 <= ovr <= 99:
                player["ovr"] = ovr
                print(f"✓ Updated overall to {ovr}")
            else:
                print("Overall rating must be between 60 and 99")
        except ValueError:
            print("Invalid rating")
    elif field_choice == "5":
        new_value = input("Enter new rating delta (e.g., +3, -2, or 0): ").strip()
        try:
            delta = int(new_value.replace("+", ""))
            player["in_delta"] = delta
            print(f"✓ Updated delta to {delta:+d}" if delta != 0 else "✓ Updated delta to 0")
        except ValueError:
            print("Invalid delta")
    else:
        print("Invalid option")

def add_missing_player(roster, team_name=None):
    """Add a missing player."""
    print("\nAdd missing player:")
    
    name = input("Player name (e.g., J. Smith): ").strip()
    if not name:
        return
    
    if team_name:
        team = team_name
        print(f"Team: {team}")
    else:
        team = input("Team name: ").strip()
        if not team:
            team = "Unknown"
    
    pos = input("Position (PG/SG/SF/PF/C): ").strip().upper()
    if not pos:
        pos = None
    
    age_input = input("Age (18-45, or leave blank): ").strip()
    age = None
    if age_input:
        try:
            age = int(age_input)
            if not 18 <= age <= 45:
                print("Age must be between 18 and 45")
                return
        except ValueError:
            print("Invalid age")
            return
    
    ovr_input = input("Overall rating (60-99, or leave blank): ").strip()
    ovr = None
    if ovr_input:
        try:
            ovr = int(ovr_input)
            if not 60 <= ovr <= 99:
                print("Overall rating must be between 60 and 99")
                return
        except ValueError:
            print("Invalid rating")
            return
    
    delta_input = input("Rating delta (e.g., +3, -2, or leave blank): ").strip()
    delta = None
    if delta_input:
        try:
            delta = int(delta_input.replace("+", ""))
        except ValueError:
            print("Invalid delta")
            return
    
    new_player = {
        "name": name,
        "team": team,
        "pos": pos,
        "age": age,
        "ovr": ovr,
        "in_delta": delta,
        "source": "manual_edit"
    }
    
    roster.append(new_player)
    print(f"✓ Added {name}")

def remove_player(roster):
    """Remove a player from the roster."""
    player_name = input("\nEnter player name to remove: ").strip()
    if not player_name:
        return
    
    matches = find_player(roster, player_name)
    
    if not matches:
        print(f"No player found matching '{player_name}'")
        return
    
    if len(matches) > 1:
        print(f"\nFound {len(matches)} players:")
        for i, player in enumerate(matches, 1):
            print(f"{i}. {player['name']}")
        choice = input("Select player number to remove: ").strip()
        try:
            player = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    else:
        player = matches[0]
    
    confirm = input(f"Remove {player['name']}? (y/n): ").strip().lower()
    if confirm == "y":
        roster.remove(player)
        print(f"✓ Removed {player['name']}")

def sort_roster(roster):
    """Sort roster alphabetically by name."""
    roster.sort(key=lambda p: p["name"].lower())
    print("✓ Sorted roster alphabetically")

def team_menu(roster, team_name):
    """Menu for a specific team."""
    modified = False
    
    while True:
        team_roster = filter_roster_by_team(roster, team_name)
        display_roster(team_roster, team_name)
        
        print("\n" + "="*80)
        print("OPTIONS:")
        print("  1. Edit player field")
        print("  2. Add missing player")
        print("  3. Remove player")
        print("  4. Sort roster alphabetically")
        print("  5. Back to team selection")
        print("="*80)
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            edit_player_field(roster)
            modified = True
        elif choice == "2":
            add_missing_player(roster, team_name)
            modified = True
        elif choice == "3":
            remove_player(roster)
            modified = True
        elif choice == "4":
            sort_roster(roster)
            modified = True
        elif choice == "5":
            break
        else:
            print("Invalid option")
    
    return modified

def main():
    roster = load_roster()
    if roster is None:
        return
    
    modified = False
    
    while True:
        teams = get_teams(roster)
        
        print("\n" + "="*80)
        print("ROSTER EDITOR - TEAM SELECTION")
        print("="*80)
        print(f"Total players: {len(roster)}")
        print(f"Teams: {len(teams)}\n")
        
        for i, team in enumerate(teams, 1):
            team_count = len(filter_roster_by_team(roster, team))
            print(f"  {i}. {team} ({team_count} players)")
        
        print(f"\n  {len(teams)+1}. View all players")
        print(f"  {len(teams)+2}. Save and exit")
        print(f"  {len(teams)+3}. Exit without saving")
        print("="*80)
        
        choice = input("\nSelect team number: ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(teams):
                selected_team = teams[choice_num - 1]
                team_modified = team_menu(roster, selected_team)
                modified = modified or team_modified
            elif choice_num == len(teams) + 1:
                display_roster(roster)
                input("\nPress Enter to continue...")
            elif choice_num == len(teams) + 2:
                if modified:
                    save_roster(roster)
                else:
                    print("\nNo changes made.")
                break
            elif choice_num == len(teams) + 3:
                if modified:
                    confirm = input("\nDiscard changes? (y/n): ").strip().lower()
                    if confirm == "y":
                        print("Changes discarded.")
                        break
                else:
                    break
            else:
                print("Invalid option")
        except ValueError:
            print("Invalid input")

if __name__ == "__main__":
    main()
