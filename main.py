import sys
import os
import zipfile
import tarfile
import subprocess
from pathlib import Path

# 필수 라이브러리: pip install PySide6 py7zr
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QMessageBox,
    QStackedWidget, QFrame, QCheckBox, QComboBox, QListWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QCursor, QDragEnterEvent, QDropEvent

# 7z 지원 확인
try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

# --- 다국어 데이터 ---
LANG_DATA = {
    "Korean": {
        "comp": "압축", "ext": "풀기", "set": "설정",
        "comp_title": "파일/폴더 압축", "comp_sub": "항목을 추가하여 압축하세요.",
        "ext_title": "압축 해제", "ext_sub": "ZIP, 7z, TAR, ISO 지원",
        "set_title": "시스템 설정", "add": "+ 항목 추가", "clear": "비우기",
        "start_comp": "압축 시작", "start_ext": "지금 해제하기",
        "auto_open": "완료 후 폴더 열기", "theme": "테마 모드",
        "lang": "언어 설정", "def_fmt": "기본 압축 형식",
        "sel_file": "파일 선택", "no_file": "선택된 파일 없음",
        "success": "완료", "msg_done": "작업이 성공적으로 끝났습니다.",
        "error": "오류", "info": "ZipIt Pro v1.0.0 | Arrow Corp. 2026"
    },
    "English": {
        "comp": "Archive", "ext": "Extract", "set": "Settings",
        "comp_title": "Compress Items", "comp_sub": "Add items to archive.",
        "ext_title": "Extract Archive", "ext_sub": "Supports ZIP, 7z, TAR, ISO",
        "set_title": "Global Settings", "add": "+ Add Items", "clear": "Clear",
        "start_comp": "Start Compression", "start_ext": "Extract Now",
        "auto_open": "Open folder when done", "theme": "Theme Mode",
        "lang": "Language", "def_fmt": "Default Format",
        "sel_file": "Select File", "no_file": "No file selected",
        "success": "Success", "msg_done": "Task completed successfully.",
        "error": "Error", "info": "ZipIt Pro v1.0.0 | Arrow Corp. 2026"
    },
    "Japanese": {
        "comp": "圧縮", "ext": "解凍", "set": "設定",
        "comp_title": "圧縮する", "comp_sub": "項目を追加して圧縮してください。",
        "ext_title": "アーカイブ解凍", "ext_sub": "ZIP, 7z, TAR, ISO 対応",
        "set_title": "システム設定", "add": "+ 追加", "clear": "クリア",
        "start_comp": "圧縮시작", "start_ext": "今すぐ解凍",
        "auto_open": "完了後にフォルダを開く", "theme": "テーマ",
        "lang": "言語設定", "def_fmt": "基本形式",
        "sel_file": "파일選択", "no_file": "選択なし",
        "success": "完了", "msg_done": "正常に完了しました。",
        "error": "エラー", "info": "ZipIt Pro v1.0.0 | Arrow Corp. 2026"
    },
    "Chinese": {
        "comp": "压缩", "ext": "解压", "set": "设置",
        "comp_title": "文件压缩", "comp_sub": "添加项目进行压缩。",
        "ext_title": "解压缩", "ext_sub": "支持 ZIP, 7z, TAR, ISO",
        "set_title": "系统设置", "add": "+ 添加项目", "clear": "清空",
        "start_comp": "开始压缩", "start_ext": "立即解压",
        "auto_open": "完成后打开文件夹", "theme": "主题模式",
        "lang": "语言设置", "def_fmt": "默认格式",
        "sel_file": "选择文件", "no_file": "未选择文件",
        "success": "成功", "msg_done": "任务成功完成。",
        "error": "错误", "info": "ZipIt Pro v1.0.0 | Arrow Corp. 2026"
    }
}

