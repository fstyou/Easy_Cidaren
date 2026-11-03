"""Offscreen GUI smoke test, run on machines with working PyQt6."""
import logging
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QFileDialog, QLabel, QMessageBox, QPushButton, QRadioButton, \
    QAbstractItemView, QWidget

ROOT = Path(__file__).resolve( ).parents[1]
sys.path.insert(0, str(ROOT))
from easy_cidaren.app import main as application_entry
from easy_cidaren.ui.main_window import UiMainWindow
from easy_cidaren.ui.token_dialog import CaptureProgressDialog
from easy_cidaren.ui.dialogs import confirm_action, create_message, select_file
from easy_cidaren.ui.settings import SettingsWindow
from easy_cidaren.ui.about import AboutDialog
from easy_cidaren.token_capture.service import CaptureStatus, TokenCaptureService
from easy_cidaren.ui.theme import ThemeManager

app = QApplication([])
app._theme_manager = ThemeManager(app, 'light')
assert callable(application_entry)
message = create_message(None, '提示', '测试内容', QMessageBox.Icon.Information)
assert message.button(QMessageBox.StandardButton.Ok).text( ) == '知道了'
assert message.escapeButton( ) == message.button(QMessageBox.StandardButton.Ok)

dark_parent = QWidget( )
dark_palette = QPalette(dark_parent.palette( ))
dark_palette.setColor(QPalette.ColorRole.Window, QColor('#202020'))
dark_palette.setColor(QPalette.ColorRole.WindowText, QColor('#ffffff'))
dark_palette.setColor(QPalette.ColorRole.Base, QColor('#202020'))
dark_palette.setColor(QPalette.ColorRole.Text, QColor('#ffffff'))
dark_parent.setPalette(dark_palette)
for icon in (QMessageBox.Icon.Information, QMessageBox.Icon.Warning, QMessageBox.Icon.Critical):
    dark_message = create_message(dark_parent, '提示', '测试内容', icon)
    assert dark_message.palette( ).color(QPalette.ColorRole.Window).name( ) == '#f4f6f9'
    assert dark_message.palette( ).color(QPalette.ColorRole.WindowText).name( ) == '#263548'

def reject_confirmation(dialog):
    assert dialog.palette( ).color(QPalette.ColorRole.Window).name( ) == '#f4f6f9'
    assert dialog.button(QMessageBox.StandardButton.Yes).text( ) == '中止任务'
    assert dialog.button(QMessageBox.StandardButton.No).text( ) == '取消'
    assert dialog.defaultButton( ) == dialog.button(QMessageBox.StandardButton.No)
    assert dialog.escapeButton( ) == dialog.button(QMessageBox.StandardButton.No)
    return QMessageBox.StandardButton.No

with patch.object(QMessageBox, 'exec', new = reject_confirmation):
    assert not confirm_action(None, '确认停止', '确定中止吗？', confirm_text = '中止任务')

original_message_exec = QMessageBox.exec
def close_confirmation(dialog):
    QTimer.singleShot(0, dialog.close)
    return original_message_exec(dialog)

with patch.object(QMessageBox, 'exec', new = close_confirmation):
    assert not confirm_action(None, '确认开始', '确定开始吗？', confirm_text = '开始', default_confirm = True)

def cancel_file_dialog(dialog):
    assert dialog.palette( ).color(QPalette.ColorRole.Base).lightness( ) > 200
    assert dialog.palette( ).color(QPalette.ColorRole.Text).name( ) == '#263548'
    assert dialog.labelText(QFileDialog.DialogLabel.Accept) == (
        '保存' if dialog.acceptMode( ) == QFileDialog.AcceptMode.AcceptSave else '打开')
    assert dialog.labelText(QFileDialog.DialogLabel.Reject) == '取消'
    return QFileDialog.DialogCode.Rejected

