"""Run a request operation in the background and deliver its result to the UI."""

from collections.abc import Callable

from PyQt6 import QtCore


class RequestWorker(QtCore.QThread):
    result_ready = QtCore.pyqtSignal(object)
    
    def __init__(self, operation: Callable, parent = None):
        super( ).__init__(parent)
        self.operation = operation
    
    def run(self):
        try:
            result = self.operation( )
        except Exception as exc:
            result = exc
        self.result_ready.emit(result)
