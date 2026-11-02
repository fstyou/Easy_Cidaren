"""Shared styling for application dialogs."""

DIALOG_STYLE = '''
    QDialog { background: #f4f6f9; color: #263548; }
    QLabel, QCheckBox { color: #263548; font-size: 13px; }
    QLabel#title { color: #20344f; font-size: 20px; font-weight: 600; }
    QFrame#card { background: white; border: 1px solid #dce3ec; border-radius: 8px; }
    QFrame#card QLabel { border: none; background: transparent; }
    QLabel#muted { color: #52657c; }
    QPushButton { background: #edf2f7; color: #29415f; border: 1px solid #d4deea;
                  border-radius: 6px; padding: 7px 14px; font-size: 13px; }
    QPushButton:hover { background: #e1eaf5; }
    QPushButton#primaryButton { background: #3269bd; border-color: #3269bd; color: white; }
    QPushButton#primaryButton:hover { background: #285aa4; }
'''