with patch.object(QFileDialog, 'exec', new = cancel_file_dialog):
    assert select_file(dark_parent, '导出日志', '', '日志文件 (*.log)', save = True) == ''
    assert select_file(dark_parent, '选择音频', '', '音频文件 (*.wav)') == ''

app._theme_manager.set_mode('dark')
assert app._theme_manager.dark
dark_message = create_message(dark_parent, '提示', '深色测试', QMessageBox.Icon.Warning)
dark_message.show( )
app.processEvents( )
assert dark_message.palette( ).color(QPalette.ColorRole.Window).lightness( ) < 100
assert dark_message.palette( ).color(QPalette.ColorRole.WindowText).lightness( ) > 180
dark_message.close( )
def check_dark_file_dialog(dialog):
    dialog.show( )
    app.processEvents( )
    assert dialog.palette( ).color(QPalette.ColorRole.Window).lightness( ) < 100
    assert dialog.palette( ).color(QPalette.ColorRole.Text).lightness( ) > 180
    dialog.close( )
    return QFileDialog.DialogCode.Rejected

with patch.object(QFileDialog, 'exec', new = check_dark_file_dialog):
    assert select_file(dark_parent, '打开', '', '所有文件 (*)') == ''
app._theme_manager.set_mode('system')
scheme = app.styleHints( ).colorScheme( )
if scheme != Qt.ColorScheme.Unknown:
    assert app._theme_manager.dark == (scheme == Qt.ColorScheme.Dark)
app._theme_manager.set_mode('light')
assert not app._theme_manager.dark

with patch('easy_cidaren.ui.main_window.load_token', return_value = 'remembered-token'):
    remembered = UiMainWindow(SimpleNamespace(version = 'test'), logging.getLogger('gui-test'), None)
assert remembered.ui.token_input.text( ) == 'remembered-token'
assert '上次' in remembered.ui.login_hint.text( )
assert remembered.login_worker is None
remembered.close( )
with patch('easy_cidaren.ui.main_window.load_token', return_value = ''):
    window = UiMainWindow(SimpleNamespace(version = 'test'), logging.getLogger('gui-test'), None)
window.show( )
app.processEvents( )
assert window.width( ) <= min(1000, window.screen( ).availableGeometry( ).width( ))
assert window.width( ) <= window.maximumWidth( )
assert window.maximumHeight( ) <= 380
window.resize(5000, 5000)
assert window.width( ) <= window.maximumWidth( )
assert window.height( ) <= window.maximumHeight( )
assert window.ui.capture_button.text( ) == '获取 Token'
assert window.ui.help_button.text( ) == '查看帮助'
assert window.ui.about_button.text( ) == '关于'
assert window.menuWidget( ) is None
assert window.ui.settings_button.text( ) == '设置'
settings_state = SimpleNamespace(min_time = 1, max_time = 3, spend_min_time = 2, spend_max_time = 10,
                                 br_choices = True, play_music = False, music_path = '')
settings_state.input_info = lambda *args: saved_settings.append(args)
saved_settings = []
with patch.object(window, 'public_info', settings_state):
    window.ui.settings_button.click( )
    assert isinstance(window.settings, SettingsWindow)
    assert window.settings.isVisible( )
    window.settings.min_time.setValue(5)
    with patch('easy_cidaren.ui.settings.show_warning') as warning:
        window.settings.save( )
        warning.assert_called_once( )
        assert not saved_settings
    window.settings.min_time.setValue(1)
    window.settings.theme_choice.setCurrentIndex(window.settings.theme_choice.findData('dark'))
    window.settings.save( )
    assert saved_settings[0][:4] == (1, 3, 2, 10)
    assert saved_settings[0][-1] == 'dark'
    assert app._theme_manager.dark
    assert not window.settings.isVisible( )
app._theme_manager.set_mode('light')
print('界面测试：设置完成', flush = True)
with patch('easy_cidaren.ui.log_export.export_logs') as export_logs:
    window.ui.export_logs_button.click( )
    export_logs.assert_called_once_with(window)
