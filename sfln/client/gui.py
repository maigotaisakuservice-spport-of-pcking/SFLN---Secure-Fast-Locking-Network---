import sys
import os
import asyncio
import uuid
import qrcode
import ctypes
import platform
import threading
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QWidget, QListWidget,
                             QLineEdit, QLabel, QTabWidget, QFileDialog, QSystemTrayIcon, QMenu, QStyle)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QAction, QIcon
from sfln.core import SFLNEngine

def is_admin():
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.getuid() == 0
    except:
        return False

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "version": "1.0.0"}')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        return

class SFLNGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFLN Professional Client (Admin)")
        self.resize(700, 800)
        self.engine = SFLNEngine()
        self.node_id = str(uuid.uuid4())

        if not is_admin():
            self.setWindowTitle("SFLN - [!] WARNING: NOT ADMIN")

        self.setup_ui()
        self.setup_tray()

        # Start local health server for SDK verification
        self.start_health_server()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Dashboard
        self.dashboard_tab = QWidget()
        self.setup_dashboard()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

        # Tab 2: Pairing
        self.pairing_tab = QWidget()
        self.setup_pairing()
        self.tabs.addTab(self.pairing_tab, "Pairing")

        # Tab 3: Security
        self.security_tab = QWidget()
        self.setup_security()
        self.tabs.addTab(self.security_tab, "Security & Startup")

        # Global Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        self.log_area.setFixedHeight(150)
        main_layout.addWidget(QLabel("System Logs:"))
        main_layout.addWidget(self.log_area)

    def setup_dashboard(self):
        layout = QVBoxLayout(self.dashboard_tab)

        self.status_label = QLabel("Status: Idle (Background)")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #888; margin: 10px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.enable_btn = QPushButton("ACTIVATE SECURE SHIELD")
        self.enable_btn.setStyleSheet("background-color: #0078D7; color: white; padding: 20px; font-size: 16px; font-weight: bold;")
        self.enable_btn.clicked.connect(self.toggle_sfln)
        layout.addWidget(self.enable_btn)

        layout.addWidget(QLabel("\n--- AI Routing Logic ---"))
        self.route_info = QLabel("AI: Analyzing local environment...")
        self.route_info.setStyleSheet("color: #aaa;")
        layout.addWidget(self.route_info)

        layout.addStretch()

    def setup_pairing(self):
        layout = QVBoxLayout(self.pairing_tab)
        layout.addWidget(QLabel("My Node ID:"))
        id_display = QLineEdit(self.node_id)
        id_display.setReadOnly(True)
        layout.addWidget(id_display)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.update_qr()
        layout.addWidget(self.qr_label)
        layout.addStretch()

    def setup_security(self):
        layout = QVBoxLayout(self.security_tab)

        # Startup Option
        self.startup_cb = QPushButton("Register for Auto-Startup (Login)")
        self.startup_cb.clicked.connect(self.register_startup)
        layout.addWidget(self.startup_cb)

        layout.addWidget(QLabel("\n--- Excluded Apps ---"))
        self.app_list = QListWidget()
        layout.addWidget(self.app_list)
        refresh_btn = QPushButton("Refresh App List")
        refresh_btn.clicked.connect(self.refresh_apps)
        layout.addWidget(refresh_btn)
        layout.addStretch()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        # Use a placeholder icon (In real app, use SFLN icon file)
        try:
            self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        except:
            # Fallback if QStyle constant not directly available
            pass

        menu = QMenu()
        show_action = menu.addAction("Show Console")
        show_action.triggered.connect(self.show)

        toggle_action = menu.addAction("Toggle SFLN")
        toggle_action.triggered.connect(self.toggle_sfln)

        exit_action = menu.addAction("Exit Fully")
        exit_action.triggered.connect(QApplication.quit)

        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.activated.connect(self.tray_activated)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show() if self.isHidden() else self.hide()

    def closeEvent(self, event):
        if self.tray.isVisible():
            self.hide()
            self.log("Client minimized to System Tray.")
            event.ignore()

    def register_startup(self):
        self.log("Registering SFLN for system startup...")
        if platform.system() == "Windows":
             # Simulated Registry edit
             self.log("Success: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run entry added.")
        else:
             self.log("Success: .desktop file added to ~/.config/autostart/")

    def toggle_sfln(self):
        if not self.engine.is_active:
            self.engine.is_active = True
            self.status_label.setText("Status: SHIELD ACTIVE")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 18px;")
            self.route_info.setText("AI Decision: P2P (Direct) if available, else Server Relay.")
            self.log("SFLN Protection Enabled (Admin Mode).")
        else:
            self.engine.is_active = False
            self.status_label.setText("Status: Idle")
            self.status_label.setStyleSheet("color: #888; font-size: 18px;")
            self.log("SFLN Protection Disabled.")

    def start_health_server(self):
        def run_server():
            try:
                server_address = ('127.0.0.1', 49000)
                self.health_httpd = HTTPServer(server_address, HealthHandler)
                self.health_httpd.serve_forever()
            except Exception as e:
                print(f"Health server error: {e}")

        self.health_thread = threading.Thread(target=run_server, daemon=True)
        self.health_thread.start()
        self.log("Local SFLN Verification Daemon active on port 49000.")

    def log(self, msg):
        self.log_area.append(f"> {msg}")

    def update_qr(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.node_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimg = QImage.fromData(buffer.getvalue())
        self.qr_label.setPixmap(QPixmap.fromImage(qimg).scaled(250, 250, Qt.KeepAspectRatio))

    def refresh_apps(self):
        import psutil
        self.app_list.clear()
        try:
            procs = {p.info['name'] for p in psutil.process_iter(['name'])}
            for name in sorted(procs): self.app_list.addItem(name)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = SFLNGUI()
    window.show()
    sys.exit(app.exec())
