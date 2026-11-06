import html

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from easy_cidaren.app_logging.config import get_logger
from easy_cidaren.token_capture.service import CaptureStatus, TokenCaptureService

dialog_logger = get_logger("builtin_token")


class TokenCaptureWorker(QThread):
    """工作线程：负责在后台调用 Token 捕获服务"""
    token_captured = pyqtSignal(str)  # 捕获到 token 的信号
    status_update = pyqtSignal(object, str)  # 状态类型与展示文案
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, capture_directory):
        super( ).__init__( )
        self.service = TokenCaptureService(capture_directory)
    
    def run(self):
        """在线程中执行 token 捕获"""
        try:
            self.service.start_capture(
                    status_callback = self.status_update.emit,
                    token_callback = self.token_captured.emit,
                    error_callback = self.error_occurred.emit,
            )
        
        except Exception as e:
            dialog_logger.error(f"捕获线程发生异常: {e}", exc_info = True)
            self.error_occurred.emit(f"发生错误: {str(e)}")
    
    def stop(self):
        """停止工作线程"""
        self.service.stop( )


class CaptureProgressDialog(QDialog):
    """Show capture instructions while the main window owns the worker."""
    
    cancel_requested = pyqtSignal( )
    
    def __init__(self, parent = None):
        super( ).__init__(parent)
        self._running = True
        self._cancel_requested = False
        self._setup_steps = {}
        self.setWindowTitle("获取 Token")
        self.setObjectName("tokenCaptureDialog")
        screen = parent.screen( ) if parent else QtWidgets.QApplication.primaryScreen( )
        available_width = screen.availableGeometry( ).width( ) if screen else 552
        self.setFixedWidth(max(300, min(520, available_width - 32)))
        self.setModal(True)
        self.setStyleSheet("""
            QDialog#tokenCaptureDialog { background: #ffffff; color: #263548; }
            QLabel#captureTitle { color: #20344f; font-size: 18px; font-weight: 600; }
            QLabel#captureSubtitle { color: #52657c; font-size: 13px; }
            QLabel#captureSteps { color: #30445e; font-size: 13px; }
            QFrame#captureStatus { background: #f3f7fd; border: 1px solid #e1eaf6; border-radius: 8px; }
            QLabel#captureStatusText { color: #315780; font-size: 13px; font-weight: 600; }
            QProgressBar#captureProgress { background: #dce7f5; border: none; border-radius: 3px; height: 6px; }
            QProgressBar#captureProgress::chunk { background: #3978d9; border-radius: 3px; }
            QPushButton#captureCancel { background: #edf2f8; color: #263d5b; border: 1px solid #dce4ee; border-radius: 6px; padding: 7px 16px; }
            QPushButton#captureCancel:hover { background: #e1ebf8; }
            QPushButton#captureCancel:disabled { color: #9cabbc; }
        """)
        self.content_layout = layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.title_label = QLabel("获取登录 Token")
        self.title_label.setObjectName("captureTitle")
        layout.addWidget(self.title_label)
        self.subtitle_label = QLabel("按以下步骤操作，获取成功后将自动登录")
        self.subtitle_label.setObjectName("captureSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)
        self.instructions = QLabel( )
        self.instructions.setObjectName("captureSteps")
        self.instructions.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.instructions.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)
        self._render_steps( )
        
        self.status_frame = QtWidgets.QFrame( )
        self.status_frame.setObjectName("captureStatus")
        self.status_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                        QtWidgets.QSizePolicy.Policy.Fixed)
        self.status_layout = status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(8)
        self.status_label = QLabel("正在准备，请稍候…")
        self.status_label.setObjectName("captureStatusText")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        status_layout.addWidget(self.status_label)
        self.progress = QtWidgets.QProgressBar( )
        self.progress.setObjectName("captureProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        status_layout.addWidget(self.progress)
        layout.addWidget(self.status_frame)
        self.buttons = QHBoxLayout( )
        self.buttons.addStretch( )
        self.cancel_button = QPushButton("取消获取")
        self.cancel_button.setObjectName("captureCancel")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons.addWidget(self.cancel_button)
        layout.addLayout(self.buttons)
    
    def showEvent(self, a0):
        super( ).showEvent(a0)
        QtCore.QTimer.singleShot(0, self._fit_content)
    
    def _fit_content(self):
        """Size the dialog to its wrapped text instead of expanding to screen height."""
        if not self.isVisible( ):
            return
        margins = self.content_layout.contentsMargins( )
        width = self.width( ) - margins.left( ) - margins.right( )
        
        def label_height(label):
            preferred_height = label.heightForWidth(width) if label.hasHeightForWidth( ) else -1
            return max(label.minimumSizeHint( ).height( ),
                       preferred_height if preferred_height > 0 else label.sizeHint( ).height( ))
        
        self.status_layout.activate( )
        status_height = self.status_layout.totalHeightForWidth(width)
        if status_height < 0:
            status_height = self.status_frame.sizeHint( ).height( )
        height = (margins.top( ) + margins.bottom( ) + self.content_layout.spacing( ) * 4
                  + label_height(self.title_label) + label_height(self.subtitle_label)
                  + label_height(self.instructions) + status_height + self.buttons.sizeHint( ).height( ))
        self.setFixedHeight(height)
    
    def _render_steps(self):
        steps = ["打开电脑微信并登录"]
        steps.extend(self._setup_steps[key] for key in sorted(self._setup_steps))
        steps.extend([
            "在微信中进入“词达人”公众号的学生端，或在任意聊天发送并打开 https://app.vocabgo.com/student/",
            "在学生端浏览几个页面，等待自动获取",
        ])
        self.instructions.setText('<ol>' + ''.join(
                f'<li style="margin-bottom: 8px;">{html.escape(step)}</li>' for step in steps
        ) + '</ol>')
    
    def show_status(self, status, message):
        if status is CaptureStatus.WAITING:
            self.status_label.setText("等待获取 Token…")
        elif status is CaptureStatus.MANUAL_PROXY:
            self._setup_steps[0] = message
            self._render_steps( )
            QtCore.QTimer.singleShot(0, self._fit_content)
        elif status is CaptureStatus.CERT_TRUST:
            self._setup_steps[1] = message
            self._render_steps( )
            QtCore.QTimer.singleShot(0, self._fit_content)
        elif status in (CaptureStatus.WARNING, CaptureStatus.RESTORE_PROXY):
            self.status_label.setText(message)
    
    def captured(self):
        self.status_label.setText("已获取 Token，正在恢复代理设置…")
        self._cancel_requested = True
        self.cancel_button.setEnabled(False)
    
    def failed(self, message):
        self.status_label.setStyleSheet("color: #a73630;")
        self.status_label.setText(f"获取失败：{message}")
        QtCore.QTimer.singleShot(0, self._fit_content)
    
    def finish(self, *, success = False, error = False):
        self._running = False
        self.progress.hide( )
        if success or not error:
            self.accept( )
        else:
            self.cancel_button.setText("关闭")
            self.cancel_button.setEnabled(True)
    
    def reject(self):
        if not self._running:
            super( ).reject( )
        elif not self._cancel_requested:
            self._cancel_requested = True
            self.cancel_button.setEnabled(False)
            self.status_label.setText("正在停止获取并清理代理…")
            self.cancel_requested.emit( )
    
    def closeEvent(self, a0):
        if a0 is None:
            return
        if self._running:
            self.reject( )
            a0.ignore( )
        else:
            a0.accept( )