print('界面测试：日志导出入口完成', flush = True)
with patch('easy_cidaren.ui.main_window.QtGui.QDesktopServices.openUrl', return_value = True) as open_url:
    window.ui.help_button.click( )
    assert open_url.call_args.args[0].toString( ) == 'https://github.com/fstyou/Easy_Cidaren#readme'
print('界面测试：帮助入口完成', flush = True)
def inspect_about(dialog):
    dialog.show( )
    app.processEvents( )
    buttons = {button.text( ): button for button in dialog.findChildren(QPushButton)}
    assert '确定' in buttons
    assert '复制信息' not in buttons
    assert '项目首页' not in buttons
    labels = [label.text( ) for label in dialog.findChildren(QLabel)]
    assert 'GNU GPL v3' in labels
    assert dialog.minimumWidth( ) == dialog.maximumWidth( )
    assert dialog.minimumWidth( ) >= 400
    assert dialog.minimumHeight( ) == dialog.maximumHeight( )
    project_link = dialog.findChild(QLabel, 'projectLink')
    assert 'https://github.com/fstyou/Easy_Cidaren' in project_link.text( )
    assert project_link.fontMetrics( ).horizontalAdvance(
            'https://github.com/fstyou/Easy_Cidaren') <= project_link.contentsRect( ).width( )
    assert project_link.alignment( ) & Qt.AlignmentFlag.AlignLeft
    with patch('easy_cidaren.ui.about.QtGui.QDesktopServices.openUrl', return_value = True) as open_url:
        project_link.linkActivated.emit('https://github.com/fstyou/Easy_Cidaren')
        assert open_url.call_args.args[0].toString( ) == 'https://github.com/fstyou/Easy_Cidaren'
    dialog.close( )
    return 0

about_errors = []
def inspect_about_safely(dialog):
    try:
        return inspect_about(dialog)
    except Exception as exc:
        about_errors.append(exc)
        return 0

with patch.object(AboutDialog, 'exec', new = inspect_about_safely):
    window.ui.about_button.click( )
if about_errors:
    raise about_errors[0]
print('界面测试：关于窗口内容完成', flush = True)
original_about_exec = AboutDialog.exec
def close_about(dialog):
    QTimer.singleShot(0, dialog.close)
    result = original_about_exec(dialog)
    assert not dialog.isVisible( )
    return result

with patch.object(AboutDialog, 'exec', new = close_about):
    window.ui.about_button.click( )
assert not window.ui.stop_task.isEnabled( )
assert not window.ui.task_card.isVisible( )
assert not window.ui.user_info.isVisible( )
assert not window.ui.progress_card.isVisible( )
assert window.ui.login_hint.isVisible( )
assert '获取 Token 并登录' in window.ui.login_hint.text( )
window.resize(820, 700)
app.processEvents( )
assert window.ui.account_card.height( ) <= window.ui.account_card.sizeHint( ).height( ) + 2
with patch('easy_cidaren.ui.main_window.show_warning'):
    window.on_login_result(1)
assert not window.ui.task_card.isVisible( )
with patch.object(window, 'get_task_list'):
    window.on_login_result({'data': {'user_info': {
        'student_name': '测试用户', 'student_code': '20260001',
        'school_name': '用于验证长学校名称自动换行的测试大学', 'class_name': None,
    }}})
app.processEvents( )
assert window.ui.task_card.isVisible( )
assert window.ui.user_info.isVisible( )
if window.minimumHeight( ) < window.maximumHeight( ):
    assert window.ui.scroll_area.verticalScrollBar( ).maximum( ) == 0
