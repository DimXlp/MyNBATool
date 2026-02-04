# edit_contracts.py
"""Interactive editor for contract data extracted from NBA 2K26 screenshots."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

OUTPUT_DIR = Path("output")
CONTRACTS_FILE = OUTPUT_DIR / "contracts.json"

def load_contracts() -> List[Dict[str, Any]]:
    """Load contracts from JSON file."""
    if not CONTRACTS_FILE.exists():
        print(f"ERROR: {CONTRACTS_FILE} not found. Run extract_contracts.py first.")
        exit(1)
    
    return json.loads(CONTRACTS_FILE.read_text(encoding="utf-8"))

def get_teams(contracts: List[Dict[str, Any]]) -> List[str]:
    """Extract unique teams from contracts."""
    teams = set()
    for contract in contracts:
        team = contract.get("team", "Unknown")
        teams.add(team)
    return sorted(teams)

def filter_contracts_by_team(contracts: List[Dict[str, Any]], team_name: str) -> List[Dict[str, Any]]:
    """Filter contracts to only show players from a specific team."""
    return [c for c in contracts if c.get("team", "Unknown") == team_name]

def save_contracts(contracts: List[Dict[str, Any]]) -> None:
    """Save contracts to JSON file."""
    CONTRACTS_FILE.write_text(json.dumps(contracts, indent=2), encoding="utf-8")
    print(f"✓ Saved to {CONTRACTS_FILE}")

def display_contract(contract: Dict[str, Any]) -> None:
    """Display a single contract's details."""
    print(f"\n{'='*60}")
    print(f"Name: {contract.get('name', 'N/A')}")
    print(f"Team: {contract.get('team', 'N/A')}")
    print(f"Salary: {contract.get('salary', 'N/A')}")
    print(f"Option: {contract.get('option', 'N/A')}")
    print(f"Signing Status: {contract.get('sign', 'N/A')}")
    print(f"Extension: {contract.get('extension', 'N/A')}")
    print(f"No Trade Clause: {contract.get('ntc', 'N/A')}")
    print(f"Source: {contract.get('source', 'N/A')}")
    print(f"{'='*60}\n")

def search_contracts(contracts: List[Dict[str, Any]], query: str) -> List[int]:
    """Search for contracts by player name. Returns list of indices."""
    query_lower = query.lower()
    matches = []
    
    for i, contract in enumerate(contracts):
        name = contract.get("name", "").lower()
        if query_lower in name:
            matches.append(i)
    
    return matches

def edit_contract_field(contract: Dict[str, Any], field: str) -> None:
    """Edit a specific field of a contract."""
    current = contract.get(field, "N/A")
    print(f"Current {field}: {current}")
    
    if field == "salary":
        print("Enter salary (e.g., $40.54M) or leave empty to clear:")
        new_value = input("> ").strip()
        contract[field] = new_value if new_value else None
    
    elif field == "option":
        print("Options: Player, Team, 2 Yr Team, None")
        new_value = input("> ").strip()
        contract[field] = new_value if new_value else None
    
    elif field == "sign":
        print("Enter signing status (e.g., 1yr +1, 4 yrs) or leave empty to clear:")
        new_value = input("> ").strip()
        contract[field] = new_value if new_value else None
    
    elif field == "extension":
        print("Options: Will Resign, Not Eligible, None")
        new_value = input("> ").strip()
        contract[field] = new_value if new_value else None
    
    elif field == "ntc":
        print("No Trade Clause (Yes/No):")
        new_value = input("> ").strip()
        if new_value.upper() in ["YES", "Y"]:
            contract[field] = "Yes"
        elif new_value.upper() in ["NO", "N"]:
            contract[field] = "No"
        else:
            contract[field] = None
    
    elif field == "name":
        print("Enter player name (e.g., J. Brunson):")
        new_value = input("> ").strip()
        if new_value:
            contract[field] = new_value
    
    elif field == "team":
        print("Enter team name:")
        new_value = input("> ").strip()
        if new_value:
            contract[field] = new_value
    
    print(f"✓ Updated {field}")

