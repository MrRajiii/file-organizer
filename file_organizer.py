import os
import sys
import hashlib
import shutil
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QFileDialog,
    QMessageBox, QGroupBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

class FileService:
    
    def __init__(self, file_types):
        self.file_types = file_types

    @staticmethod
    def calculate_file_hash(filepath):
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None

    def find_duplicates(self, source_dir, method, progress_callback=None):
        files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
        total_files = len(files)
        key_dict = {}

        for i, filename in enumerate(files):
            filepath = os.path.join(source_dir, filename)
            
            if method == 'name':
                key = filename.lower()
            elif method == 'content':
                key = self.calculate_file_hash(filepath)
                if key is None: continue 

            key_dict.setdefault(key, []).append(filename)
            
            if progress_callback:
                progress_callback(f"Scanning... ({i+1}/{total_files})", i + 1, total_files)

        duplicates = {k: v for k, v in key_dict.items() if len(v) > 1}
        
        if progress_callback:
             progress_callback("Scan complete!", total_files, total_files)
             
        return duplicates

    def organize_files(self, source_dir, dest_dir, active_rules, progress_callback=None):
        for category in active_rules.keys():
            os.makedirs(os.path.join(dest_dir, category), exist_ok=True)
        
        files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
        total_files = len(files)
        processed = 0

        for filename in files:
            filepath = os.path.join(source_dir, filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            for category, extensions in active_rules.items():
                if ext in extensions:
                    dest_folder = os.path.join(dest_dir, category)
                    try:
                        shutil.move(filepath, os.path.join(dest_folder, filename))
                        break
                    except Exception as e:
                        print(f"Error moving {filename}: {e}")
                        break
            
            processed += 1
            if progress_callback:
                progress_callback(f"Processing... ({processed}/{total_files})", processed, total_files)
        
        return processed

class ScanThread(QThread):
    progress_signal = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    
    def __init__(self, source, method, enabled, file_service):
        super().__init__()
        self.source = source
        self.method = method
        self.enabled = enabled
        self.file_service = file_service

    def run(self):
        if not self.enabled:
            self.finished.emit({})
            return
        
        duplicates = self.file_service.find_duplicates(
            self.source, 
            self.method, 
            progress_callback=self.progress_signal.emit
        )
        self.finished.emit(duplicates)


class OrganizeThread(QThread):
    progress_signal = pyqtSignal(str, int, int)
    finished = pyqtSignal()
    
    def __init__(self, source, dest, active_rules, file_service):
        super().__init__()
        self.source = source
        self.dest = dest
        self.active_rules = active_rules
        self.file_service = file_service

    def run(self):
        self.file_service.organize_files(
            self.source,
            self.dest,
            self.active_rules,
            progress_callback=self.progress_signal.emit
        )
        self.finished.emit()
        
class DuplicateWindow(QMainWindow):
    def __init__(self, parent, source_dir, duplicates, file_service):
        super().__init__(parent)
        self.source_dir = source_dir
        self.duplicates_data = duplicates
        self.file_service = file_service
        self.parent_app = parent
        
        self.setWindowTitle("Duplicate Files Management")
        self.resize(800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.tab_widget = QTabWidget()
        self.build_tabs()
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.tab_widget)

    def build_tabs(self):
        for group_id, (key, files) in enumerate(self.duplicates_data.items()):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            tree = self._create_tree_widget(files)
            
            button_layout = QHBoxLayout()
            
            delete_all_button = QPushButton("Delete All But First")
            delete_all_button.clicked.connect(lambda _, f=files: self._delete_duplicates(f, keep_first=True))
            button_layout.addWidget(delete_all_button)
            
            delete_selected_button = QPushButton("Delete Selected")
            delete_selected_button.clicked.connect(lambda _, t=tree: self._delete_selected_duplicates(t))
            button_layout.addWidget(delete_selected_button)
            
            layout.addWidget(QLabel(f"Key: {key[:10]}..."))
            layout.addWidget(tree)
            layout.addLayout(button_layout)
            
            self.tab_widget.addTab(tab, f"Group {group_id+1} ({len(files)} files)")
            
    def _create_tree_widget(self, files):
        tree = QTreeWidget()
        tree.setHeaderLabels(["Filename", "Size", "Modified Date"])
        tree.setColumnCount(3)
        tree.setSortingEnabled(True)
        tree.setSelectionMode(QTreeWidget.ExtendedSelection)

        for filename in files:
            filepath = os.path.join(self.source_dir, filename)
            if not os.path.exists(filepath):
                 continue
                 
            size = os.path.getsize(filepath)
            modified = os.path.getmtime(filepath)
            modified_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified))
            
            item = QTreeWidgetItem([filename, str(size), modified_str])
            item.setData(0, Qt.UserRole, filepath)
            tree.addTopLevelItem(item)
        
        tree.expandAll()
        for i in range(tree.columnCount()):
             tree.resizeColumnToContents(i)
        return tree

    def _delete_duplicates(self, files, keep_first=True):
        to_delete = files[1:] if keep_first else files
        self._execute_deletion(to_delete)

    def _delete_selected_duplicates(self, tree):
        selected_items = tree.selectedItems()
        to_delete = [item.data(0, Qt.UserRole) for item in selected_items]
        self._execute_deletion(to_delete, is_filepath=True)

    def _execute_deletion(self, file_list, is_filepath=False):
        if not file_list: return
        
        confirm = QMessageBox.question(self, "Confirm Deletion", f"Permanently delete {len(file_list)} files?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes: return
        
        deleted = 0
        source = self.source_dir
        
        for item in file_list:
            filepath = item if is_filepath else os.path.join(source, item)
            try:
                os.remove(filepath)
                deleted += 1
            except Exception as e:
                print(f"Failed to delete {filepath}: {e}")
        
        QMessageBox.information(self, "Success", f"Deleted {deleted} files.")
        self.parent_app.scan_duplicates()
        self.close()


class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.file_types = {
            "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            "Documents": ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
            "Audio": ['.mp3', '.wav', '.ogg', '.flac', '.aac'],
            "Video": ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
            "Archives": ['.zip', '.rar', '.7z', '.tar', '.gz'],
            "Executables": ['.exe', '.msi', '.dmg', '.pkg', '.deb'],
            "Code": ['.py', '.js', '.html', '.css', '.cpp', '.java', '.php', '.json', '.xml']
        }
        self.rule_checkboxes = {}
        self.dark_mode = True
        self.preview_window = None
        self.duplicates_window = None
        
        self.file_service = FileService(self.file_types) 
        
        self.setWindowTitle("File Organizer Pro")
        self.setWindowIcon(QIcon("icon.png")) 
        self.resize(1200, 800)
        
        self.setup_theme()
        self.apply_qss()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.create_side_panel()
        self.create_main_panel()

    def setup_theme(self):
        palette = QPalette()
        ACCENT = QColor(0, 150, 255)
        
        if self.dark_mode:
            BG = QColor(30, 30, 30)
            FG = Qt.white
            ALT = QColor(40, 40, 40)
            BASE = QColor(20, 20, 20)
        else:
            BG = QColor(240, 240, 240)
            FG = Qt.black
            ALT = QColor(220, 220, 220)
            BASE = Qt.white

        palette.setColor(QPalette.Window, BG)
        palette.setColor(QPalette.WindowText, FG)
        palette.setColor(QPalette.Base, BASE)
        palette.setColor(QPalette.AlternateBase, ALT)
        palette.setColor(QPalette.Text, FG)
        palette.setColor(QPalette.Button, ALT)
        palette.setColor(QPalette.ButtonText, FG)
        palette.setColor(QPalette.Highlight, ACCENT)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        
        QApplication.setPalette(palette)

    def apply_qss(self):
        qss = """
        QMainWindow, QWidget {
            background-color: rgb(30, 30, 30);
            color: white;
            font-family: "Segoe UI", sans-serif;
        }
        
        #SidePanel { 
            background-color: rgb(35, 35, 35); 
            border-right: 1px solid rgb(50, 50, 50);
        }
        QGroupBox {
            font-weight: bold;
            font-size: 13px;
            margin-top: 15px;
            border: 1px solid rgb(50, 50, 50);
            border-radius: 8px;
            padding-top: 20px;
        }

        QLineEdit {
            padding: 8px;
            border: 1px solid rgb(70, 70, 70);
            border-radius: 4px;
            background-color: rgb(40, 40, 40);
        }
        
        QPushButton {
            padding: 10px 15px;
            border-radius: 5px;
            background-color: rgb(60, 60, 60);
            color: white;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: rgb(80, 80, 80);
        }

        #OrganizeButton { 
            background-color: #4CAF50;
            font-weight: bold;
        }
        #OrganizeButton:hover {
            background-color: #5cb860;
        }
        
        QProgressBar {
            text-align: center;
            border: 1px solid rgb(50, 50, 50);
            border-radius: 5px;
            background-color: rgb(40, 40, 40);
            color: white;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: rgb(0, 150, 255);
            border-radius: 5px;
        }
        
        QTreeWidget {
            background-color: rgb(35, 35, 35);
            alternate-background-color: rgb(40, 40, 40);
            border: 1px solid rgb(50, 50, 50);
        }
        QTreeWidget::item:selected {
            background-color: rgb(0, 150, 255);
        }
        """
        self.setStyleSheet(qss)
        
    def create_side_panel(self):
        side_panel = QWidget()
        side_panel.setObjectName("SidePanel")
        side_panel.setFixedWidth(400)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(15, 20, 15, 15)
        side_layout.setSpacing(15)

        self.create_header(side_layout)
        self.create_folder_selectors(side_layout)
        self.create_options_section(side_layout)
        self.create_rules_section(side_layout)
        
        self.main_layout.addWidget(side_panel)

    def create_main_panel(self):
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        status_group = QGroupBox("Operation Status & Progress")
        status_layout = QVBoxLayout(status_group)
        self.create_progress_bar(status_layout)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QWidget(), "Organization Log")
        main_layout.addWidget(self.tab_widget, 1)

        self.create_action_buttons(main_layout)
        
        self.main_layout.addWidget(main_panel, 1)

    def create_header(self, parent_layout):
        header = QLabel("File Organizer Pro")
        header.setFont(QFont("Segoe UI", 20, QFont.ExtraBold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: rgb(0, 150, 255); margin-bottom: 5px;")
        parent_layout.addWidget(header)
        
        tagline = QLabel("Smartly sort and manage your digital workspace.")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: rgb(180, 180, 180); font-size: 10pt; margin-bottom: 10px;")
        parent_layout.addWidget(tagline)
        
    def create_folder_selectors(self, parent_layout):
        source_group = QGroupBox("Source Folder")
        source_layout = QHBoxLayout()
        self.source_entry = QLineEdit()
        self.source_entry.setPlaceholderText("Select folder to organize...")
        source_layout.addWidget(self.source_entry, 1)
        source_button = QPushButton("Browse")
        source_button.clicked.connect(self.select_source)
        source_layout.addWidget(source_button)
        source_group.setLayout(source_layout)
        parent_layout.addWidget(source_group)
        
        dest_group = QGroupBox("Destination Root")
        dest_layout = QHBoxLayout()
        self.dest_entry = QLineEdit()
        self.dest_entry.setPlaceholderText("Select root folder for categorized files...")
        dest_layout.addWidget(self.dest_entry, 1)
        dest_button = QPushButton("Browse")
        dest_button.clicked.connect(self.select_destination)
        dest_layout.addWidget(dest_button)
        dest_group.setLayout(dest_layout)
        parent_layout.addWidget(dest_group)

    def create_options_section(self, parent_layout):
        options_group = QGroupBox("Optimization & Duplicate Options")
        options_layout = QVBoxLayout()
        
        self.dup_check = QCheckBox("Enable duplicate detection (Recommended)")
        self.dup_check.setChecked(True)
        options_layout.addWidget(self.dup_check)
        
        method_group = QButtonGroup(self)
        self.dup_name_radio = QRadioButton("Filename Only (Fast)")
        self.dup_content_radio = QRadioButton("File Content (Accurate)")
        self.dup_content_radio.setChecked(True)
        method_group.addButton(self.dup_name_radio)
        method_group.addButton(self.dup_content_radio)
        
        method_layout = QHBoxLayout()
        method_layout.addWidget(self.dup_name_radio)
        method_layout.addWidget(self.dup_content_radio)
        method_layout.addStretch()
        
        options_layout.addLayout(method_layout)
        options_group.setLayout(options_layout)
        parent_layout.addWidget(options_group)

    def create_rules_section(self, parent_layout):
        rules_group = QGroupBox("Active Organization Rules")
        parent_layout.addWidget(rules_group, 1)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        rules_content = QWidget()
        self.rules_layout = QVBoxLayout(rules_content)
        self.rules_layout.setAlignment(Qt.AlignTop)
        
        for category, extensions in self.file_types.items():
            cb = QCheckBox(f"**{category}** ({', '.join(extensions)})")
            cb.setChecked(True)
            self.rules_layout.addWidget(cb)
            self.rule_checkboxes[category] = cb
        
        custom_group = QGroupBox("Add Custom Rule")
        custom_layout = QHBoxLayout()
        self.custom_category = QLineEdit()
        self.custom_category.setPlaceholderText("New Category Name")
        self.custom_extensions = QLineEdit()
        self.custom_extensions.setPlaceholderText(".ext1, .ext2, ...")
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_custom_rule)
        
        custom_layout.addWidget(self.custom_category)
        custom_layout.addWidget(self.custom_extensions)
        custom_layout.addWidget(add_button)
        
        custom_group.setLayout(custom_layout)
        self.rules_layout.addWidget(custom_group)
        
        self.rules_layout.addStretch()
        scroll.setWidget(rules_content)
        rules_group.setLayout(QVBoxLayout())
        rules_group.layout().addWidget(scroll)

    def create_action_buttons(self, parent_layout):
        button_layout = QHBoxLayout()
        
        self.scan_dup_button = QPushButton("🔍 Scan for Duplicates")
        self.scan_dup_button.clicked.connect(self.scan_duplicates)
        button_layout.addWidget(self.scan_dup_button)
        
        self.preview_button = QPushButton("📊 Preview Changes")
        self.preview_button.clicked.connect(self.preview_changes)
        button_layout.addWidget(self.preview_button)
        
        self.organize_button = QPushButton("🚀 Organize Files")
        self.organize_button.setObjectName("OrganizeButton")
        self.organize_button.clicked.connect(self.start_organization)
        button_layout.addWidget(self.organize_button)
        
        parent_layout.addLayout(button_layout)
        
    def create_progress_bar(self, parent_layout):
        self.progress_label = QLabel("Ready. Select your source folder to begin.")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont("Segoe UI", 10))
        parent_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        parent_layout.addWidget(self.progress_bar)

    def select_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_entry.setText(folder)
            self.update_file_count(folder)

    def update_file_count(self, source_folder):
        if not os.path.exists(source_folder):
            self.progress_label.setText("Source folder not found.")
            return

        try:
            file_count = sum(1 for entry in os.scandir(source_folder) if entry.is_file())
            self.progress_label.setText(f"**Ready.** Found **{file_count}** files in source directory.")
        except Exception:
            self.progress_label.setText("Error reading file count.")

    def select_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_entry.setText(folder)

    def add_custom_rule(self):
        category = self.custom_category.text().strip()
        extensions = [ext.strip().lower() for ext in self.custom_extensions.text().split(',') if ext.strip()]
        
        if not category or not extensions:
            QMessageBox.critical(self, "Error", "Please enter both category name and extensions.")
            return
        
        self.file_types[category] = extensions
        cb = QCheckBox(f"**{category}** ({', '.join(extensions)})")
        cb.setChecked(True)
        self.rules_layout.insertWidget(self.rules_layout.count() - 2, cb) 
        self.rule_checkboxes[category] = cb
        
        self.custom_category.clear()
        self.custom_extensions.clear()
        QMessageBox.information(self, "Success", f"Custom rule '{category}' added.")


    def validate_inputs(self, require_dest=True):
        source = self.source_entry.text()
        dest = self.dest_entry.text()
        
        if not source or (require_dest and not dest):
            QMessageBox.critical(self, "Error", "Please select both source and destination folders.")
            return False
        
        if require_dest and source == dest:
            QMessageBox.critical(self, "Error", "Source and destination folders cannot be the same.")
            return False
            
        return True

    def scan_duplicates(self):
        if not self.validate_inputs(require_dest=False): return
        
        source = self.source_entry.text()
        method = "content" if self.dup_content_radio.isChecked() else "name"
        
        self.set_buttons_enabled(False)
        self.progress_label.setText("Starting duplicate scan...")
        
        self.scan_thread = ScanThread(source, method, self.dup_check.isChecked(), self.file_service)
        self.scan_thread.progress_signal.connect(self.update_progress)
        self.scan_thread.finished.connect(self.on_scan_complete)
        self.scan_thread.start()

    def on_scan_complete(self, duplicates):
        self.set_buttons_enabled(True)
        
        if not duplicates:
            QMessageBox.information(self, "Scan Complete", "No duplicate files found!")
            self.progress_label.setText("Scan complete! No duplicates found.")
            return
        
        self.duplicates_window = DuplicateWindow(self, self.source_entry.text(), duplicates, self.file_service)
        self.duplicates_window.show()
        self.progress_label.setText(f"Scan complete! Found {len(duplicates)} groups of duplicates.")

    def preview_changes(self):
        if not self.validate_inputs(): return
        
        active_rules = {cat: exts for cat, exts in self.file_types.items() 
                         if self.rule_checkboxes.get(cat) and self.rule_checkboxes[cat].isChecked()}
                         
        source = self.source_entry.text()
        dest = self.dest_entry.text()
        file_mapping = {}
        other_files = []
        
        for filename in os.listdir(source):
            filepath = os.path.join(source, filename)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                
                moved = False
                for category, extensions in active_rules.items():
                    if ext in extensions:
                        dest_folder = os.path.join(dest, category)
                        file_mapping[filename] = os.path.join(dest_folder, filename)
                        moved = True
                        break
                
                if not moved:
                    other_files.append(filename)
        
        if self.preview_window: self.preview_window.close()
        
        self.preview_window = QMainWindow(self)
        self.preview_window.setWindowTitle("Organization Preview")
        self.preview_window.resize(800, 600)
        
        tab_widget = QTabWidget()
        org_tree = QTreeWidget()
        org_tree.setHeaderLabels(["Filename", "New Location"])
        
        for filename, new_path in file_mapping.items():
            QTreeWidgetItem(org_tree, [filename, new_path])
        
        tab_widget.addTab(org_tree, f"Files to be Organized ({len(file_mapping)})")
        self.preview_window.setCentralWidget(tab_widget)
        self.preview_window.show()


    def start_organization(self):
        if not self.validate_inputs(): return
        
        self.set_buttons_enabled(False)
        self.progress_label.setText("Starting file organization...")
        
        active_rules = {cat: exts for cat, exts in self.file_types.items() 
                         if self.rule_checkboxes.get(cat) and self.rule_checkboxes[cat].isChecked()}

        self.organize_thread = OrganizeThread(
            self.source_entry.text(),
            self.dest_entry.text(),
            active_rules,
            self.file_service
        )
        self.organize_thread.progress_signal.connect(self.update_progress)
        self.organize_thread.finished.connect(self.on_organization_complete)
        self.organize_thread.start()

    def on_organization_complete(self):
        self.set_buttons_enabled(True)
        QMessageBox.information(self, "Complete", "File organization finished!")
        self.update_file_count(self.source_entry.text())

    def set_buttons_enabled(self, enabled):
        self.scan_dup_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.organize_button.setEnabled(enabled)

    def update_progress(self, message, value, maximum):
        self.progress_label.setText(message)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def closeEvent(self, event):
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.terminate()
        if hasattr(self, 'organize_thread') and self.organize_thread.isRunning():
            self.organize_thread.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion") 
    
    window = FileOrganizerApp()
    window.show()
    
    sys.exit(app.exec_())