assert window.maximumHeight( ) <= 800
assert window.minimumHeight( ) <= window.maximumHeight( )
assert not window.ui.login_hint.isVisible( )
assert window.ui.label.text( ) == '账号信息'
assert window.ui.user_info.values['student_name'].text( ) == '测试用户'
assert window.ui.user_info.values['student_code'].text( ) == '20260001'
assert window.ui.user_info.values['class_name'].text( ) == '—'
assert window.ui.user_info.values['school_name'].wordWrap( )
assert window.ui.user_info.window( ) is window
window.ui.user_info.set_user({'student_name': '<测试姓名>'})
assert window.ui.user_info.values['student_name'].textFormat( ) == Qt.TextFormat.PlainText
assert window.ui.user_info.values['student_name'].text( ) == '<测试姓名>'
assert window.ui.user_info.values['student_code'].text( ) == '—'
assert not window.ui.progress_card.isVisible( )
assert not window.ui.stop_task.isVisible( )
unopened = {'task_name': '未开始的任务', 'over_status': 1, 'progress': 0,
            'start_time': 1793604627860, 'over_time': 115172140}
available = {'task_name': '已开放的任务', 'over_status': 2, 'progress': 0}
completed = {'task_name': '已完成的任务', 'over_status': 2, 'progress': 100}
def fake_load_tasks(info):
    info.task_list = [unopened, available, completed]
    return info.task_list

# The event loop must remain responsive while a list request is pending.
release_request = threading.Event( )
def delayed_load_tasks(info):
    if not release_request.wait(2):
        raise TimeoutError('test request was not released')
    return fake_load_tasks(info)

with patch('easy_cidaren.ui.main_window.load_class_tasks', delayed_load_tasks):
    window.get_task_list( )
    pending_worker = window.task_list_worker
    window.get_task_list( )
    assert window.task_list_worker is pending_worker
    assert not window.ui.login.isEnabled( )
    ticks = []
    QTimer.singleShot(0, lambda: ticks.append(True))
    app.processEvents( )
    assert ticks
    release_request.set( )
    pending_worker.wait( )
    app.processEvents( )

with patch('easy_cidaren.ui.main_window.load_class_tasks', side_effect = OSError('offline')), \
        patch('easy_cidaren.ui.main_window.show_warning') as warning:
    window.get_task_list( )
    window.task_list_worker.wait( )
    app.processEvents( )
    warning.assert_called_once( )
assert window.public_info.task_list == []
assert window.ui.task_list.rowCount( ) == 0
assert window.ui.login.isEnabled( )

with patch('easy_cidaren.ui.main_window.load_class_tasks', fake_load_tasks):
    window.get_task_list( )
    window.task_list_worker.wait( )
    app.processEvents( )
    app.processEvents( )
unavailable_radio = window.ui.task_list.cellWidget(0, 0).findChild(QRadioButton)
available_radio = window.ui.task_list.cellWidget(1, 0).findChild(QRadioButton)
completed_radio = window.ui.task_list.cellWidget(2, 0).findChild(QRadioButton)
assert not unavailable_radio.isEnabled( )
assert available_radio.isEnabled( )
assert not completed_radio.isEnabled( )
completed_radio.click( )
assert not completed_radio.isChecked( )
assert not (window.ui.task_list.item(2, 1).flags( ) & Qt.ItemFlag.ItemIsSelectable)
assert '已完成' in window.ui.task_list.item(2, 1).toolTip( )
for column in range(1, 6):
    assert window.ui.task_list.item(2, column).foreground( ).color( ).name( ) == '#196b4b'