def edit_contract_menu(contracts: List[Dict[str, Any]], idx: int) -> None:
    """Show edit menu for a specific contract."""
    contract = contracts[idx]
    
    while True:
        display_contract(contract)
        print("Edit options:")
        print("1. Edit name")
        print("2. Edit team")
        print("3. Edit salary")
        print("4. Edit option")
        print("5. Edit signing status")
        print("6. Edit extension")
        print("7. Edit no trade clause")
        print("8. Back to main menu")
        
        choice = input("\nChoose option (1-8): ").strip()
        
        if choice == "1":
            edit_contract_field(contract, "name")
        elif choice == "2":
            edit_contract_field(contract, "team")
        elif choice == "3":
            edit_contract_field(contract, "salary")
        elif choice == "4":
            edit_contract_field(contract, "option")
        elif choice == "5":
            edit_contract_field(contract, "sign")
        elif choice == "6":
            edit_contract_field(contract, "extension")
        elif choice == "7":
            edit_contract_field(contract, "ntc")
        elif choice == "8":
            break
        else:
            print("Invalid option. Try again.")

def add_contract_menu(contracts: List[Dict[str, Any]], team_name: Optional[str] = None) -> None:
    """Add a new contract."""
    print("\n=== Add New Contract ===")
    
    name = input("Player name (e.g., J. Brunson): ").strip()
    if not name:
        print("Name is required. Cancelled.")
        return
    
    if team_name:
        team = team_name
        print(f"Team: {team}")
    else:
        team = input("Team name: ").strip()
    
    salary = input("Salary (e.g., $40.54M): ").strip()
    option = input("Option (Player/Team/None): ").strip()
    sign = input("Signing status (e.g., 1yr +1): ").strip()
    extension = input("Extension (Will Resign/Not Eligible/None): ").strip()
    ntc = input("No Trade Clause (Yes/No): ").strip()
    
    new_contract = {
        "name": name,
        "team": team if team else "Unknown",
        "salary": salary if salary else None,
        "option": option if option else None,
        "sign": sign if sign else None,
        "extension": extension if extension else None,
        "ntc": "Yes" if ntc.upper() in ["YES", "Y"] else ("No" if ntc.upper() in ["NO", "N"] else None),
        "source": "manual_entry",
        "y0": 0,
        "y1": 0,
        "name_conf": 100.0,
    }
    
    contracts.append(new_contract)
    print(f"✓ Added contract for {name}")

def remove_contract_menu(contracts: List[Dict[str, Any]]) -> None:
    """Remove a contract."""
    name = input("Enter player name to remove: ").strip()
    matches = search_contracts(contracts, name)
    
    if not matches:
        print(f"No contracts found matching '{name}'")
        return
    
    if len(matches) == 1:
        idx = matches[0]
        contract = contracts[idx]
        print(f"Remove contract for {contract['name']} ({contract.get('team', 'Unknown')})?")
        confirm = input("Confirm (y/n): ").strip().lower()
        
        if confirm == "y":
            contracts.pop(idx)
            print(f"✓ Removed contract")
        else:
            print("Cancelled")
    else:
        print(f"Found {len(matches)} contracts:")
        for i, idx in enumerate(matches, 1):
            contract = contracts[idx]
            print(f"{i}. {contract['name']} - {contract.get('team', 'Unknown')} - {contract.get('salary', 'N/A')}")
        
        choice = input(f"Choose contract to remove (1-{len(matches)}): ").strip()
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(matches):
                idx = matches[choice_idx]
                contracts.pop(idx)
                print(f"✓ Removed contract")
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")

