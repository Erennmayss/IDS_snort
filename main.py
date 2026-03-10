from GUI.configuration import InterfaceParametresIDS
from PyQt6.QtWidgets import QApplication

app = QApplication([])
window = InterfaceParametresIDS()
window.show()

app.exec()