assert unavailable_radio.geometry( ).center( ).x( ) == available_radio.geometry( ).center( ).x( )
unavailable_radio.click( )
assert not unavailable_radio.isChecked( )
window.ui.task_list.setRowCount(30)
window.set_ui_enabled(False)
app.processEvents( )
assert window.ui.task_list.isEnabled( )
assert window.ui.task_list.selectionMode( ) == QAbstractItemView.SelectionMode.NoSelection
assert not available_radio.isEnabled( )
scrollbar = window.ui.task_list.verticalScrollBar( )
assert scrollbar.maximum( ) > 0
scrollbar.setValue(scrollbar.maximum( ))
assert scrollbar.value( ) == scrollbar.maximum( )
window.set_ui_enabled(True)
assert available_radio.isEnabled( )
assert not unavailable_radio.isEnabled( )
assert not completed_radio.isEnabled( )
assert window.ui.task_list.selectionMode( ) == QAbstractItemView.SelectionMode.SingleSelection
window.ui.task_list.setRowCount(3)
assert not (window.ui.task_list.item(0, 1).flags( ) & Qt.ItemFlag.ItemIsSelectable)
assert window.ui.task_list.item(0, 2).text( ) != '—'
assert window.ui.task_list.item(0, 3).text( ) != '—'
assert not (window.ui.task_list.item(0, 3).flags( ) & Qt.ItemFlag.ItemIsSelectable)
assert window.ui.task_list.item(1, 2).text( ) == '—'
assert '尚未开始' in window.ui.task_list.item(0, 1).toolTip( )
assert window.ui.task_list.item(1, 1).flags( ) & Qt.ItemFlag.ItemIsSelectable

class FakeSignal:
    def __init__(self):
        self.connections = []
    
    def connect(self, callback):
        self.connections.append(callback)

class FakeWorker:
    def __init__(self, state, tasks, batch_mode = False):
        self.state, self.tasks, self.batch_mode = state, tasks, batch_mode
        for name in ('finished', 'task_finished', 'task_error', 'task_progress', 'task_notice', 'batch_finished'):
            setattr(self, name, FakeSignal( ))
        self.started = False
    
    def setParent(self, parent):
        self.parent = parent
    
    def deleteLater(self):
        pass
    
    def start(self):
        self.started = True

window.task_worker_class = FakeWorker
with patch.object(window, 'show_task_progress'):
    window._start_worker([available], batch_mode = False)
    assert window.task_worker.state is window.public_info
    assert window.task_worker.started and not window.task_worker.batch_mode
    assert not window.task_worker.batch_finished.connections
    window._start_worker([available], batch_mode = True)
    assert window.task_worker.started and window.task_worker.batch_mode
    assert len(window.task_worker.batch_finished.connections) == 1
window.task_worker = None
window.set_ui_enabled(True)
window.set_logged_in(False)
with patch('easy_cidaren.ui.main_window.show_warning'):
    window.on_login_result(1)
assert not window.ui.task_card.isVisible( )
assert not window.ui.user_info.isVisible( )
assert window.ui.login_hint.isVisible( )
window.set_logged_in(True)
window.show_task_progress('测试任务')
assert window.maximumHeight( ) <= 900
assert window.minimumHeight( ) <= window.maximumHeight( )
previous_height = window.height( )
app.processEvents( )
assert window.height( ) >= previous_height
assert window.height( ) <= window.screen( ).availableGeometry( ).height( )
window.resize(window.width( ), window.maximumHeight( ))
app.processEvents( )
large_table_height = window.ui.task_list.height( )
large_progress_height = window.ui.progress_card.height( )
window.resize(window.width( ), window.minimumHeight( ))
app.processEvents( )
app.processEvents( )
if window.maximumHeight( ) - window.minimumHeight( ) >= 80:
    assert window.ui.task_list.height( ) < large_table_height
    assert window.ui.progress_card.height( ) == large_progress_height
    assert window.ui.scroll_area.verticalScrollBar( ).maximum( ) == 0
window.resize(820, 300)
app.processEvents( )
app.processEvents( )
assert window.ui.progress_card.isVisible( )
assert window.ui.progress_card.y( ) >= window.ui.task_card.y( ) + window.ui.task_card.height( )
assert window.ui.start_task.y( ) >= window.ui.task_list.y( ) + window.ui.task_list.height( )
if window.minimumHeight( ) < window.maximumHeight( ):
    assert window.ui.scroll_area.verticalScrollBar( ).maximum( ) == 0