class ZipWorker(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, mode, src_paths, dest_path, archive_format='zip'):
        super().__init__()
        self.mode = mode
        self.src_paths = src_paths
        self.dest_path = dest_path
        self.archive_format = archive_format

    def run(self):
        try:
            if self.mode == 'compress': self._compress()
            else: self._extract()
        except Exception as e: self.error.emit(str(e))

    def _compress(self):
        dest = Path(self.dest_path)
        all_files = []
        for p in self.src_paths:
            path_obj = Path(p)
            if path_obj.is_file(): all_files.append((path_obj, path_obj.name))
            else:
                for root, _, files in os.walk(path_obj):
                    for file in files:
                        full_path = Path(root) / file
                        rel_path = path_obj.name / full_path.relative_to(path_obj)
                        all_files.append((full_path, rel_path))
        
        total = len(all_files)
        if total == 0: raise Exception("No files to compress")
        
        fmt = self.archive_format.lower()
        if fmt == 'zip':
            with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, (f, arc) in enumerate(all_files):
                    zf.write(f, arc); self.progress.emit(int((i + 1) / total * 100))
        elif fmt == '7z' and HAS_7Z:
            with py7zr.SevenZipFile(dest, 'w') as sz:
                for i, (f, arc) in enumerate(all_files):
                    sz.write(f, arc); self.progress.emit(int((i + 1) / total * 100))
        elif fmt == 'tar':
            with tarfile.open(dest, 'w') as tf:
                for i, (f, arc) in enumerate(all_files):
                    tf.add(f, arcname=arc); self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit(str(dest.parent))

    def _extract(self):
        src = Path(self.src_paths[0]); dest = Path(self.dest_path)
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src, 'r') as zf:
                items = zf.infolist()
                for i, m in enumerate(items):
                    zf.extract(m, path=dest); self.progress.emit(int((i + 1) / len(items) * 100))
        elif HAS_7Z and py7zr.is_7zfile(src):
            with py7zr.SevenZipFile(src, mode='r') as sz:
                sz.extractall(path=dest); self.progress.emit(100)
        elif tarfile.is_tarfile(src):
            with tarfile.open(src, 'r:*') as tf:
                items = tf.getmembers()
                for i, m in enumerate(items):
                    tf.extract(m, path=dest); self.progress.emit(int((i + 1) / len(items) * 100))
        else: raise Exception("Unsupported format")
        self.finished.emit(str(dest))

