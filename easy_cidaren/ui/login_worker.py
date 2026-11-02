"""Run login requests without blocking the interface."""

from PyQt6 import QtCore

from easy_cidaren.api.login import verify_token


class LoginWorker(QtCore.QThread):
    result_ready = QtCore.pyqtSignal(object)
    
    def __init__(self, token, parent = None):
        super( ).__init__(parent)
        self.token = token
    
    def run(self):
        try:
            self.result_ready.emit(verify_token(self.token))
        except Exception as exc:
            self.result_ready.emit(exc)