assert window.ui.stop_task.isVisible( )
assert window.ui.progress_bar.maximum( ) == 0
window.update_progress('3/10|2|0|1|1/1|测试任务')
assert window.ui.progress_bar.maximum( ) == 10
assert window.ui.progress_bar.value( ) == 3
assert window.ui.progress_skip_label.text( ) == '跳过 1'
window.play_music = lambda: None
window.get_task_list = lambda: None
window._batch_mode = False
with patch('easy_cidaren.ui.main_window.show_information'):
    window.on_task_finished('任务已完成')
assert not window.ui.progress_card.isVisible( )
assert not window.ui.stop_task.isVisible( )
assert window.maximumHeight( ) <= 800
window.show_task_progress('测试任务')
with patch('easy_cidaren.ui.main_window.show_error') as critical:
    window.on_task_error('无法跳过题目')
    assert '无法跳过题目' in critical.call_args.args
assert not window.ui.progress_card.isVisible( )

calls = []
window.token_login = lambda: calls.append(window.ui.token_input.text( ))
window.on_builtin_token_captured('captured-test-token')
assert not calls
window.on_capture_finished( )
assert calls == ['captured-test-token']

window.show_notice('⚠ <题目错误>')
window.show_notice('⚠ 已跳过')
assert '<题目错误>' in window._notice_dialog.text( )
assert '已跳过' in window._notice_dialog.text( )
assert not window._notice_dialog.isModal( )
assert window._notice_dialog.button(QMessageBox.StandardButton.Ok).text( ) == '知道了'
assert window._notice_dialog.escapeButton( ) == window._notice_dialog.button(QMessageBox.StandardButton.Ok)
window._notice_dialog.close( )

dialog = CaptureProgressDialog(window)
dialog.open( )
app.processEvents( )
assert dialog.isVisible( )
assert any('微信' in label.text( ) for label in dialog.findChildren(type(dialog.status_label)))
dialog.show_status(CaptureStatus.MANUAL_PROXY, '代理设置说明：127.0.0.1:8888')
with tempfile.TemporaryDirectory( ) as directory:
    cert = Path(directory) / '.mitmproxy' / 'mitmproxy-ca-cert.cer'
    cert.parent.mkdir( )
    cert.touch( )
    service = TokenCaptureService(directory)
    with patch('easy_cidaren.token_capture.service.Path.home', return_value = Path(directory)), \
            patch('easy_cidaren.token_capture.service.sys.platform', 'darwin'):
        service._ensure_mitm_cert_ready(dialog.show_status)
    cert_path = str(cert)
app.processEvents( )
assert dialog.height( ) < 600
assert dialog.maximumHeight( ) == dialog.height( )
assert dialog.subtitle_label.y( ) <= dialog.title_label.y( ) + dialog.title_label.height( ) + 20
assert dialog.instructions.y( ) <= dialog.subtitle_label.y( ) + dialog.subtitle_label.height( ) + 20
steps = dialog.instructions.text( )
assert '127.0.0.1:8888' in steps
assert cert_path in steps
assert steps.index('127.0.0.1:8888') < steps.index(cert_path) < steps.index('公众号')
assert not hasattr(dialog, 'details')
dialog.show_status(CaptureStatus.WAITING, '任意等待提示')
assert '等待获取' in dialog.status_label.text( )
window._capture_warnings = []
window.on_capture_status(CaptureStatus.RESTORE_PROXY, '自定义恢复提示')
window.on_capture_status(CaptureStatus.WARNING, '自定义错误提示')
assert window._capture_warnings == ['自定义恢复提示', '自定义错误提示']
window._capture_warnings = []
dialog.captured( )
dialog.finish(success = True)
assert not dialog.isVisible( )

cancelled = []
dialog = CaptureProgressDialog(window)
dialog.cancel_requested.connect(lambda: cancelled.append(True))
dialog.open( )
dialog.reject( )
assert cancelled == [True]
assert dialog.isVisible( )
dialog.finish( )
assert not dialog.isVisible( )
window.close( )
print('GUI smoke test passed')
