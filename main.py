# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication, QDialog
from ritt.ui.main_window import TachographWindow
from ritt.ui.login_dialog import LoginDialog
from ritt.ui.theme import apply_theme

def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    dlg = LoginDialog()
    if dlg.exec() != QDialog.Accepted:   # <- poprawka
        sys.exit(0)

    username = dlg.username
    display_name = dlg.display_name

    win = TachographWindow(lang="pl")
    if username:
        win.set_logged_user(login=username, name=display_name)

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
