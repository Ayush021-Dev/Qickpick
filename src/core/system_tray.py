from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal
import os
import sys
import winreg
import logging

class SystemTrayService(QObject):
    show_ui_signal = pyqtSignal()
    stop_monitoring_signal = pyqtSignal()
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tray_icon = None
        self.setup_tray()
        self.setup_logging()
        
    def setup_logging(self):
        # Setup logging to a file
        log_dir = os.path.join(os.path.expanduser("~"), "FaceOrganizer")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "face_organizer.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
    def setup_tray(self):
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(QIcon("assets/icon.png"))  # Make sure to add an icon file
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show UI action
        show_action = QAction("Show Face Organizer", self.app)
        show_action.triggered.connect(self.show_ui_signal.emit)
        tray_menu.addAction(show_action)
        
        # Start/Stop monitoring action
        self.monitor_action = QAction("Stop Monitoring", self.app)
        self.monitor_action.triggered.connect(self.toggle_monitoring)
        tray_menu.addAction(self.monitor_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self.app)
        exit_action.triggered.connect(self.app.quit)
        tray_menu.addAction(exit_action)
        
        # Set the tray icon's menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()
        
    def toggle_monitoring(self):
        self.stop_monitoring_signal.emit()
        if self.monitor_action.text() == "Stop Monitoring":
            self.monitor_action.setText("Start Monitoring")
        else:
            self.monitor_action.setText("Stop Monitoring")
            
    def set_monitoring_status(self, is_monitoring: bool):
        self.monitor_action.setText("Stop Monitoring" if is_monitoring else "Start Monitoring")
        
    def show_notification(self, title: str, message: str):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
        
    @staticmethod
    def set_autostart(enable: bool):
        """Enable or disable autostart with Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            if enable:
                # Get the path to the executable
                if getattr(sys, 'frozen', False):
                    # Running as compiled exe
                    app_path = sys.executable
                else:
                    # Running as script
                    app_path = os.path.abspath(sys.argv[0])
                
                winreg.SetValueEx(key, "FaceOrganizer", 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, "FaceOrganizer")
                except WindowsError:
                    pass
                    
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logging.error(f"Failed to set autostart: {str(e)}")
            return False 