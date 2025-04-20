# src/main.py
import sys
from PyQt5.QtWidgets import QApplication
from ui.layout import SensorDashboard

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SensorDashboard()
    window.show()
    sys.exit(app.exec_())
