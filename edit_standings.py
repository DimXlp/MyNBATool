#!/usr/bin/env python3
"""Interactive editor for standings.json - fix OCR errors and adjust rankings."""

import json
import os
from pathlib import Path

STANDINGS_FILE = Path("output/standings.json")

def load_standings():
    """Load standings from JSON file."""
    if not STANDINGS_FILE.exists():
        print(f"Error: {STANDINGS_FILE} not found. Run extract_roster_names.py first.")
        return None
    return json.loads(STANDINGS_FILE.read_text(encoding="utf-8"))

def save_standings(standings):
    """Save standings to JSON file."""
    STANDINGS_FILE.write_text(json.dumps(standings, indent=2), encoding="utf-8")
    print(f"\n✓ Saved to {STANDINGS_FILE}")

def display_standings(standings):
    """Display current standings grouped by conference."""
    eastern = sorted([t for t in standings if t["conference"] == "Eastern"], 
                     key=lambda x: x["rank"])
    western = sorted([t for t in standings if t["conference"] == "Western"], 
                     key=lambda x: x["rank"])
    
    print("\n" + "="*70)
    print("EASTERN CONFERENCE")
    print("="*70)
    for team in eastern:
        rank = team["rank"]
        name = team["team"]
        record = team["record"] or "??-??"
        print(f"{rank:2}. {name:30} {record}")
    
    print("\n" + "="*70)
    print("WESTERN CONFERENCE")
    print("="*70)
    for team in western:
        rank = team["rank"]
        name = team["team"]
        record = team["record"] or "??-??"
        print(f"{rank:2}. {name:30} {record}")
    
    print(f"\nTotal teams: {len(standings)} (Eastern: {len(eastern)}, Western: {len(western)})")

def find_team(standings, query):
    """Find a team by partial name match."""
    query_lower = query.lower()
    matches = [t for t in standings if query_lower in t["team"].lower()]
    return matches

def edit_team_record(standings):
    """Edit a team's W-L record."""
    team_name = input("\nEnter team name (or part of it): ").strip()
    if not team_name:
        return
    
    matches = find_team(standings, team_name)
    
    if not matches:
        print(f"No team found matching '{team_name}'")
        return
    
    if len(matches) > 1:
        print(f"\nFound {len(matches)} teams:")
        for i, team in enumerate(matches, 1):
            print(f"{i}. {team['team']} ({team['conference']}) - {team['record']}")
        choice = input("Select team number: ").strip()
        try:
            team = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    else:
        team = matches[0]
    
    print(f"\nEditing: {team['team']}")
    print(f"Current record: {team['record']}")
    new_record = input("Enter new W-L record (e.g., 17-12): ").strip()
    
    if not new_record:
        return
    
    # Validate format
    if "-" not in new_record:
        print("Invalid format. Use: W-L (e.g., 17-12)")
        return
    
    team["record"] = new_record
    print(f"✓ Updated {team['team']} record to {new_record}")

def edit_team_rank(standings):
    """Edit a team's rank."""
    team_name = input("\nEnter team name (or part of it): ").strip()
    if not team_name:
        return
    
    matches = find_team(standings, team_name)
    
    if not matches:
        print(f"No team found matching '{team_name}'")
        return
    
    if len(matches) > 1:
        print(f"\nFound {len(matches)} teams:")
        for i, team in enumerate(matches, 1):
            print(f"{i}. {team['team']} ({team['conference']}) - Rank {team['rank']}")
        choice = input("Select team number: ").strip()
        try:
            team = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    else:
        team = matches[0]
    
    print(f"\nEditing: {team['team']}")
    print(f"Current rank: {team['rank']}")
    new_rank = input("Enter new rank (1-15): ").strip()
    
    try:
        new_rank = int(new_rank)
        if not 1 <= new_rank <= 15:
            print("Rank must be between 1 and 15")
            return
    except ValueError:
        print("Invalid rank")
        return
    
    team["rank"] = new_rank
    print(f"✓ Updated {team['team']} rank to {new_rank}")

def add_missing_team(standings):
    """Add a missing team."""
    print("\nAdd missing team:")
    team_name = input("Team name: ").strip()
    if not team_name:
        return
    
    conference = input("Conference (Eastern/Western): ").strip()
    if conference not in ["Eastern", "Western"]:
        print("Invalid conference")
        return
    
    rank = input("Rank (1-15): ").strip()
    try:
        rank = int(rank)
        if not 1 <= rank <= 15:
            print("Rank must be between 1 and 15")
            return
    except ValueError:
        print("Invalid rank")
        return
    
    record = input("W-L record (e.g., 10-22): ").strip()
    if "-" not in record:
        print("Invalid format")
        return
    
    new_team = {
        "conference": conference,
        "rank": rank,
        "power_rank": None,
        "team": team_name,
        "record": record,
        "source": "manual_edit"
    }
    
    standings.append(new_team)
    print(f"✓ Added {team_name} to {conference} Conference")

def recalculate_ranks(standings):
    """Recalculate ranks based on W-L records within each conference."""
    def sort_by_record(team):
        record = team.get("record", "0-0")
        try:
            wins, losses = map(int, record.split("-"))
            return (-wins, losses)
        except:
            return (0, 999)
    
    eastern = sorted([t for t in standings if t["conference"] == "Eastern"], 
                     key=sort_by_record)
    western = sorted([t for t in standings if t["conference"] == "Western"], 
                     key=sort_by_record)
    
    for i, team in enumerate(eastern, 1):
        team["rank"] = i
    
    for i, team in enumerate(western, 1):
        team["rank"] = i
    
    print("✓ Recalculated ranks based on W-L records")

def main():
    standings = load_standings()
    if standings is None:
        return
    
    modified = False
    
    while True:
        display_standings(standings)
        
        print("\n" + "="*70)
        print("OPTIONS:")
        print("  1. Edit team W-L record")
        print("  2. Edit team rank")
        print("  3. Add missing team")
        print("  4. Recalculate ranks from W-L records")
        print("  5. Save and exit")
        print("  6. Exit without saving")
        print("="*70)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            edit_team_record(standings)
            modified = True
        elif choice == "2":
            edit_team_rank(standings)
            modified = True
        elif choice == "3":
            add_missing_team(standings)
            modified = True
        elif choice == "4":
            recalculate_ranks(standings)
            modified = True
        elif choice == "5":
            if modified:
                save_standings(standings)
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
