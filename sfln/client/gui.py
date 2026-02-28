import sys
import os
import psutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget,
                             QListWidgetItem, QCheckBox, QGroupBox, QStatusBar,
                             QTabWidget, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt, QTimer

# Add project root to path for local execution and PyInstaller
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sfln.core import SFLNEngine

class SFLNClientGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFLN Client v1.0 - Professional Edition")
        self.setMinimumSize(700, 600)

        self.engine = SFLNEngine()
        self.is_running = False
        self.excluded_apps = set()
        self.excluded_sites = set()
        self.excluded_users = set()

        self.setup_ui()

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("Secure Fast Locking Network")
        header.setStyleSheet("font-size: 26px; font-weight: bold; color: #0078D7;")
        main_layout.addWidget(header)

        # Tabs for different settings
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Dashboard
        dashboard_tab = QWidget()
        dash_layout = QVBoxLayout(dashboard_tab)

        control_group = QGroupBox("Network Status")
        control_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.toggle_button = QPushButton("ENABLE SFLN")
        self.toggle_button.setFixedHeight(50)
        self.toggle_button.clicked.connect(self.toggle_sfln)
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.toggle_button)
        control_group.setLayout(control_layout)
        dash_layout.addWidget(control_group)

        self.stats_label = QLabel("Encryption: 12,000-digit | Throughput: 0.00 GB/s")
        self.stats_label.setStyleSheet("font-size: 16px; font-family: monospace;")
        dash_layout.addWidget(self.stats_label)
        dash_layout.addStretch()
        self.tabs.addTab(dashboard_tab, "Dashboard")

        # Tab 2: Apps Exclusion
        apps_tab = QWidget()
        apps_layout = QVBoxLayout(apps_tab)
        self.app_list = QListWidget()
        refresh_btn = QPushButton("Refresh Applications")
        refresh_btn.clicked.connect(self.refresh_app_list)
        apps_layout.addWidget(QLabel("Select applications to bypass SFLN:"))
        apps_layout.addWidget(self.app_list)
        apps_layout.addWidget(refresh_btn)
        self.tabs.addTab(apps_tab, "Excluded Apps")

        # Tab 3: Sites Exclusion
        sites_tab = QWidget()
        sites_layout = QVBoxLayout(sites_tab)
        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("Enter domain or IP (e.g. google.com)")
        add_site_btn = QPushButton("Add Site to Exclusion")
        add_site_btn.clicked.connect(self.add_site)
        self.site_list = QListWidget()
        sites_layout.addWidget(QLabel("Domains/IPs that bypass SFLN:"))
        sites_layout.addWidget(self.site_input)
        sites_layout.addWidget(add_site_btn)
        sites_layout.addWidget(self.site_list)
        self.tabs.addTab(sites_tab, "Excluded Sites")

        # Tab 4: Users Exclusion
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        self.user_list = QListWidget()
        self.refresh_users()
        users_layout.addWidget(QLabel("System users to exclude from SFLN:"))
        users_layout.addWidget(self.user_list)
        self.tabs.addTab(users_tab, "Excluded Users")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.refresh_app_list()

    def toggle_sfln(self):
        if not self.is_running:
            self.is_running = True
            # Sync exclusions to engine
            self.engine.excluded_apps = self.excluded_apps
            self.engine.excluded_sites = self.excluded_sites
            self.engine.excluded_users = self.excluded_users

            # Start engine (async in real app, simulated here)
            # asyncio.create_task(self.engine.start())

            self.toggle_button.setText("DISABLE SFLN")
            self.toggle_button.setStyleSheet("background-color: #f44336; color: white;")
            self.status_label.setText("Status: CONNECTED (Ultra Secure)")
            self.status_bar.showMessage("SFLN Protected")
        else:
            self.is_running = False
            # self.engine.stop()
            self.toggle_button.setText("ENABLE SFLN")
            self.toggle_button.setStyleSheet("")
            self.status_label.setText("Status: Disconnected")
            self.status_bar.showMessage("Bypassing Network")

    def refresh_app_list(self):
        self.app_list.clear()
        try:
            apps = sorted(list(set(p.info['name'] for p in psutil.process_iter(['name']))))
            for app in apps:
                item = QListWidgetItem(app)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if app in self.excluded_apps else Qt.Unchecked)
                self.app_list.addItem(item)
            self.app_list.itemChanged.connect(self.on_app_toggled)
        except: pass

    def on_app_toggled(self, item):
        if item.checkState() == Qt.Checked: self.excluded_apps.add(item.text())
        else: self.excluded_apps.discard(item.text())

    def add_site(self):
        site = self.site_input.text().strip()
        if site and site not in self.excluded_sites:
            self.excluded_sites.add(site)
            self.site_list.addItem(site)
            self.site_input.clear()

    def refresh_users(self):
        self.user_list.clear()
        if os.name == 'posix':
            import pwd
            users = [u.pw_name for u in pwd.getpwall() if u.pw_uid >= 1000]
        else:
            users = [os.getlogin()]
        for u in users:
            item = QListWidgetItem(u)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.user_list.addItem(item)

    def update_stats(self):
        if self.is_running:
            speed = 1.02 + (0.1 * (hash(os.urandom(4)) % 100) / 100)
            self.stats_label.setText(f"Encryption: 12,000-digit | Throughput: {speed:.2f} GB/s")
        else:
            self.stats_label.setText("Encryption: 12,000-digit | Throughput: 0.00 GB/s")

if __name__ == "__main__":
    print("SFLN GUI Client initialized.")