def team_menu(contracts: List[Dict[str, Any]], team_name: str) -> bool:
    """Menu for a specific team's contracts."""
    unsaved_changes = False
    
    while True:
        team_contracts = filter_contracts_by_team(contracts, team_name)
        
        print("\n" + "="*60)
        print(f"CONTRACT EDITOR - {team_name}")
        print("="*60)
        print(f"Team contracts: {len(team_contracts)}")
        if unsaved_changes:
            print("⚠ You have unsaved changes")
        
        print("\nOptions:")
        print("1. Search and edit contract")
        print("2. List team contracts")
        print("3. Add new contract")
        print("4. Remove contract")
        print("5. Back to team selection")
        
        choice = input("\nChoose option (1-5): ").strip()
        
        if choice == "1":
            name = input("Enter player name to search: ").strip()
            matches = search_contracts(team_contracts, name)
            
            if not matches:
                print(f"No contracts found matching '{name}' in {team_name}")
            elif len(matches) == 1:
                # Find the actual index in full contracts list
                team_contract = team_contracts[matches[0]]
                actual_idx = contracts.index(team_contract)
                edit_contract_menu(contracts, actual_idx)
                unsaved_changes = True
            else:
                print(f"Found {len(matches)} contracts:")
                for i, idx in enumerate(matches, 1):
                    contract = team_contracts[idx]
                    print(f"{i}. {contract['name']} - {contract.get('salary', 'N/A')}")
                
                choice_num = input(f"Choose contract to edit (1-{len(matches)}): ").strip()
                try:
                    choice_idx = int(choice_num) - 1
                    if 0 <= choice_idx < len(matches):
                        team_contract = team_contracts[matches[choice_idx]]
                        actual_idx = contracts.index(team_contract)
                        edit_contract_menu(contracts, actual_idx)
                        unsaved_changes = True
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Invalid input")
        
        elif choice == "2":
            print(f"\n{team_name} contracts ({len(team_contracts)}):")
            for i, contract in enumerate(team_contracts, 1):
                print(f"{i}. {contract['name']} - {contract.get('salary', 'N/A')}")
        
        elif choice == "3":
            add_contract_menu(contracts, team_name)
            unsaved_changes = True
        
        elif choice == "4":
            remove_contract_menu(contracts)
            unsaved_changes = True
        
        elif choice == "5":
            break
        
        else:
            print("Invalid option. Try again.")
    
    return unsaved_changes

def main_menu() -> None:
    """Main menu with team selection."""
    contracts = load_contracts()
    print(f"\nLoaded {len(contracts)} contracts from {CONTRACTS_FILE}")
    
    unsaved_changes = False
    
    while True:
        teams = get_teams(contracts)
        
        print("\n" + "="*60)
        print("CONTRACT EDITOR - TEAM SELECTION")
        print("="*60)
        print(f"Total contracts: {len(contracts)}")
        print(f"Teams: {len(teams)}")
        if unsaved_changes:
            print("⚠ You have unsaved changes")
        
        print("\nTeams:")
        for i, team in enumerate(teams, 1):
            team_count = len(filter_contracts_by_team(contracts, team))
            print(f"  {i}. {team} ({team_count} contracts)")
        
        print(f"\n  {len(teams)+1}. View all contracts")
        print(f"  {len(teams)+2}. Sort all contracts by name")
        print(f"  {len(teams)+3}. Save changes")
        print(f"  {len(teams)+4}. Discard changes and exit")
        print(f"  {len(teams)+5}. Save and exit")
        
        choice = input("\nChoose option: ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(teams):
                selected_team = teams[choice_num - 1]
                team_modified = team_menu(contracts, selected_team)
                unsaved_changes = unsaved_changes or team_modified
            
            elif choice_num == len(teams) + 1:
                print(f"\nAll contracts ({len(contracts)}):")
                for i, contract in enumerate(contracts, 1):
                    print(f"{i}. {contract['name']} - {contract.get('team', 'Unknown')} - {contract.get('salary', 'N/A')}")
                input("\nPress Enter to continue...")
            
            elif choice_num == len(teams) + 2:
                contracts.sort(key=lambda c: c["name"].lower())
                print("✓ Sorted contracts by name")
                unsaved_changes = True
            
            elif choice_num == len(teams) + 3:
                save_contracts(contracts)
                unsaved_changes = False
            
            elif choice_num == len(teams) + 4:
                if unsaved_changes:
                    confirm = input("Discard unsaved changes? (y/n): ").strip().lower()
                    if confirm == "y":
                        print("Changes discarded. Exiting.")
                        break
                else:
                    print("No changes to discard. Exiting.")
                    break
            
            elif choice_num == len(teams) + 5:
                if unsaved_changes:
                    save_contracts(contracts)
                print("Exiting.")
                break
            
            else:
                print("Invalid option. Try again.")
        
        except ValueError:
            print("Invalid input")

if __name__ == "__main__":
    main_menu()
