"""Compact, labelled account information displayed after login."""

from collections.abc import Mapping

from PyQt6 import QtCore, QtWidgets


class UserInfoWidget(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super( ).__init__(parent)
        self.setObjectName('userInfo')
        self.setStyleSheet('''
            QLabel#userField { color: #607086; font-size: 12px; }
            QLabel#userValue { color: #344b66; font-size: 13px; }
            QLabel#userName { color: #20344f; font-size: 14px; font-weight: 600; }
        ''')
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)
        layout.setColumnMinimumWidth(2, 24)
        layout.setColumnStretch(4, 1)
        self.values: dict[str, QtWidgets.QLabel] = {}
        fields = (('student_name', '姓名'), ('student_code', '学号'),
                  ('school_name', '学校'), ('class_name', '班级'))
        for index, (key, title) in enumerate(fields):
            row, group = divmod(index, 2)
            column = group * 3
            heading = QtWidgets.QLabel(title)
            heading.setObjectName('userField')
            value = QtWidgets.QLabel('—')
            value.setObjectName('userName' if key == 'student_name' else 'userValue')
            value.setAccessibleName(title)
            value.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            value.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
            value.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
            layout.addWidget(heading, row, column, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
            layout.addWidget(value, row, column + 1)
            self.values[key] = value
    
    def set_user(self, user: Mapping):
        if not isinstance(user, Mapping):
            raise ValueError('用户信息格式无效')
        for key, label in self.values.items( ):
            value = user.get(key)
            text = str(value).strip( ) if isinstance(value, (str, int)) and not isinstance(value, bool) else ''
            label.setText(text or '—')
    
    def clear(self):
        self.set_user({})
