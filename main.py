import sys
import os
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.system_tray import SystemTrayService
import logging

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Don't quit when window is closed
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create system tray service
    tray_service = SystemTrayService(app)
    
    # Create main window (but don't show it yet)
    window = MainWindow()
    
    # Connect tray signals
    tray_service.show_ui_signal.connect(window.show)
    tray_service.stop_monitoring_signal.connect(window.toggle_monitoring)
    
    # Connect window signals
    window.monitoring_started.connect(lambda: tray_service.set_monitoring_status(True))
    window.monitoring_stopped.connect(lambda: tray_service.set_monitoring_status(False))
    window.photo_processed.connect(lambda path: tray_service.show_notification(
        "New Photo Processed",
        f"Processed: {os.path.basename(path)}"
    ))
    
    # Show window if started with --show flag
    if "--show" in sys.argv:
        window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 