class ZipItApp(QMainWindow):
    def __init__(self, initial_path=None):
        super().__init__()
        self.setWindowTitle("ZipIt Pro v1.0.0")
        self.resize(1000, 700)
        self.setAcceptDrops(True) # 드래그 앤 드롭 활성화
        
        # Default State
        self.target_paths = [initial_path] if initial_path else []
        self.archive_format = 'zip'
        self.open_folder_after = True
        self.theme = "Dark"
        self.current_lang = "Korean"
        
        self.init_ui()
        self.apply_theme()
        self.update_texts()
        
        if self.target_paths: self.process_inputs(self.target_paths)

    # --- 드래그 앤 드롭 이벤트 처리 ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_inputs(files)

    def apply_theme(self):
        if self.theme == "Dark":
            self.setStyleSheet("""
                QMainWindow { background-color: #0F0F0F; }
                #SideBar { background-color: #1A1A1A; border-right: 1px solid #2A2A2A; }
                #ContentArea { background-color: #0F0F0F; }
                QLabel { color: #FFFFFF; }
                #Title { font-size: 28px; font-weight: bold; color: #FFFFFF; }
                #SubTitle { color: #888888; font-size: 14px; }
                QListWidget { background-color: #1A1A1A; border: 1px solid #333; color: #EEE; border-radius: 12px; padding: 10px; }
                QPushButton#MenuBtn { background-color: transparent; color: #666; border: none; padding: 25px; font-weight: bold; font-size: 14px; }
                QPushButton#MenuBtn:hover { color: #BBB; background-color: #252525; }
                QPushButton#MenuBtn[active="true"] { color: #0A84FF; background-color: #252525; border-right: 4px solid #0A84FF; }
                QPushButton#ActionBtn { background-color: #0A84FF; color: white; border-radius: 12px; padding: 18px; font-size: 16px; font-weight: bold; border: 1px solid #3A9FFF; }
                QPushButton#ActionBtn:hover { background-color: #0070E0; }
                QPushButton#ActionBtn:disabled { background-color: #222; color: #444; border: 1px solid #333; }
                QPushButton#SubBtn { background-color: #2A2A2A; color: #DDD; border: 1px solid #444; border-radius: 8px; padding: 8px; }
                QPushButton#SubBtn:hover { background-color: #353535; }
                QProgressBar { border: none; border-radius: 4px; text-align: center; background-color: #222; color: transparent; height: 8px; }
                QProgressBar::chunk { background-color: #0A84FF; border-radius: 4px; }
                QComboBox, QCheckBox { background-color: #1A1A1A; color: #DDD; border: 1px solid #333; padding: 5px; border-radius: 5px; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #F2F2F7; }
                #SideBar { background-color: #FFFFFF; border-right: 1px solid #D1D1D6; }
                #ContentArea { background-color: #F2F2F7; }
                QLabel { color: #1C1C1E; }
                #Title { font-size: 28px; font-weight: bold; color: #1C1C1E; }
                #SubTitle { color: #8E8E93; font-size: 14px; }
                QListWidget { background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #1C1C1E; border-radius: 12px; padding: 10px; }
                QPushButton#MenuBtn { background-color: transparent; color: #8E8E93; border: none; padding: 25px; font-weight: bold; font-size: 14px; }
                QPushButton#MenuBtn:hover { color: #1C1C1E; background-color: #E5E5EA; }
                QPushButton#MenuBtn[active="true"] { color: #007AFF; background-color: #E5E5EA; border-right: 4px solid #007AFF; }
                QPushButton#ActionBtn { background-color: #007AFF; color: white; border-radius: 12px; padding: 18px; font-size: 16px; font-weight: bold; }
                QPushButton#ActionBtn:hover { background-color: #0062CC; }
                QPushButton#SubBtn { background-color: #FFFFFF; color: #1C1C1E; border: 1px solid #C7C7CC; border-radius: 8px; padding: 8px; }
                QProgressBar { border: none; border-radius: 4px; background-color: #D1D1D6; height: 8px; }
                QProgressBar::chunk { background-color: #007AFF; border-radius: 4px; }
            """)

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        
        container = QWidget(); container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("SideBar")
        side_lay = QVBoxLayout(self.sidebar); side_lay.setContentsMargins(0, 50, 0, 50); side_lay.setAlignment(Qt.AlignTop)

        self.btn_p1 = self.create_menu_btn("📦", 0)
        self.btn_p2 = self.create_menu_btn("🔓", 1)
        self.btn_p3 = self.create_menu_btn("⚙️", 2)

        side_lay.addWidget(self.btn_p1); side_lay.addWidget(self.btn_p2); side_lay.addWidget(self.btn_p3)
        main_layout.addWidget(self.sidebar)

        # Content
        self.stack = QStackedWidget(); self.stack.setObjectName("ContentArea")
        self.stack.addWidget(self.create_p1())
        self.stack.addWidget(self.create_p2())
        self.stack.addWidget(self.create_p3())
        main_layout.addWidget(self.stack); self.switch_page(0)

    def create_menu_btn(self, icon, idx):
        btn = QPushButton(icon); btn.setObjectName("MenuBtn"); btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.switch_page(idx))
        return btn

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate([self.btn_p1, self.btn_p2, self.btn_p3]):
            b.setProperty("active", i == idx); b.style().unpolish(b); b.style().polish(b)

    def create_p1(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(50, 50, 50, 50)
        self.title1 = QLabel(objectName="Title"); self.sub1 = QLabel(objectName="SubTitle")
        lay.addWidget(self.title1); lay.addWidget(self.sub1); lay.addSpacing(30)

        self.list_comp = QListWidget(); lay.addWidget(self.list_comp)
        
        h = QHBoxLayout(); self.btn_add = QPushButton(objectName="SubBtn"); self.btn_clear = QPushButton(objectName="SubBtn")
        self.btn_add.clicked.connect(self.add_items); self.btn_clear.clicked.connect(self.list_comp.clear)
        h.addWidget(self.btn_add); h.addWidget(self.btn_clear); lay.addLayout(h)
        
        lay.addSpacing(30); self.run_comp = QPushButton(objectName="ActionBtn")
        self.run_comp.clicked.connect(lambda: self.run_task('compress'))
        lay.addWidget(self.run_comp); self.bar1 = QProgressBar(); lay.addWidget(self.bar1)
        return w

    def create_p2(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(50, 50, 50, 50)
        self.title2 = QLabel(objectName="Title"); self.sub2 = QLabel(objectName="SubTitle")
        lay.addWidget(self.title2); lay.addWidget(self.sub2); lay.addSpacing(30)

        self.ext_info = QLabel(); lay.addWidget(self.ext_info)
        self.btn_sel = QPushButton(objectName="SubBtn"); self.btn_sel.clicked.connect(self.select_extract_file)
        lay.addWidget(self.btn_sel); lay.addStretch()

        self.run_ext = QPushButton(objectName="ActionBtn")
        self.run_ext.clicked.connect(lambda: self.run_task('extract'))
        lay.addWidget(self.run_ext); self.bar2 = QProgressBar(); lay.addWidget(self.bar2)
        return w

    def create_p3(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(50, 50, 50, 50)
        self.title3 = QLabel(objectName="Title"); lay.addWidget(self.title3); lay.addSpacing(40)
        
        self.chk_open = QCheckBox(); self.chk_open.setChecked(True); self.chk_open.stateChanged.connect(self.save_settings)
        lay.addWidget(self.chk_open); lay.addSpacing(20)

        lay.addWidget(QLabel("Theme / 테마 / テーマ / 主题"))
        self.cmb_thm = QComboBox(); self.cmb_thm.addItems(["Dark", "Light"]); self.cmb_thm.currentTextChanged.connect(self.save_settings)
        lay.addWidget(self.cmb_thm); lay.addSpacing(20)

        lay.addWidget(QLabel("Language / 언어 / 言語 / 语言"))
        self.cmb_lang = QComboBox(); self.cmb_lang.addItems(["Korean", "English", "Japanese", "Chinese"])
        self.cmb_lang.currentTextChanged.connect(self.save_settings)
        lay.addWidget(self.cmb_lang); lay.addSpacing(20)

        lay.addWidget(QLabel("Format / 형식 / 形式"))
        self.cmb_fmt = QComboBox(); self.cmb_fmt.addItems(["ZIP", "7Z", "TAR"]); self.cmb_fmt.currentTextChanged.connect(self.save_settings)
        lay.addWidget(self.cmb_fmt); lay.addStretch()

        self.info_lbl = QLabel(objectName="SubTitle"); self.info_lbl.setAlignment(Qt.AlignCenter); lay.addWidget(self.info_lbl)
        return w

    def update_texts(self):
        d = LANG_DATA[self.current_lang]
        self.btn_p1.setText(f"📦\n{d['comp']}"); self.btn_p2.setText(f"🔓\n{d['ext']}"); self.btn_p3.setText(f"⚙️\n{d['set']}")
        self.title1.setText(d['comp_title']); self.sub1.setText(d['comp_sub'])
        self.title2.setText(d['ext_title']); self.sub2.setText(d['ext_sub'])
        self.title3.setText(d['set_title'])
        self.btn_add.setText(d['add']); self.btn_clear.setText(d['clear'])
        self.run_comp.setText(d['start_comp']); self.run_ext.setText(d['start_ext'])
        self.chk_open.setText(d['auto_open']); self.btn_sel.setText(d['sel_file'])
        self.info_lbl.setText(d['info'])
        if not self.target_paths: self.ext_info.setText(d['no_file'])

    def save_settings(self):
        self.open_folder_after = self.chk_open.isChecked()
        self.archive_format = self.cmb_fmt.currentText().lower()
        self.current_lang = self.cmb_lang.currentText()
        if self.cmb_thm.currentText() != self.theme:
            self.theme = self.cmb_thm.currentText(); self.apply_theme()
        self.update_texts()

    def add_items(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Add Files"); self.list_comp.addItems(fs)
        f = QFileDialog.getExistingDirectory(self, "Add Folder")
        if f: self.list_comp.addItem(f)

    def select_extract_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Archive", "", "Archives (*.zip *.7z *.tar *.iso)")
        if f:
            self.target_paths = [f]; self.ext_info.setText(f"{LANG_DATA[self.current_lang]['sel_file']}: {Path(f).name}")
            self.run_ext.setEnabled(True)

    def process_inputs(self, paths):
        p = paths[0]
        # 압축 파일인지 확인 (zip 구조 또는 특정 확장자)
        if zipfile.is_zipfile(p) or p.lower().endswith(('.7z', '.tar', '.iso')):
            self.switch_page(1)
            self.target_paths = [p]
            self.ext_info.setText(f"{LANG_DATA[self.current_lang]['sel_file']}: {Path(p).name}")
            self.run_ext.setEnabled(True)
        else:
            # 여러 파일 드롭 시 모두 추가
            self.switch_page(0)
            self.list_comp.addItems(paths)

    def run_task(self, mode):
        paths = [self.list_comp.item(i).text() for i in range(self.list_comp.count())] if mode == 'compress' else self.target_paths
        if not paths: return
        dest = str(Path(paths[0]).parent / (f"Archive_{Path(paths[0]).stem}.{self.archive_format}" if mode == 'compress' else Path(paths[0]).stem))
        if mode == 'extract': os.makedirs(dest, exist_ok=True)
        
        pb = self.bar1 if mode == 'compress' else self.bar2; pb.setValue(0)
        self.worker = ZipWorker(mode, paths, dest, self.archive_format)
        self.worker.progress.connect(pb.setValue)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, LANG_DATA[self.current_lang]['error'], e))
        self.worker.start()

    def on_success(self, folder):
        if self.open_folder_after:
            if sys.platform == 'win32': os.startfile(folder)
            else: subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder])
        else: QMessageBox.information(self, LANG_DATA[self.current_lang]['success'], LANG_DATA[self.current_lang]['msg_done'])

if __name__ == "__main__":
    app = QApplication(sys.argv); window = ZipItApp(initial_path=sys.argv[1] if len(sys.argv) > 1 else None)
    window.show(); sys.exit(app.exec())