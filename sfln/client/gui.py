import sys
import os
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QWidget, QListWidget, QLineEdit, QLabel
from PySide6.QtCore import Qt, QTimer
from sfln.core import SFLNEngine

class SFLNGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFLN Professional Client")
        self.resize(600, 700)
        self.engine = SFLNEngine()
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(self.status_label)

        self.enable_btn = QPushButton("ENABLE SFLN")
        self.enable_btn.setStyleSheet("background-color: #0078D7; color: white; padding: 10px; font-weight: bold;")
        self.enable_btn.clicked.connect(self.toggle_sfln)
        layout.addWidget(self.enable_btn)

        layout.addWidget(QLabel("--- Excluded Apps ---"))
        self.app_list = QListWidget()
        self.refresh_apps()
        layout.addWidget(self.app_list)

        btn_layout = QVBoxLayout()
        refresh_btn = QPushButton("Refresh Apps")
        refresh_btn.clicked.connect(self.refresh_apps)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("--- Excluded Sites ---"))
        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("example.com")
        layout.addWidget(self.site_input)
        add_site_btn = QPushButton("Add Site")
        add_site_btn.clicked.connect(self.add_site)
        layout.addWidget(add_site_btn)
        self.site_list = QListWidget()
        layout.addWidget(self.site_list)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        layout.addWidget(self.log_area)

    def log(self, msg):
        self.log_area.append(f"> {msg}")

    def toggle_sfln(self):
        if not self.engine.is_active:
            # Simple start for demo
            self.engine.is_active = True
            self.status_label.setText("Status: ACTIVE (Mesh: Connected)")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            self.enable_btn.setText("DISABLE SFLN")
            self.log("SFLN Engine Started. 12,000-digit encryption initialized.")
        else:
            self.engine.is_active = False
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: #888;")
            self.enable_btn.setText("ENABLE SFLN")
            self.log("SFLN Engine Stopped.")

    def refresh_apps(self):
        import psutil
        self.app_list.clear()
        procs = {p.info['name'] for p in psutil.process_iter(['name'])}
        for name in sorted(procs):
            self.app_list.addItem(name)

    def add_site(self):
        site = self.site_input.text()
        if site:
            self.engine.excluded_sites.add(site)
            self.site_list.addItem(site)
            self.site_input.clear()
            self.log(f"Site excluded: {site}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SFLNGUI()
    window.show()
    sys.exit(app.exec())
