import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from theme_manager import ThemeManager
from gui.main_window import MainWindow
from app_controller import AppController
from utils import resource_path  # <-- IMPORT THE HELPER

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    try:
        # MODIFIED: Use resource_path to find the bundled config files.
        config_file = resource_path('config.json')
        theme_file = resource_path('themes/light.json')
        
        theme_manager = ThemeManager(config_file, theme_file)
        
        controller = AppController(theme_manager)

        app.setStyleSheet(theme_manager.generate_stylesheet())
        
        window = MainWindow(theme_manager, controller)
        window.show()
        
        sys.exit(app.exec())
        
    except IOError as e:
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setText("Application Critical Error")
        error_box.setInformativeText(f"Could not initialize the application.\n\nDetails: {e}")
        error_box.setWindowTitle("Fatal Error")
        error_box.exec()
        sys.exit(1)