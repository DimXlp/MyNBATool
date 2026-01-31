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

def display_roster(roster):
    """Display current roster with all player data."""
    print("\n" + "="*80)
    print("ROSTER")
    print("="*80)
    print(f"{'#':<3} {'Name':<25} {'POS':<6} {'AGE':<5} {'OVR':<5} {'Δ':<4}")
    print("-"*80)
    
    for i, player in enumerate(roster, 1):
        name = player.get("name", "???")
        pos = player.get("pos", "?")
        age = str(player.get("age", "?"))
        ovr = str(player.get("ovr", "?"))
        delta = player.get("in_delta")
        delta_str = f"+{delta}" if delta and delta > 0 else str(delta) if delta else ""
        
        print(f"{i:<3} {name:<25} {pos:<6} {age:<5} {ovr:<5} {delta_str:<4}")
    
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

def add_missing_player(roster):
    """Add a missing player."""
    print("\nAdd missing player:")
    
    name = input("Player name (e.g., J. Smith): ").strip()
    if not name:
        return
    
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

def main():
    roster = load_roster()
    if roster is None:
        return
    
    modified = False
    
    while True:
        display_roster(roster)
        
        print("\n" + "="*80)
        print("OPTIONS:")
        print("  1. Edit player field")
        print("  2. Add missing player")
        print("  3. Remove player")
        print("  4. Sort roster alphabetically")
        print("  5. Save and exit")
        print("  6. Exit without saving")
        print("="*80)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            edit_player_field(roster)
            modified = True
        elif choice == "2":
            add_missing_player(roster)
            modified = True
        elif choice == "3":
            remove_player(roster)
            modified = True
        elif choice == "4":
            sort_roster(roster)
            modified = True
        elif choice == "5":
            if modified:
                save_roster(roster)
            else:
                print("\nNo changes made.")
            break
        elif choice == "6":
            if modified:
                confirm = input("\nDiscard changes? (y/n): ").strip().lower()
                if confirm == "y":
                    print("Changes discarded.")
                    break
            else:
                break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
