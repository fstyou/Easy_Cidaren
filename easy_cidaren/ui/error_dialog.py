"""Startup error dialog."""

from PyQt6 import QtCore, QtGui, QtWidgets

from easy_cidaren.paths import LOG_DIR
from easy_cidaren.ui.dialogs import show_warning


class ErrorDialog(QtWidgets.QDialog):
    def __init__(self):
        super( ).__init__( )
        self.setWindowTitle('程序启动失败')
        self.setMinimumWidth(380)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)
        message = QtWidgets.QLabel('程序遇到错误，无法继续运行。请查看日志了解详情。')
        message.setWordWrap(True)
        layout.addWidget(message)
        buttons = QtWidgets.QHBoxLayout( )
        buttons.addStretch( )
        open_logs = QtWidgets.QPushButton('打开日志文件夹')
        open_logs.clicked.connect(self.open_logs_folder)
        close = QtWidgets.QPushButton('关闭')
        close.clicked.connect(self.accept)
        buttons.addWidget(open_logs)
        buttons.addWidget(close)
        layout.addLayout(buttons)
    
    def open_logs_folder(self):
        try:
            LOG_DIR.mkdir(parents = True, exist_ok = True)
            if QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(LOG_DIR))):
                return
        except OSError as exc:
            show_warning(self, '无法打开日志', str(exc))
            return
        show_warning(self, '无法打开日志', '请检查系统的文件管理器设置')
