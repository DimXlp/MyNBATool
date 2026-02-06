#!/usr/bin/env python3
"""
NBA 2K26 League Manager - Desktop Application
A modern desktop UI for managing your MyLeague data
"""

import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QComboBox, QLineEdit, QStatusBar, QMessageBox, QHeaderView,
    QMenu, QMenuBar, QFileDialog, QGroupBox, QSplitter, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor

import db_config


class LeagueManagerApp(QMainWindow):
    """Main application window for NBA 2K26 League Manager"""
    
    def __init__(self):
        super().__init__()
        self.conn = None
        self.cur = None
        self.current_team = None
        self.teams = []
        
        self.init_ui()
        self.connect_database()
        self.load_teams()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("NBA 2K26 League Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for sidebar and content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left sidebar
        sidebar = self.create_sidebar()
        splitter.addWidget(sidebar)
        
        # Right content area
        content = self.create_content_area()
        splitter.addWidget(content)
        
        # Set splitter sizes (sidebar smaller than content)
        splitter.setSizes([250, 1150])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Apply modern styling
        self.apply_style()
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        import_action = QAction("&Import Data...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("&Export for ChatGPT...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data)
        view_menu.addAction(refresh_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        extract_action = QAction("Run &Extractors...", self)
        extract_action.triggered.connect(self.run_extractors)
        tools_menu.addAction(extract_action)
        
        edit_action = QAction("Edit &Data...", self)
        edit_action.triggered.connect(self.edit_data)
        tools_menu.addAction(edit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_sidebar(self):
        """Create left sidebar with team selector and quick stats"""
        sidebar = QWidget()
        sidebar.setMaximumWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Title
        title = QLabel("🏀 NBA Teams")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        sidebar_layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search teams...")
        self.search_box.textChanged.connect(self.filter_teams)
        sidebar_layout.addWidget(self.search_box)
        
        # Team selector
        self.team_combo = QComboBox()
        self.team_combo.currentTextChanged.connect(self.on_team_selected)
        sidebar_layout.addWidget(self.team_combo)
        
        # Quick stats group
        stats_group = QGroupBox("Quick Stats")
        stats_layout = QVBoxLayout()
        
        self.roster_count_label = QLabel("Roster: --")
        self.salary_total_label = QLabel("Total Salary: --")
        self.draft_picks_label = QLabel("Draft Picks: --")
        
        stats_layout.addWidget(self.roster_count_label)
        stats_layout.addWidget(self.salary_total_label)
        stats_layout.addWidget(self.draft_picks_label)
        
        stats_group.setLayout(stats_layout)
        sidebar_layout.addWidget(stats_group)
        
        # Action buttons
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        sidebar_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("📤 Export Team")
        self.export_btn.clicked.connect(self.export_team)
        sidebar_layout.addWidget(self.export_btn)
        
        sidebar_layout.addStretch()
        
        return sidebar
        
    def create_content_area(self):
        """Create main content area with tabs"""
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Team header
        self.team_header = QLabel("Select a team")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        self.team_header.setFont(header_font)
        content_layout.addWidget(self.team_header)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.roster_tab = self.create_roster_tab()
        self.contracts_tab = self.create_contracts_tab()
        self.draft_picks_tab = self.create_draft_picks_tab()
        self.standings_tab = self.create_standings_tab()
        self.salary_cap_tab = self.create_salary_cap_tab()
        
        self.tabs.addTab(self.roster_tab, "📋 Roster")
        self.tabs.addTab(self.contracts_tab, "💰 Contracts")
        self.tabs.addTab(self.draft_picks_tab, "🎯 Draft Picks")
        self.tabs.addTab(self.standings_tab, "🏆 Standings")
        self.tabs.addTab(self.salary_cap_tab, "💵 Salary Cap")
        
        content_layout.addWidget(self.tabs)
        
        return content
        
    def create_roster_tab(self):
        """Create roster view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.roster_table = QTableWidget()
        self.roster_table.setColumnCount(7)
        self.roster_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Change", "Team", "Source"
        ])
        
        # Make table sortable and resize columns
        self.roster_table.setSortingEnabled(True)
        header = self.roster_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.roster_table)
        
        return tab
        
    def create_contracts_tab(self):
        """Create contracts view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.contracts_table = QTableWidget()
        self.contracts_table.setColumnCount(7)
        self.contracts_table.setHorizontalHeaderLabels([
            "Player", "Salary", "Option", "Years", "Extension", "NTC", "Team"
        ])
        
        self.contracts_table.setSortingEnabled(True)
        header = self.contracts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.contracts_table)
        
        return tab
        
    def create_draft_picks_tab(self):
        """Create draft picks view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.draft_picks_table = QTableWidget()
        self.draft_picks_table.setColumnCount(6)
        self.draft_picks_table.setHorizontalHeaderLabels([
            "Year", "Round", "Pick", "Protection", "Origin", "Team"
        ])
        
        self.draft_picks_table.setSortingEnabled(True)
        header = self.draft_picks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for i in [1, 2, 4, 5]:
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.draft_picks_table)
        
        return tab
        
    def create_standings_tab(self):
        """Create standings view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Conference selector
        conf_layout = QHBoxLayout()
        conf_label = QLabel("Conference:")
        self.conf_combo = QComboBox()
        self.conf_combo.addItems(["All", "Eastern", "Western"])
        self.conf_combo.currentTextChanged.connect(self.load_standings)
        conf_layout.addWidget(conf_label)
        conf_layout.addWidget(self.conf_combo)
        conf_layout.addStretch()
        layout.addLayout(conf_layout)
        
        # Table
        self.standings_table = QTableWidget()
        self.standings_table.setColumnCount(6)
        self.standings_table.setHorizontalHeaderLabels([
            "Rank", "Team", "Conference", "W-L", "Win %", "Power Rank"
        ])
        
        self.standings_table.setSortingEnabled(True)
        header = self.standings_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in [0, 2, 3, 4, 5]:
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.standings_table)
        
        return tab
        
    def create_salary_cap_tab(self):
        """Create salary cap overview tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.salary_cap_table = QTableWidget()
        self.salary_cap_table.setColumnCount(6)
        self.salary_cap_table.setHorizontalHeaderLabels([
            "Team", "Total Salary", "Avg Salary", "Max Salary", "Players", "Cap Space"
        ])
        
        self.salary_cap_table.setSortingEnabled(True)
        header = self.salary_cap_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.salary_cap_table)
        
        return tab
        
    def connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = db_config.get_connection()
            self.cur = self.conn.cursor()
            self.statusBar.showMessage("Connected to database")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Failed to connect to database:\n{str(e)}")
            self.statusBar.showMessage("Database connection failed")
            
    def load_teams(self):
        """Load team list from database"""
        if not self.cur:
            return
            
        try:
            self.cur.execute("SELECT team_name FROM teams ORDER BY team_name")
            self.teams = [row[0] for row in self.cur.fetchall()]
            
            self.team_combo.clear()
            self.team_combo.addItems(["-- Select Team --"] + self.teams)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load teams:\n{str(e)}")
            
    def filter_teams(self, text):
        """Filter team list based on search text"""
        self.team_combo.clear()
        
        if text:
            filtered = [t for t in self.teams if text.lower() in t.lower()]
            self.team_combo.addItems(filtered)
        else:
            self.team_combo.addItems(["-- Select Team --"] + self.teams)
            
    def on_team_selected(self, team_name):
        """Handle team selection"""
        if team_name == "-- Select Team --" or not team_name:
            return
            
        self.current_team = team_name
        self.team_header.setText(f"{team_name}")
        
        # Load all data for selected team
        self.load_roster()
        self.load_contracts()
        self.load_draft_picks()
        self.load_quick_stats()
        
    def load_roster(self):
        """Load roster for current team"""
        if not self.cur or not self.current_team:
            return
            
        try:
            self.cur.execute("""
                SELECT name, position, age, overall_rating, delta_string, team, source_filename
                FROM roster_players
                WHERE team = %s
                ORDER BY overall_rating DESC
            """, (self.current_team,))
            
            rows = self.cur.fetchall()
            self.roster_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    if j == 3:  # OVR column
                        item.setData(Qt.ItemDataRole.UserRole, value)
                    self.roster_table.setItem(i, j, item)
                    
            self.statusBar.showMessage(f"Loaded {len(rows)} players")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load roster:\n{str(e)}")
            
    def load_contracts(self):
        """Load contracts for current team"""
        if not self.cur or not self.current_team:
            return
            
        try:
            self.cur.execute("""
                SELECT player_name, salary, contract_option, signing_status, 
                       extension_status, no_trade_clause, team
                FROM contracts
                WHERE team = %s
                ORDER BY salary_numeric DESC NULLS LAST
            """, (self.current_team,))
            
            rows = self.cur.fetchall()
            self.contracts_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if j == 5:  # NTC column (boolean)
                        item = QTableWidgetItem("Yes" if value else "No")
                    else:
                        item = QTableWidgetItem(str(value) if value is not None else "")
                    self.contracts_table.setItem(i, j, item)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load contracts:\n{str(e)}")
            
    def load_draft_picks(self):
        """Load draft picks for current team"""
        if not self.cur or not self.current_team:
            return
            
        try:
            self.cur.execute("""
                SELECT draft_year, round, pick_number, protection, origin_team, team
                FROM draft_picks
                WHERE team = %s
                ORDER BY draft_year, round, pick_number
            """, (self.current_team,))
            
            rows = self.cur.fetchall()
            self.draft_picks_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    # Format round as "1st" or "2nd"
                    if j == 1 and value:
                        display_value = "1st" if value == 1 else "2nd" if value == 2 else str(value)
                    else:
                        display_value = str(value) if value is not None else ""
                    item = QTableWidgetItem(display_value)
                    self.draft_picks_table.setItem(i, j, item)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load draft picks:\n{str(e)}")
            
    def load_standings(self):
        """Load league standings"""
        if not self.cur:
            return
            
        try:
            conference = self.conf_combo.currentText()
            
            if conference == "All":
                self.cur.execute("""
                    SELECT conference_rank, team, conference, wins, losses, 
                           ROUND(wins::numeric / (wins + losses), 3) as win_pct, power_rank
                    FROM standings
                    ORDER BY conference, conference_rank
                """)
            else:
                self.cur.execute("""
                    SELECT conference_rank, team, conference, wins, losses,
                           ROUND(wins::numeric / (wins + losses), 3) as win_pct, power_rank
                    FROM standings
                    WHERE conference = %s
                    ORDER BY conference_rank
                """, (conference,))
            
            rows = self.cur.fetchall()
            self.standings_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if j == 3:  # W-L column
                        wins, losses = value, row[4]
                        item = QTableWidgetItem(f"{wins}-{losses}")
                    elif j == 4:  # Skip losses (combined with wins)
                        continue
                    else:
                        item = QTableWidgetItem(str(value) if value is not None else "")
                    
                    # Adjust column index after combining W-L
                    col = j if j < 4 else j - 1
                    self.standings_table.setItem(i, col, item)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load standings:\n{str(e)}")
            
    def load_salary_cap(self):
        """Load salary cap data for all teams"""
        if not self.cur:
            return
            
        try:
            self.cur.execute("""
                SELECT team_name, total_salary, avg_salary, max_salary, player_count,
                       150.0 - COALESCE(total_salary, 0.0) as cap_space
                FROM team_salary_summary
                ORDER BY total_salary DESC NULLS LAST
            """)
            
            rows = self.cur.fetchall()
            self.salary_cap_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if j in [1, 2, 3, 5]:  # Salary columns
                        display_value = f"${value:.2f}M" if value is not None else "$0.00M"
                    else:
                        display_value = str(value) if value is not None else ""
                    item = QTableWidgetItem(display_value)
                    self.salary_cap_table.setItem(i, j, item)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load salary cap data:\n{str(e)}")
            
    def load_quick_stats(self):
        """Load quick stats for current team"""
        if not self.cur or not self.current_team:
            return
            
        try:
            # Roster count
            self.cur.execute("SELECT COUNT(*) FROM roster_players WHERE team = %s", 
                           (self.current_team,))
            roster_count = self.cur.fetchone()[0]
            self.roster_count_label.setText(f"Roster: {roster_count} players")
            
            # Total salary
            self.cur.execute("""
                SELECT COALESCE(SUM(salary_numeric), 0.0)
                FROM contracts
                WHERE team = %s
            """, (self.current_team,))
            total_salary = self.cur.fetchone()[0]
            self.salary_total_label.setText(f"Total Salary: ${total_salary:.2f}M")
            
            # Draft picks count
            self.cur.execute("SELECT COUNT(*) FROM draft_picks WHERE team = %s",
                           (self.current_team,))
            draft_count = self.cur.fetchone()[0]
            self.draft_picks_label.setText(f"Draft Picks: {draft_count}")
            
        except Exception as e:
            print(f"Error loading quick stats: {e}")
            
    def refresh_data(self):
        """Refresh all data"""
        self.load_teams()
        if self.current_team:
            self.on_team_selected(self.current_team)
        self.load_standings()
        self.load_salary_cap()
        self.statusBar.showMessage("Data refreshed")
        
    def import_data(self):
        """Run import from JSON files"""
        reply = QMessageBox.question(self, "Import Data",
                                     "Import all JSON files from output/ directory to database?\n\nThis will update the database with new data.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.statusBar.showMessage("Importing data...")
                
                # Get Python executable path from virtual environment
                python_exe = Path(sys.executable)
                script_path = Path(__file__).parent / "import_to_database_v2.py"
                
                # Run import script
                result = subprocess.run(
                    [str(python_exe), str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    QMessageBox.information(self, "Import Successful",
                                          f"Data imported successfully!\n\n{result.stdout}")
                    self.statusBar.showMessage("Import completed successfully")
                    # Auto-refresh after import
                    QTimer.singleShot(500, self.refresh_data)
                else:
                    QMessageBox.warning(self, "Import Failed",
                                      f"Import failed with error:\n\n{result.stderr}")
                    self.statusBar.showMessage("Import failed")
                    
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Timeout", "Import took too long and was cancelled.")
                self.statusBar.showMessage("Import timeout")
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", 
                                   f"Could not find import_to_database_v2.py\n\nExpected location: {script_path}")
                self.statusBar.showMessage("Import script not found")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to run import:\n\n{str(e)}")
                self.statusBar.showMessage("Import error")
            
    def export_data(self):
        """Export league state for ChatGPT"""
        reply = QMessageBox.question(self, "Export Data",
                                     "Export league data for ChatGPT?\n\nThis will generate 4 text files in league_exports/ directory.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.statusBar.showMessage("Exporting league data...")
                
                # Get Python executable path from virtual environment
                python_exe = Path(sys.executable)
                script_path = Path(__file__).parent / "export_league_state.py"
                
                # Run export script
                result = subprocess.run(
                    [str(python_exe), str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    export_dir = Path(__file__).parent / "league_exports"
                    files_msg = "\n".join([
                        "- 1_standings.txt",
                        "- 2_salary_cap.txt",
                        "- 3_rosters.txt",
                        "- 4_draft_picks.txt"
                    ])
                    
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Export Successful")
                    msg.setText("League data exported successfully!")
                    msg.setDetailedText(result.stdout)
                    msg.setInformativeText(f"Files created in league_exports/:\n\n{files_msg}")
                    
                    # Add button to open folder
                    open_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
                    msg.addButton(QMessageBox.StandardButton.Ok)
                    
                    msg.exec()
                    
                    if msg.clickedButton() == open_btn:
                        # Open export directory in file explorer
                        if sys.platform == 'win32':
                            subprocess.run(['explorer', str(export_dir)])
                        elif sys.platform == 'darwin':
                            subprocess.run(['open', str(export_dir)])
                        else:
                            subprocess.run(['xdg-open', str(export_dir)])
                    
                    self.statusBar.showMessage("Export completed successfully")
                else:
                    QMessageBox.warning(self, "Export Failed",
                                      f"Export failed with error:\n\n{result.stderr}")
                    self.statusBar.showMessage("Export failed")
                    
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Timeout", "Export took too long and was cancelled.")
                self.statusBar.showMessage("Export timeout")
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", 
                                   f"Could not find export_league_state.py\n\nExpected location: {script_path}")
                self.statusBar.showMessage("Export script not found")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to run export:\n\n{str(e)}")
                self.statusBar.showMessage("Export error")
            
    def export_team(self):
        """Export current team data"""
        if not self.current_team:
            QMessageBox.warning(self, "No Team", "Please select a team first.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Team Data", f"{self.current_team}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            # TODO: Generate team export file
            QMessageBox.information(self, "Export", f"Team data would be exported to:\n{filename}")
            
    def run_extractors(self):
        """Show extractor dialog"""
        QMessageBox.information(self, "Extractors",
                               "Run extractors from command line:\n\n"
                               "1. python classify_screens.py\n"
                               "2. python extract_roster_names.py\n"
                               "3. python extract_contracts.py\n"
                               "4. python extract_draft_picks.py\n"
                               "5. python extract_standings.py")
        
    def edit_data(self):
        """Show edit data dialog"""
        QMessageBox.information(self, "Edit Data",
                               "Run editors from command line:\n\n"
                               "- python edit_roster.py\n"
                               "- python edit_contracts.py\n"
                               "- python edit_draft_picks.py\n"
                               "- python edit_standings.py")
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About NBA 2K26 League Manager",
                         "NBA 2K26 League Manager\n\n"
                         "A desktop application for managing your MyLeague data.\n\n"
                         "Features:\n"
                         "- View rosters, contracts, and draft picks\n"
                         "- Track salary cap and standings\n"
                         "- Export data for AI analysis\n\n"
                         "Built with PyQt6 and PostgreSQL")
        
    def apply_style(self):
        """Apply modern styling to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QComboBox, QLineEdit {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #2196F3;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QStatusBar {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        
    def closeEvent(self, event):
        """Handle application close"""
        if self.conn:
            self.conn.close()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern cross-platform style
    
    window = LeagueManagerApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
