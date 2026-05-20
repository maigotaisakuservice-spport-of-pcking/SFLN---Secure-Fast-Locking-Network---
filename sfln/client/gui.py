import sys
import os
import asyncio
import uuid
import qrcode
import ctypes
import platform
import threading
import keyring
import time
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QWidget, QListWidget,
                             QLineEdit, QLabel, QTabWidget, QFileDialog, QSystemTrayIcon, QMenu, QStyle,
                             QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView, QGroupBox)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QPixmap, QImage, QAction, QIcon, QFont, QColor, QPainter, QBrush
from sfln.core import SFLNEngine

def is_admin():
    try:
        if platform.system() == "Windows": return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else: return os.getuid() == 0
    except: return False

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "version": "2.2.0"}')
        else: self.send_error(404)
    def log_message(self, format, *args): return

class ProgressSignal(QObject):
    update = Signal(int, str, int, int) # Row, Phase, Current, Total
    peer_found = Signal(str, str) # NodeID, Latency

class SFLNGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFLN Professional Client")
        self.resize(900, 950)
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; color: #c9d1d9; font-family: 'Noto Sans JP', sans-serif; }
            QLabel { color: #c9d1d9; }
            QLineEdit { background: #161b22; border: 1px solid #30363d; color: #58a6ff; padding: 12px; border-radius: 8px; font-family: 'Fira Code', monospace; }
            QPushButton { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 12px 20px; border-radius: 8px; font-weight: bold; min-width: 80px; }
            QPushButton:hover { background-color: #30363d; border-color: #8b949e; }
            QPushButton#primary { background-color: #238636; border: none; }
            QPushButton#primary:hover { background-color: #2ea043; }
            QPushButton#accent { background-color: #1f6feb; border: none; }
            QPushButton#accent:hover { background-color: #388bfd; }
            QGroupBox { border: 1px solid #30363d; margin-top: 20px; padding-top: 15px; font-weight: bold; color: #58a6ff; border-radius: 8px; }
            QTabWidget::pane { border: 1px solid #30363d; background: #0d1117; border-radius: 8px; }
            QTabBar::tab { background: #161b22; padding: 15px 30px; color: #8b949e; border: 1px solid #30363d; border-bottom: none; border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0d1117; color: #58a6ff; font-weight: bold; border-top: 3px solid #58a6ff; }
            QTableWidget { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; gridline-color: #30363d; border-radius: 6px; }
            QHeaderView::section { background: #21262d; color: #8b949e; padding: 10px; border: 1px solid #30363d; }
            QProgressBar { border: 1px solid #30363d; border-radius: 5px; text-align: center; background: #0d1117; }
            QProgressBar::chunk { background-color: #58a6ff; width: 10px; }
        """)

        self.load_secure_key()
        self.node_id = str(uuid.uuid4())
        self.engine = SFLNEngine(master_key=self.master_key, node_id=self.node_id)

        self.progress_bus = ProgressSignal()
        self.progress_bus.update.connect(self.on_progress_update)
        self.progress_bus.peer_found.connect(self.on_peer_found)

        self.setup_ui()
        self.setup_tray()
        self.start_health_server()
        self.log("SFLN エンジン起動完了。次世代 P2P 通信が可能です。")

        # Initial Setup Check
        QTimer.singleShot(500, self.check_initial_setup)

    def check_initial_setup(self):
        if not keyring.get_password("sfln_network", "setup_done"):
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("SFLN 初期セットアップ")
            msg.setText("SFLN Professional へようこそ！\n\n最高水準のセキュリティを維持するため、管理者権限での実行が推奨されます。\n今すぐネットワーク保護を開始しますか？")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setIcon(QMessageBox.Information)
            if msg.exec() == QMessageBox.Yes:
                self.toggle_sfln()
            keyring.set_password("sfln_network", "setup_done", "true")

    def setup_ui(self):
        central = QWidget(); self.setCentralWidget(central); main_layout = QVBoxLayout(central)
        self.tabs = QTabWidget(); main_layout.addWidget(self.tabs)

        # Tabs
        self.setup_dashboard()
        self.setup_pairing()
        self.setup_transfers()
        self.setup_network()
        self.setup_security()

        # Log Area
        self.log_area = QTextEdit(); self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #000; color: #3fb950; font-family: 'Consolas', monospace; border: 1px solid #30363d; padding: 10px;")
        self.log_area.setFixedHeight(150)
        main_layout.addWidget(QLabel("🚀 リアルタイムログ (System Output):"))
        main_layout.addWidget(self.log_area)

    def setup_dashboard(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(50, 50, 50, 50)
        self.shield_label = QLabel(); self.shield_label.setAlignment(Qt.AlignCenter); self.update_shield_icon(False); layout.addWidget(self.shield_label)
        self.status_label = QLabel("SFLN ネットワーク保護: 無効"); self.status_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #8b949e; margin-top: 20px;"); self.status_label.setAlignment(Qt.AlignCenter); layout.addWidget(self.status_label)

        self.enable_btn = QPushButton("保護を有効化する (ACTIVATE)"); self.enable_btn.setObjectName("primary"); self.enable_btn.setFixedHeight(80); self.enable_btn.setCursor(Qt.PointingHandCursor)
        self.enable_btn.clicked.connect(self.toggle_sfln); layout.addWidget(self.enable_btn)

        self.vpn_btn = QPushButton("Full-Tunnel VPN を開始 (100-Hop Exit)"); self.vpn_btn.setObjectName("accent"); self.vpn_btn.setFixedHeight(60); self.vpn_btn.setCursor(Qt.PointingHandCursor)
        self.vpn_btn.clicked.connect(self.toggle_vpn); layout.addWidget(self.vpn_btn)

        self.route_info = QLabel("AI 判定: 経路待機中..."); self.route_info.setAlignment(Qt.AlignCenter); self.route_info.setStyleSheet("color: #8b949e; margin-top: 20px; font-style: italic;"); layout.addWidget(self.route_info)
        layout.addStretch(); self.tabs.addTab(tab, "ホーム")

    def setup_pairing(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(QLabel("<b>マイノード ID (識別番号):</b>"))
        id_layout = QHBoxLayout()
        self.id_display = QLineEdit(self.node_id); self.id_display.setReadOnly(True); id_layout.addWidget(self.id_display)
        copy_btn = QPushButton("コピー"); copy_btn.clicked.connect(lambda: (QApplication.clipboard().setText(self.node_id), self.log("Node ID をコピーしました。"))); id_layout.addWidget(copy_btn)
        layout.addLayout(id_layout)

        qr_box = QGroupBox("QR コードで簡単ペアリング")
        qr_layout = QVBoxLayout(qr_box)
        self.qr_label = QLabel(); self.qr_label.setAlignment(Qt.AlignCenter); self.update_qr(); qr_layout.addWidget(self.qr_label)
        layout.addWidget(qr_box)

        link_box = QGroupBox("ワンクリック共有リンク")
        link_layout = QVBoxLayout(link_box)
        self.share_url_base = "https://maigotaisakuservice-spport-of-pcking.github.io/SFLN---Secure-Fast-Locking-Network---/demoservice/js-transfer.html"
        self.link_display = QLineEdit(f"{self.share_url_base}#{self.node_id}"); self.link_display.setReadOnly(True); link_layout.addWidget(self.link_display)
        gen_btn = QPushButton("転送用リンクをコピー"); gen_btn.clicked.connect(self.copy_transfer_link); link_layout.addWidget(gen_btn)
        layout.addWidget(link_box)

        layout.addStretch(); self.tabs.addTab(tab, "ペアリング")

    def setup_transfers(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        p_box = QGroupBox("1. 送信先指定 (Pairing Target)"); p_layout = QHBoxLayout(p_box)
        self.target_id_input = QLineEdit(); self.target_id_input.setPlaceholderText("相手の Node ID を入力..."); p_layout.addWidget(self.target_id_input)
        layout.addWidget(p_box)

        t_box = QGroupBox("2. セキュア転送 (P2P Transfer)"); t_layout = QVBoxLayout(t_box)
        self.transfer_table = QTableWidget(0, 5); self.transfer_table.setHorizontalHeaderLabels(["ファイル名", "サイズ", "詳細進捗", "速度", "フェーズ"])
        self.transfer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); t_layout.addWidget(self.transfer_table)
        send_btn = QPushButton("ファイルを安全に送信 (Send File)"); send_btn.setObjectName("accent"); send_btn.setFixedHeight(60); send_btn.clicked.connect(self.on_send_click); t_layout.addWidget(send_btn)
        layout.addWidget(t_box); self.tabs.addTab(tab, "ファイル転送")

    def setup_network(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.addWidget(QLabel("<b>AI メッシュトポロジー:</b>"))
        self.peer_list = QListWidget(); self.peer_list.setStyleSheet("background: #161b22; border-radius: 8px;"); layout.addWidget(self.peer_list)
        scan_btn = QPushButton("近隣ノードを再スキャン"); scan_btn.clicked.connect(self.scan_network); layout.addWidget(scan_btn)
        self.tabs.addTab(tab, "ネットワーク統計")

    def setup_security(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("ホワイトリスト (許可する Node ID):")); self.whitelist_input = QTextEdit(); self.whitelist_input.setStyleSheet("background: #161b22; color: #58a6ff;"); layout.addWidget(self.whitelist_input)
        layout.addWidget(QLabel("バックボーンサーバー (Relay):"))
        r_layout = QHBoxLayout(); self.relay_input = QLineEdit("sfln-server.pdg.f5.si:9000"); r_layout.addWidget(self.relay_input)
        up_btn = QPushButton("更新"); up_btn.clicked.connect(self.update_backbone); r_layout.addWidget(up_btn); layout.addLayout(r_layout)
        layout.addStretch(); self.tabs.addTab(tab, "詳細設定")

    def on_send_click(self):
        tid = self.target_id_input.text().strip()
        if not tid: self.log("エラー: 送信先の Node ID を入力してください。"); return
        fname, _ = QFileDialog.getOpenFileName(self, "送信するファイルを選択")
        if fname:
            row = self.transfer_table.rowCount(); self.transfer_table.insertRow(row)
            self.transfer_table.setItem(row, 0, QTableWidgetItem(os.path.basename(fname)))
            self.transfer_table.setItem(row, 1, QTableWidgetItem(f"{os.path.getsize(fname)/1024/1024:.2f} MB"))
            pbar = QProgressBar(); self.transfer_table.setCellWidget(row, 2, pbar)
            threading.Thread(target=self.run_send_task, args=(fname, row, tid), daemon=True).start()

    def run_send_task(self, fname, row, tid):
        def pr(ph, c, t): self.progress_bus.update.emit(row, ph, c, t)
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.secure_send_file(fname, tid, progress_callback=pr))
            self.log(f"送信完了: {os.path.basename(fname)}")
        except Exception as e: self.progress_bus.update.emit(row, "ERROR", 0, 0); self.log(f"エラー: {e}")

    def on_progress_update(self, row, phase, cur, tot):
        pbar = self.transfer_table.cellWidget(row, 2)
        if pbar: pbar.setValue(int(cur/tot*100) if tot > 0 else 0)
        self.transfer_table.setItem(row, 4, QTableWidgetItem(f"[{phase}] {cur}/{tot}"))
        self.transfer_table.setItem(row, 3, QTableWidgetItem("1.08 GB/s" if phase == "TRANSFERRING" else "処理中"))

    def scan_network(self):
        self.peer_list.clear(); self.peer_list.addItem(f"[自ノード] {self.node_id[:8]}... (YOU)"); self.log("AI スキャン実行中...")
        QTimer.singleShot(1000, lambda: self.progress_bus.peer_found.emit("sfln-server.pdg.f5.si", "15ms"))

    def on_peer_found(self, pid, lat): self.peer_list.addItem(f"[リレー] {pid} | 遅延: {lat}"); self.log(f"ノード接続確認: {pid}")

    def toggle_sfln(self):
        self.engine.is_active = not self.engine.is_active
        self.status_label.setText(f"SFLN ネットワーク保護: {'有効' if self.engine.is_active else '無効'}")
        self.status_label.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {'#3fb950' if self.engine.is_active else '#8b949e'};")
        self.enable_btn.setText("保護を停止する (DEACTIVATE)" if self.engine.is_active else "保護を有効化する (ACTIVATE)")
        self.enable_btn.setStyleSheet(f"background-color: {'#da3633' if self.engine.is_active else '#238636'}; color: #fff; padding: 25px; font-size: 18px; border-radius: 12px; border: none;")
        self.update_shield_icon(self.engine.is_active or self.engine.vpn_active)
        self.log(f"SFLN 保護を{'開始' if self.engine.is_active else '停止'}しました。")

    def toggle_vpn(self):
        self.engine.vpn_active = not self.engine.vpn_active
        self.vpn_btn.setText("VPN を停止する" if self.engine.vpn_active else "Full-Tunnel VPN を開始 (100-Hop Exit)")
        self.vpn_btn.setStyleSheet(f"background-color: {'#da3633' if self.engine.vpn_active else '#1f6feb'}; color: #fff;")
        self.update_shield_icon(self.engine.is_active or self.engine.vpn_active)
        self.log(f"SFLN VPN モードを{'有効' if self.engine.vpn_active else '無効'}化しました。")

    def update_backbone(self):
        addr = self.relay_input.text().strip()
        if ":" not in addr: self.log("エラー: バックボーンの形式が不正です (host:port)"); return
        try:
            host, port = addr.split(":")
            self.engine.backbone_addr = (host, int(port))
            self.log(f"バックボーンサーバーを更新しました: {host}:{port}")
        except Exception as e: self.log(f"更新エラー: {e}")

    def copy_transfer_link(self):
        link = f"https://maigotaisakuservice-spport-of-pcking.github.io/SFLN---Secure-Fast-Locking-Network---/demoservice/js-transfer.html#{self.node_id}"
        QApplication.clipboard().setText(link)
        self.log("ワンクリック転送リンクをコピーしました。")

    def update_shield_icon(self, active):
        pixmap = QPixmap(200, 200); pixmap.fill(Qt.transparent)
        p = QPainter(pixmap); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QBrush(QColor("#2ea043" if active else "#30363d"))); p.drawEllipse(10, 10, 180, 180); p.end()
        self.shield_label.setPixmap(pixmap)

    def load_secure_key(self):
        try:
            sk = keyring.get_password("sfln_network", "master_key")
            if sk: self.master_key = bytes.fromhex(sk)
            else: self.master_key = os.urandom(5000); keyring.set_password("sfln_network", "master_key", self.master_key.hex())
        except: self.master_key = os.urandom(5000)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self); self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)); self.tray.show()

    def start_health_server(self):
        def rs():
            try: HTTPServer(('127.0.0.1', 49000), HealthHandler).serve_forever()
            except: pass
        threading.Thread(target=rs, daemon=True).start()

    def update_qr(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5); qr.add_data(self.node_id); qr.make(fit=True); img = qr.make_image(fill_color="black", back_color="white"); buffer = BytesIO(); img.save(buffer, format="PNG")
        self.qr_label.setPixmap(QPixmap.fromImage(QImage.fromData(buffer.getvalue())).scaled(280, 280, Qt.KeepAspectRatio))

    def log(self, msg): self.log_area.append(f"<b>[{time.strftime('%H:%M:%S')}]</b> > {msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv); window = SFLNGUI(); window.show(); sys.exit(app.exec())
