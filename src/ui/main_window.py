from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QScrollArea,
    QProgressBar, QMessageBox, QFrame, QDialog, QListWidget, QListWidgetItem, QCheckBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
import os
from typing import List, Dict
from ..core.face_recognizer import FaceRecognizer, Person
from ..core.face_detector import FaceLocation, FaceDetector
from ..core.folder_monitor import FolderMonitor
import cv2
import numpy as np
import shutil

class ProcessingThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, recognizer: FaceRecognizer, folder_path: str):
        super().__init__()
        self.recognizer = recognizer
        self.folder_path = folder_path
        
    def run(self):
        try:
            def progress_callback(val):
                self.progress.emit(val)
            self.recognizer.scan_folder(self.folder_path, progress_callback=progress_callback)
            self.progress.emit(100)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class PhotoGalleryDialog(QDialog):
    def __init__(self, person: Person, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Photos of {person.name}")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(128, 128))
        layout.addWidget(self.list_widget)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)
        self.file_label = QLabel()
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)
        for photo_path in person.photo_paths:
            pixmap = QPixmap(photo_path).scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(QIcon(pixmap), photo_path)
            self.list_widget.addItem(item)
        self.list_widget.currentItemChanged.connect(self.show_preview)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        # Export button
        self.export_btn = QPushButton("Export Photos")
        self.export_btn.clicked.connect(self.export_photos)
        layout.addWidget(self.export_btn)
    def show_preview(self, current, previous):
        if current:
            path = current.text()
            pixmap = QPixmap(path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
            self.file_label.setText(path)
        else:
            self.preview_label.clear()
            self.file_label.clear()
    def export_photos(self):
        parent_dir = QFileDialog.getExistingDirectory(self, "Select Parent Folder for Export")
        if parent_dir:
            # Prompt for folder name
            folder_name, ok = QInputDialog.getText(self, "Folder Name", "Enter name for the new folder:", text=self.parent().person.name)
            if ok and folder_name:
                export_path = os.path.join(parent_dir, folder_name)
                os.makedirs(export_path, exist_ok=True)
                for photo_path in self.parent().person.photo_paths:
                    try:
                        shutil.copy(photo_path, export_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Export Error", f"Failed to copy {photo_path}: {e}")
                QMessageBox.information(self, "Export Complete", f"Exported {len(self.parent().person.photo_paths)} photos to {export_path}")

class PersonCard(QFrame):
    def __init__(self, person: Person, recognizer: FaceRecognizer, parent=None):
        super().__init__(parent)
        self.person = person
        self.recognizer = recognizer
        self.selected_checkbox = QCheckBox()
        self.name_label = None  # Store reference to name label
        self.setCursor(Qt.PointingHandCursor)
        self.setup_ui()
    def setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QHBoxLayout()
        # Checkbox
        layout.addWidget(self.selected_checkbox)
        # Face thumbnail
        thumb_label = QLabel()
        thumb_label.setFixedSize(64, 64)
        thumb_label.setStyleSheet("border-radius: 32px; background: #eee;")
        face_img = self.get_face_thumbnail()
        if face_img is not None:
            thumb_label.setPixmap(face_img)
        layout.addWidget(thumb_label)
        # Info
        info_layout = QVBoxLayout()
        self.name_label = QLabel(self.person.name)  # Store reference
        self.name_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(self.name_label)
        count_label = QLabel(f"{len(self.person.photo_paths)} photos")
        info_layout.addWidget(count_label)
        layout.addLayout(info_layout)
        
        # Add rename button
        rename_btn = QPushButton("Rename")
        rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        rename_btn.clicked.connect(self.rename_person)
        layout.addWidget(rename_btn)
        
        self.setLayout(layout)
    def get_face_thumbnail(self):
        # Use the most central face in the cluster as thumbnail
        if not self.person.face_indices:
            return None
        encs = self.person.face_encodings
        if len(encs) == 1:
            idx = 0
        else:
            center = np.mean(encs, axis=0)
            dists = [np.linalg.norm(enc - center) for enc in encs]
            idx = int(np.argmin(dists))
        face_idx = self.person.face_indices[idx]
        image_path, face_loc = self.recognizer.face_data[face_idx]
        detector = FaceDetector()
        face_img = detector.extract_face_image(image_path, face_loc)
        if face_img is not None and face_img.size > 0:
            rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return pixmap
        return None
    def is_selected(self):
        return self.selected_checkbox.isChecked()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.selected_checkbox.underMouse():
            dlg = PhotoGalleryDialog(self.person, self)
            dlg.exec_()
    def rename_person(self):
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Person",
            "Enter new name:",
            text=self.person.name
        )
        if ok and new_name and new_name != self.person.name:
            self.recognizer.rename_person(self.person.id, new_name)
            self.person.name = new_name
            # Update the name label using the stored reference
            if self.name_label:
                self.name_label.setText(new_name)

class MainWindow(QMainWindow):
    new_photo_signal = pyqtSignal(str)
    photo_deleted_signal = pyqtSignal(str)
    monitoring_started = pyqtSignal()
    monitoring_stopped = pyqtSignal()
    photo_processed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = FaceRecognizer()
        self.person_cards = []
        self.folder_monitor = None
        self.setup_ui()
        self.new_photo_signal.connect(self.handle_new_photo)
        self.photo_deleted_signal.connect(self.handle_photo_deleted)
        
    def setup_ui(self):
        self.setWindowTitle("Face Organizer")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        controls_layout.addWidget(self.select_folder_btn)
        
        self.monitor_btn = QPushButton("Start Monitoring")
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        self.monitor_btn.setEnabled(False)
        controls_layout.addWidget(self.monitor_btn)
        
        self.merge_btn = QPushButton("Merge Selected")
        self.merge_btn.clicked.connect(self.merge_selected)
        controls_layout.addWidget(self.merge_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        layout.addLayout(controls_layout)
        
        # Status label
        self.status_label = QLabel("No folder selected")
        layout.addWidget(self.status_label)
        
        # People grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.people_widget = QWidget()
        self.people_layout = QVBoxLayout(self.people_widget)
        scroll_area.setWidget(self.people_widget)
        
        layout.addWidget(scroll_area)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
            QLabel {
                color: #424242;
            }
        """)
        
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Photo Folder")
        if folder_path:
            self.process_folder(folder_path)
            
    def process_folder(self, folder_path: str):
        self.progress_bar.setVisible(True)
        self.select_folder_btn.setEnabled(False)
        self.status_label.setText(f"Processing folder: {folder_path}")
        
        self.processing_thread = ProcessingThread(self.recognizer, folder_path)
        self.processing_thread.progress.connect(self.progress_bar.setValue)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.error.connect(self.processing_error)
        self.processing_thread.start()
        
    def processing_finished(self):
        self.progress_bar.setVisible(False)
        self.select_folder_btn.setEnabled(True)
        self.monitor_btn.setEnabled(True)
        self.update_people_grid()
        self.status_label.setText("Processing complete. Ready to monitor for new photos.")
        
    def processing_error(self, error_msg: str):
        QMessageBox.critical(self, "Error", f"An error occurred: {error_msg}")
        self.progress_bar.setVisible(False)
        self.select_folder_btn.setEnabled(True)
        self.status_label.setText("Error occurred during processing.")
        
    def toggle_monitoring(self):
        if self.folder_monitor and self.folder_monitor.is_active():
            self.folder_monitor.stop()
            self.monitor_btn.setText("Start Monitoring")
            self.status_label.setText("Monitoring stopped.")
            self.monitoring_stopped.emit()
        else:
            self.start_monitoring()
            
    def start_monitoring(self):
        if not self.folder_monitor:
            self.folder_monitor = FolderMonitor(
                self.recognizer.current_folder,
                lambda path: self.new_photo_signal.emit(path),
                lambda path: self.photo_deleted_signal.emit(path)
            )
        self.folder_monitor.start()
        self.monitor_btn.setText("Stop Monitoring")
        self.status_label.setText("Monitoring for new photos...")
        self.monitoring_started.emit()
        
    def handle_new_photo(self, photo_path: str):
        try:
            self.recognizer.process_single_photo(photo_path)
            self.update_people_grid()
            self.status_label.setText(f"Processed new photo: {os.path.basename(photo_path)}")
            self.photo_processed.emit(photo_path)
        except PermissionError as e:
            error_msg = str(e)
            self.status_label.setText(f"Permission error: {os.path.basename(photo_path)}")
            QMessageBox.warning(
                self,
                "Permission Error",
                f"Cannot access the photo due to permission restrictions.\n\n"
                f"Please ensure the application has permission to access the file:\n{photo_path}\n\n"
                f"Try moving the photo to a different folder or running the application as administrator."
            )
        except Exception as e:
            error_msg = str(e)
            self.status_label.setText(f"Error: {os.path.basename(photo_path)}")
            QMessageBox.warning(
                self,
                "Processing Error",
                f"Failed to process the photo:\n{photo_path}\n\nError: {error_msg}"
            )
            
    def closeEvent(self, event):
        # Hide the window instead of closing
        event.ignore()
        self.hide()
        
    def update_people_grid(self):
        # Clear existing cards
        while self.people_layout.count():
            item = self.people_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add new cards
        self.person_cards = []
        people_sorted = sorted(self.recognizer.get_all_people(), key=lambda p: len(p.photo_paths), reverse=True)
        for person in people_sorted:
            card = PersonCard(person, self.recognizer)
            self.people_layout.addWidget(card)
            self.person_cards.append(card)
            
        # Add stretch to push cards to the top
        self.people_layout.addStretch()
        
    def merge_selected(self):
        selected_ids = [card.person.id for card in self.person_cards if card.is_selected()]
        if len(selected_ids) < 2:
            QMessageBox.warning(self, "Merge Error", "Select at least two people to merge.")
            return
        # Merge logic: merge all into the first selected
        main_id = selected_ids[0]
        for other_id in selected_ids[1:]:
            if other_id in self.recognizer.people:
                # Merge encodings, photos, indices
                self.recognizer.people[main_id].face_encodings.extend(self.recognizer.people[other_id].face_encodings)
                self.recognizer.people[main_id].photo_paths.update(self.recognizer.people[other_id].photo_paths)
                self.recognizer.people[main_id].face_indices.extend(self.recognizer.people[other_id].face_indices)
                del self.recognizer.people[other_id]
        self.update_people_grid()
        QMessageBox.information(self, "Merge Complete", f"Merged {len(selected_ids)} people into one.")
        
    def handle_photo_deleted(self, photo_path: str):
        try:
            # First, verify the photo exists in our data
            has_photo = False
            for person in self.recognizer.people.values():
                if photo_path in person.photo_paths:
                    has_photo = True
                    person.photo_paths.remove(photo_path)
            
            if not has_photo:
                # Photo wasn't in our data, just update UI
                self.update_people_grid()
                self.status_label.setText(f"Photo not found in database: {os.path.basename(photo_path)}")
                return
            
            # Find indices of faces to remove
            indices_to_remove = []
            for i, (path, _) in enumerate(self.recognizer.face_data):
                if path == photo_path:
                    indices_to_remove.append(i)
            
            if not indices_to_remove:
                # No faces to remove, just update UI
                self.update_people_grid()
                self.status_label.setText(f"Removed photo: {os.path.basename(photo_path)}")
                return
            
            # Create a mapping of old indices to new indices
            index_mapping = {}
            current_new_index = 0
            for i in range(len(self.recognizer.face_data)):
                if i not in indices_to_remove:
                    index_mapping[i] = current_new_index
                    current_new_index += 1
            
            # Remove face data in reverse order
            for i in sorted(indices_to_remove, reverse=True):
                if i < len(self.recognizer.face_data):
                    del self.recognizer.face_data[i]
                if i < len(self.recognizer.face_encodings):
                    del self.recognizer.face_encodings[i]
            
            # Update face indices in people using the mapping
            for person in self.recognizer.people.values():
                new_indices = []
                for old_idx in person.face_indices:
                    if old_idx not in indices_to_remove and old_idx in index_mapping:
                        new_indices.append(index_mapping[old_idx])
                person.face_indices = new_indices
            
            # Remove people with no photos
            people_to_remove = []
            for person_id, person in self.recognizer.people.items():
                if not person.photo_paths:
                    people_to_remove.append(person_id)
            
            for person_id in people_to_remove:
                del self.recognizer.people[person_id]
            
            # Update the UI
            self.update_people_grid()
            self.status_label.setText(f"Removed photo: {os.path.basename(photo_path)}")
            
        except Exception as e:
            # Log the error but don't show error message since the photo was actually removed
            print(f"Error during cleanup after photo removal: {str(e)}")
            # Still update the UI to reflect the changes
            self.update_people_grid()
            self.status_label.setText(f"Removed photo: {os.path.basename(photo_path)}") 