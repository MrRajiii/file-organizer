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

class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize attributes first
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
        self.preview_window = None
        self.duplicates_window = None
        self.dark_mode = False
        
        # Setup UI
        self.setWindowTitle("File Organizer Pro")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(1000, 800)
        self.setup_theme()
        
        # Main Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layouts
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        # Create UI components
        self.create_header()
        self.create_folder_selectors()
        self.create_options_section()
        self.create_rules_section()
        self.create_action_buttons()
        self.create_progress_bar()

    def setup_theme(self):
        """Set up light/dark theme with QPalette"""
        palette = QPalette()
        
        if self.dark_mode:
            # Dark theme
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 35, 35))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:
            # Light theme
            palette.setColor(QPalette.Window, QColor(240, 240, 240))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, Qt.white)
            palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            palette.setColor(QPalette.HighlightedText, Qt.white)
        
        QApplication.setPalette(palette)

    def create_header(self):
        """Create application header"""
        header = QLabel("File Organizer Pro")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("margin-bottom: 15px;")
        self.main_layout.addWidget(header)

    def create_folder_selectors(self):
        """Create source and destination folder selectors"""
        # Source Folder
        source_group = QGroupBox("Source Folder")
        source_layout = QHBoxLayout()
        
        self.source_entry = QLineEdit()
        self.source_entry.setPlaceholderText("Select source folder...")
        source_layout.addWidget(self.source_entry, 1)
        
        source_button = QPushButton("Browse...")
        source_button.clicked.connect(self.select_source)
        source_layout.addWidget(source_button)
        
        source_group.setLayout(source_layout)
        self.main_layout.addWidget(source_group)
        
        # Destination Folder
        dest_group = QGroupBox("Destination Folder")
        dest_layout = QHBoxLayout()
        
        self.dest_entry = QLineEdit()
        self.dest_entry.setPlaceholderText("Select destination folder...")
        dest_layout.addWidget(self.dest_entry, 1)
        
        dest_button = QPushButton("Browse...")
        dest_button.clicked.connect(self.select_destination)
        dest_layout.addWidget(dest_button)
        
        dest_group.setLayout(dest_layout)
        self.main_layout.addWidget(dest_group)

    def create_options_section(self):
        """Create duplicate detection options section"""
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # Duplicate detection
        dup_group = QGroupBox("Duplicate Detection")
        dup_layout = QVBoxLayout()
        
        self.dup_check = QCheckBox("Enable duplicate detection")
        self.dup_check.setChecked(True)
        dup_layout.addWidget(self.dup_check)
        
        # Detection method
        method_group = QButtonGroup(self)
        self.dup_name_radio = QRadioButton("Filename only")
        self.dup_content_radio = QRadioButton("File content (more accurate)")
        self.dup_content_radio.setChecked(True)
        
        method_group.addButton(self.dup_name_radio)
        method_group.addButton(self.dup_content_radio)
        
        method_layout = QHBoxLayout()
        method_layout.addWidget(self.dup_name_radio)
        method_layout.addWidget(self.dup_content_radio)
        method_layout.addStretch()
        
        dup_layout.addLayout(method_layout)
        dup_group.setLayout(dup_layout)
        options_layout.addWidget(dup_group)
        
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)

    def create_rules_section(self):
        """Create file organization rules section"""
        rules_group = QGroupBox("Organization Rules")
        self.main_layout.addWidget(rules_group, 1)  # Allow expansion
        
        # Scroll area for rules
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        rules_content = QWidget()
        self.rules_layout = QVBoxLayout(rules_content)
        self.rules_layout.setAlignment(Qt.AlignTop)
        
        # Add default file type rules
        for category, extensions in self.file_types.items():
            cb = QCheckBox(f"{category} ({', '.join(extensions)})")
            cb.setChecked(True)
            self.rules_layout.addWidget(cb)
            self.rule_checkboxes[category] = cb
        
        # Custom rule addition
        custom_group = QGroupBox("Add Custom Rule")
        custom_layout = QHBoxLayout()
        
        self.custom_category = QLineEdit()
        self.custom_category.setPlaceholderText("Category name")
        custom_layout.addWidget(self.custom_category)
        
        self.custom_extensions = QLineEdit()
        self.custom_extensions.setPlaceholderText(".ext1, .ext2")
        custom_layout.addWidget(self.custom_extensions)
        
        add_button = QPushButton("Add Rule")
        add_button.clicked.connect(self.add_custom_rule)
        custom_layout.addWidget(add_button)
        
        custom_group.setLayout(custom_layout)
        self.rules_layout.addWidget(custom_group)
        
        scroll.setWidget(rules_content)
        rules_group.setLayout(QVBoxLayout())
        rules_group.layout().addWidget(scroll)

    def create_action_buttons(self):
        """Create action buttons"""
        button_layout = QHBoxLayout()
        
        self.scan_dup_button = QPushButton("Scan for Duplicates")
        self.scan_dup_button.clicked.connect(self.scan_duplicates)
        self.scan_dup_button.setStyleSheet("padding: 8px;")
        button_layout.addWidget(self.scan_dup_button)
        
        self.preview_button = QPushButton("Preview Changes")
        self.preview_button.clicked.connect(self.preview_changes)
        self.preview_button.setStyleSheet("padding: 8px;")
        button_layout.addWidget(self.preview_button)
        
        self.organize_button = QPushButton("Organize Files")
        self.organize_button.clicked.connect(self.start_organization)
        self.organize_button.setStyleSheet("padding: 8px; background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.organize_button)
        
        self.main_layout.addLayout(button_layout)

    def create_progress_bar(self):
        """Create progress bar"""
        self.progress_label = QLabel("Ready")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.main_layout.addWidget(self.progress_bar)

    def select_source(self):
        """Select source folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_entry.setText(folder)

    def select_destination(self):
        """Select destination folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_entry.setText(folder)

    def add_custom_rule(self):
        """Add custom organization rule"""
        category = self.custom_category.text().strip()
        extensions = [ext.strip() for ext in self.custom_extensions.text().split(',')]
        
        if not category or not extensions:
            QMessageBox.critical(self, "Error", "Please enter both category name and extensions")
            return
        
        # Add to file types and create checkbox
        self.file_types[category] = extensions
        cb = QCheckBox(f"{category} ({', '.join(extensions)})")
        cb.setChecked(True)
        self.rules_layout.insertWidget(self.rules_layout.count() - 1, cb)  # Add before custom group
        self.rule_checkboxes[category] = cb
        
        # Clear input fields
        self.custom_category.clear()
        self.custom_extensions.clear()
        self.custom_extensions.setPlaceholderText(".ext1, .ext2")

    def calculate_file_hash(self, filepath):
        """Calculate MD5 hash of file content for duplicate detection"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {filepath}: {e}")
            return None

    def scan_duplicates(self):
        """Start duplicate file scanning"""
        if not self.validate_inputs(require_dest=False):
            return
        
        source = self.source_entry.text()
        method = "content" if self.dup_content_radio.isChecked() else "name"
        
        # Disable buttons during scan
        self.set_buttons_enabled(False)
        
        # Create and start worker thread
        self.scan_thread = ScanThread(source, method, self.dup_check.isChecked())
        self.scan_thread.progress_signal.connect(self.update_progress)
        self.scan_thread.finished.connect(self.on_scan_complete)
        self.scan_thread.start()

    def on_scan_complete(self, duplicates):
        """Handle completion of duplicate scanning"""
        self.set_buttons_enabled(True)
        
        if not duplicates:
            QMessageBox.information(self, "Scan Complete", "No duplicate files found!")
            return
        
        self.show_duplicates(duplicates)

    def show_duplicates(self, duplicates):
        """Display duplicate files in a new window"""
        if self.duplicates_window:
            self.duplicates_window.close()
        
        self.duplicates_window = QMainWindow(self)
        self.duplicates_window.setWindowTitle("Duplicate Files")
        self.duplicates_window.resize(800, 600)
        
        # Create tabs for each duplicate group
        tab_widget = QTabWidget()
        
        for group_id, (key, files) in enumerate(duplicates.items()):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # Create tree widget
            tree = QTreeWidget()
            tree.setHeaderLabels(["Filename", "Size", "Modified Date"])
            tree.setColumnCount(3)
            tree.setSortingEnabled(True)
            
            # Add files to tree
            for filename in files:
                filepath = os.path.join(self.source_entry.text(), filename)
                size = os.path.getsize(filepath)
                modified = os.path.getmtime(filepath)
                modified_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified))
                
                item = QTreeWidgetItem([filename, str(size), modified_str])
                item.setData(0, Qt.UserRole, filepath)  # Store full path
                tree.addTopLevelItem(item)
            
            # Add action buttons
            button_layout = QHBoxLayout()
            
            delete_all_button = QPushButton("Delete All But First")
            delete_all_button.clicked.connect(lambda: self.delete_duplicates(files, keep_first=True))
            button_layout.addWidget(delete_all_button)
            
            delete_selected_button = QPushButton("Delete Selected")
            delete_selected_button.clicked.connect(lambda: self.delete_selected_duplicates(tree))
            button_layout.addWidget(delete_selected_button)
            
            layout.addWidget(tree)
            layout.addLayout(button_layout)
            
            tab_widget.addTab(tab, f"Group {group_id+1} ({len(files)} files)")
        
        self.duplicates_window.setCentralWidget(tab_widget)
        self.duplicates_window.show()

    def delete_duplicates(self, files, keep_first=True):
        """Delete duplicate files"""
        if not files:
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete {len(files)-1 if keep_first else len(files)} duplicate files?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        source = self.source_entry.text()
        deleted = 0
        
        try:
            for i, filename in enumerate(files):
                if keep_first and i == 0:
                    continue  # Skip the first file
                
                filepath = os.path.join(source, filename)
                os.remove(filepath)
                deleted += 1
            
            QMessageBox.information(self, "Success", f"Deleted {deleted} duplicate files")
            self.scan_duplicates()  # Refresh
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete some files: {str(e)}")

    def delete_selected_duplicates(self, tree):
        """Delete selected files in duplicates list"""
        selected_items = tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "No files selected")
            return
        
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete {len(selected_items)} selected files?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        deleted = 0
        errors = []
        
        for item in selected_items:
            filepath = item.data(0, Qt.UserRole)
            try:
                os.remove(filepath)
                deleted += 1
            except Exception as e:
                errors.append(str(e))
        
        if errors:
            QMessageBox.critical(self, "Error", f"Deleted {deleted} files, but encountered errors:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Success", f"Deleted {deleted} files")
        
        self.scan_duplicates()  # Refresh

    def preview_changes(self):
        """Preview file organization changes"""
        if not self.validate_inputs():
            return
        
        source = self.source_entry.text()
        dest = self.dest_entry.text()
        
        # Get active rules
        active_rules = {cat: exts for cat, exts in self.file_types.items() 
                       if self.rule_checkboxes[cat].isChecked()}
        
        # Scan files and categorize
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
                        file_mapping[filename] = (filepath, os.path.join(dest_folder, filename))
                        moved = True
                        break
                
                if not moved:
                    other_files.append(filename)
        
        # Create preview window
        if self.preview_window:
            self.preview_window.close()
        
        self.preview_window = QMainWindow(self)
        self.preview_window.setWindowTitle("Preview Changes")
        self.preview_window.resize(800, 600)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Organized files tab
        org_tab = QWidget()
        org_layout = QVBoxLayout(org_tab)
        
        org_tree = QTreeWidget()
        org_tree.setHeaderLabels(["Filename", "New Location"])
        org_tree.setColumnCount(2)
        
        for filename, (_, new_path) in file_mapping.items():
            QTreeWidgetItem(org_tree, [filename, new_path])
        
        org_layout.addWidget(org_tree)
        tab_widget.addTab(org_tab, f"Organized Files ({len(file_mapping)})")
        
        # Other files tab
        other_tab = QWidget()
        other_layout = QVBoxLayout(other_tab)
        
        other_tree = QTreeWidget()
        other_tree.setHeaderLabels(["Filename"])
        other_tree.setColumnCount(1)
        
        for filename in other_files:
            QTreeWidgetItem(other_tree, [filename])
        
        other_layout.addWidget(other_tree)
        tab_widget.addTab(other_tab, f"Other Files ({len(other_files)})")
        
        self.preview_window.setCentralWidget(tab_widget)
        self.preview_window.show()

    def validate_inputs(self, require_dest=True):
        """Validate user inputs"""
        source = self.source_entry.text()
        dest = self.dest_entry.text()
        
        if not source or (require_dest and not dest):
            QMessageBox.critical(self, "Error", "Please select both source and destination folders")
            return False
        
        if not os.path.exists(source):
            QMessageBox.critical(self, "Error", "Source folder does not exist")
            return False
        
        if require_dest and not os.path.exists(dest):
            try:
                os.makedirs(dest)
            except OSError:
                QMessageBox.critical(self, "Error", "Could not create destination folder")
                return False
        
        if require_dest and source == dest:
            QMessageBox.critical(self, "Error", "Source and destination folders cannot be the same")
            return False
        
        return True

    def start_organization(self):
        """Start file organization process"""
        if not self.validate_inputs():
            return
        
        # Disable buttons during operation
        self.set_buttons_enabled(False)
        
        # Create and start worker thread
        self.organize_thread = OrganizeThread(
            self.source_entry.text(),
            self.dest_entry.text(),
            {cat: exts for cat, exts in self.file_types.items() 
             if self.rule_checkboxes[cat].isChecked()}
        )
        self.organize_thread.progress_signal.connect(self.update_progress)
        self.organize_thread.finished.connect(self.on_organization_complete)
        self.organize_thread.start()

    def on_organization_complete(self):
        """Handle completion of file organization"""
        self.set_buttons_enabled(True)
        QMessageBox.information(self, "Complete", "File organization finished!")

    def set_buttons_enabled(self, enabled):
        """Enable/disable action buttons"""
        self.scan_dup_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.organize_button.setEnabled(enabled)

    def update_progress(self, message, value, maximum):
        """Update progress bar and label"""
        self.progress_label.setText(message)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running threads
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.terminate()
        
        if hasattr(self, 'organize_thread') and self.organize_thread.isRunning():
            self.organize_thread.terminate()
        
        event.accept()

class ScanThread(QThread):
    """Thread for scanning duplicate files"""
    progress_signal = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    
    def __init__(self, source, method, enabled):
        super().__init__()
        self.source = source
        self.method = method
        self.enabled = enabled
    
    def run(self):
        if not self.enabled:
            self.finished.emit({})
            return
        
        files = [f for f in os.listdir(self.source) if os.path.isfile(os.path.join(self.source, f))]
        total_files = len(files)
        duplicates = {}
        
        if self.method == 'name':
            # Find duplicate filenames
            name_dict = {}
            for i, filename in enumerate(files):
                name_dict.setdefault(filename.lower(), []).append(filename)
                self.progress_signal.emit(f"Scanning... ({i+1}/{total_files})", i+1, total_files)
            
            duplicates = {k: v for k, v in name_dict.items() if len(v) > 1}
        else:
            # Find duplicate file contents
            hash_dict = {}
            for i, filename in enumerate(files):
                filepath = os.path.join(self.source, filename)
                file_hash = hashlib.md5(open(filepath, 'rb').read()).hexdigest()
                hash_dict.setdefault(file_hash, []).append(filename)
                self.progress_signal.emit(f"Scanning... ({i+1}/{total_files})", i+1, total_files)
            
            duplicates = {k: v for k, v in hash_dict.items() if len(v) > 1}
        
        self.progress_signal.emit("Scan complete!", total_files, total_files)
        self.finished.emit(duplicates)

class OrganizeThread(QThread):
    """Thread for organizing files"""
    progress_signal = pyqtSignal(str, int, int)
    finished = pyqtSignal()
    
    def __init__(self, source, dest, active_rules):
        super().__init__()
        self.source = source
        self.dest = dest
        self.active_rules = active_rules
    
    def run(self):
        # Create destination folders
        for category in self.active_rules.keys():
            os.makedirs(os.path.join(self.dest, category), exist_ok=True)
        
        # Process files
        files = [f for f in os.listdir(self.source) if os.path.isfile(os.path.join(self.source, f))]
        total_files = len(files)
        processed = 0
        
        for filename in files:
            filepath = os.path.join(self.source, filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            moved = False
            for category, extensions in self.active_rules.items():
                if ext in extensions:
                    dest_folder = os.path.join(self.dest, category)
                    try:
                        shutil.move(filepath, os.path.join(dest_folder, filename))
                        moved = True
                        break
                    except Exception as e:
                        self.progress_signal.emit(f"Error moving {filename}: {str(e)}", processed, total_files)
                        continue
            
            processed += 1
            self.progress_signal.emit(f"Processing... ({processed}/{total_files})", processed, total_files)
        
        self.progress_signal.emit("Organization complete!", processed, total_files)
        self.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = FileOrganizerApp()
    window.show()
    
    sys.exit(app.exec_())