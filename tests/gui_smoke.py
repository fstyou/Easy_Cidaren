"""Offscreen GUI smoke test, run on machines with working PyQt6."""
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QFileDialog, QLabel, QMessageBox, QPushButton, QRadioButton, QAbstractItemView

ROOT = Path(__file__).resolve( ).parents[1]
sys.path.insert(0, str(ROOT))
from easy_cidaren.ui.main_window import UiMainWindow
from easy_cidaren.ui.token_dialog import CaptureProgressDialog
from easy_cidaren.ui.dialogs import confirm_action, create_message, select_file
from easy_cidaren.ui.settings import SettingsWindow
from easy_cidaren.ui.about import AboutDialog

app = QApplication([])
message = create_message(None, '提示', '测试内容', QMessageBox.Icon.Information)
assert message.button(QMessageBox.StandardButton.Ok).text( ) == '知道了'
assert message.escapeButton( ) == message.button(QMessageBox.StandardButton.Ok)

def reject_confirmation(dialog):
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
    assert dialog.labelText(QFileDialog.DialogLabel.Accept) == '保存'
    assert dialog.labelText(QFileDialog.DialogLabel.Reject) == '取消'
    return QFileDialog.DialogCode.Rejected

with patch.object(QFileDialog, 'exec', new = cancel_file_dialog):
    assert select_file(None, '导出日志', '', '日志文件 (*.log)', save = True) == ''

with patch('easy_cidaren.ui.main_window.load_token', return_value = 'remembered-token'):
    remembered = UiMainWindow(SimpleNamespace(version = 'test'), logging.getLogger('gui-test'), None)
assert remembered.token_input.text( ) == 'remembered-token'
assert '上次' in remembered.login_hint.text( )
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
assert window.capture_button.text( ) == '获取 Token'
assert window.help_button.text( ) == '查看帮助'
assert window.about_button.text( ) == '关于'
assert window.menuWidget( ) is None
assert window.settings_button.text( ) == '设置'
settings_state = SimpleNamespace(min_time = 1, max_time = 3, spend_min_time = 2, spend_max_time = 10,
                                 br_choices = True, play_music = False, music_path = '')
settings_state.input_info = lambda *args: saved_settings.append(args)
saved_settings = []
with patch.object(window, 'public_info', settings_state):
    window.settings_button.click( )
    assert isinstance(window.settings, SettingsWindow)
    assert window.settings.isVisible( )
    window.settings.min_time.setValue(5)
    with patch('easy_cidaren.ui.settings.show_warning') as warning:
        window.settings.save( )
        warning.assert_called_once( )
        assert not saved_settings
    window.settings.min_time.setValue(1)
    window.settings.save( )
    assert saved_settings[0][:4] == (1, 3, 2, 10)
    assert not window.settings.isVisible( )
with patch('easy_cidaren.ui.log_export.export_logs') as export_logs:
    window.export_logs_button.click( )
    export_logs.assert_called_once_with(window)
with patch('easy_cidaren.ui.main_window.QtGui.QDesktopServices.openUrl', return_value = True) as open_url:
    window.help_button.click( )
    assert open_url.call_args.args[0].toString( ) == 'https://github.com/fstyou/Easy_Cidaren#readme'
def inspect_about(dialog):
    buttons = {button.text( ): button for button in dialog.findChildren(QPushButton)}
    assert {'复制信息', '确定'} <= buttons.keys( )
    assert '项目首页' not in buttons
    assert '设备 ID' in dialog.info_text
    assert 'GNU GPL v3' in dialog.info_text
    project_link = dialog.findChild(QLabel, 'projectLink')
    assert 'https://github.com/fstyou/Easy_Cidaren' in project_link.text( )
    with patch('easy_cidaren.ui.about.QtGui.QDesktopServices.openUrl', return_value = True) as open_url:
        project_link.linkActivated.emit('https://github.com/fstyou/Easy_Cidaren')
        assert open_url.call_args.args[0].toString( ) == 'https://github.com/fstyou/Easy_Cidaren'
    with patch('easy_cidaren.ui.about.show_information'):
        buttons['复制信息'].click( )
        assert QApplication.clipboard( ).text( ) == dialog.info_text
    return 0

with patch.object(AboutDialog, 'exec', new = inspect_about):
    window.about_button.click( )
original_about_exec = AboutDialog.exec
def close_about(dialog):
    QTimer.singleShot(0, dialog.close)
    result = original_about_exec(dialog)
    assert not dialog.isVisible( )
    return result

with patch.object(AboutDialog, 'exec', new = close_about):
    window.about_button.click( )
assert not window.stop_task.isEnabled( )
assert not window.task_card.isVisible( )
assert not window.user_info.isVisible( )
assert not window.progress_card.isVisible( )
assert window.login_hint.isVisible( )
assert '获取 Token 并登录' in window.login_hint.text( )
window.resize(820, 700)
app.processEvents( )
assert window.account_card.height( ) <= window.account_card.sizeHint( ).height( ) + 2
with patch('easy_cidaren.ui.main_window.show_warning'):
    window.on_login_result(1)
assert not window.task_card.isVisible( )
with patch.object(window, 'get_task_list'):
    window.on_login_result({'data': {'user_info': {'student_name': '测试用户'}}})
app.processEvents( )
assert window.task_card.isVisible( )
assert window.user_info.isVisible( )
if window.minimumHeight( ) < window.maximumHeight( ):
    assert window.scroll_area.verticalScrollBar( ).maximum( ) == 0
assert window.maximumHeight( ) <= 800
assert window.minimumHeight( ) <= window.maximumHeight( )
assert not window.login_hint.isVisible( )
assert window.label_4.isVisible( )
assert not window.label_4.isWindow( )
assert window.label_4.window( ) is window
assert not window.progress_card.isVisible( )
assert not window.stop_task.isVisible( )
unopened = {'task_name': '未开始的任务', 'over_status': 1, 'progress': 0,
            'start_time': 1793604627860, 'over_time': 115172140}
available = {'task_name': '已开放的任务', 'over_status': 2, 'progress': 0}
def fake_get_class_task(info, page):
    info.task_total_count = 2

def fake_get_all_task(info):
    info.task_list = [unopened, available]

with patch('easy_cidaren.ui.main_window.get_class_task', fake_get_class_task), \
        patch('easy_cidaren.ui.main_window.get_all_task', fake_get_all_task):
    window.get_task_list( )
app.processEvents( )
unavailable_radio = window.task_list.cellWidget(0, 0).findChild(QRadioButton)
available_radio = window.task_list.cellWidget(1, 0).findChild(QRadioButton)
assert not unavailable_radio.isEnabled( )
assert available_radio.isEnabled( )
assert unavailable_radio.geometry( ).center( ).x( ) == available_radio.geometry( ).center( ).x( )
unavailable_radio.click( )
assert not unavailable_radio.isChecked( )
window.task_list.setRowCount(30)
window.set_ui_enabled(False)
app.processEvents( )
assert window.task_list.isEnabled( )
assert window.task_list.selectionMode( ) == QAbstractItemView.SelectionMode.NoSelection
assert not available_radio.isEnabled( )
scrollbar = window.task_list.verticalScrollBar( )
assert scrollbar.maximum( ) > 0
scrollbar.setValue(scrollbar.maximum( ))
assert scrollbar.value( ) == scrollbar.maximum( )
window.set_ui_enabled(True)
assert available_radio.isEnabled( )
assert not unavailable_radio.isEnabled( )
assert window.task_list.selectionMode( ) == QAbstractItemView.SelectionMode.SingleSelection
window.task_list.setRowCount(2)
assert not (window.task_list.item(0, 1).flags( ) & Qt.ItemFlag.ItemIsSelectable)
assert window.task_list.item(0, 2).text( ) != '—'
assert window.task_list.item(0, 3).text( ) != '—'
assert not (window.task_list.item(0, 3).flags( ) & Qt.ItemFlag.ItemIsSelectable)
assert window.task_list.item(1, 2).text( ) == '—'
assert '尚未开始' in window.task_list.item(0, 1).toolTip( )
assert window.task_list.item(1, 1).flags( ) & Qt.ItemFlag.ItemIsSelectable

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
assert not window.task_card.isVisible( )
assert not window.user_info.isVisible( )
assert window.login_hint.isVisible( )
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
large_table_height = window.task_list.height( )
large_progress_height = window.progress_card.height( )
window.resize(window.width( ), window.minimumHeight( ))
app.processEvents( )
app.processEvents( )
if window.maximumHeight( ) - window.minimumHeight( ) >= 80:
    assert window.task_list.height( ) < large_table_height
    assert window.progress_card.height( ) == large_progress_height
    assert window.scroll_area.verticalScrollBar( ).maximum( ) == 0
window.resize(820, 300)
app.processEvents( )
app.processEvents( )
assert window.progress_card.isVisible( )
assert window.progress_card.y( ) >= window.task_card.y( ) + window.task_card.height( )
assert window.start_task.y( ) >= window.task_list.y( ) + window.task_list.height( )
if window.minimumHeight( ) < window.maximumHeight( ):
    assert window.scroll_area.verticalScrollBar( ).maximum( ) == 0
assert window.stop_task.isVisible( )
assert window.progress_bar.maximum( ) == 0
window.update_progress('3/10|2|0|1|1/1|测试任务')
assert window.progress_bar.maximum( ) == 10
assert window.progress_bar.value( ) == 3
assert window.progress_skip_label.text( ) == '跳过 1'
window.play_music = lambda: None
window.get_task_list = lambda: None
window._batch_mode = False
with patch('easy_cidaren.ui.main_window.show_information'):
    window.on_task_finished('任务已完成')
assert not window.progress_card.isVisible( )
assert not window.stop_task.isVisible( )
assert window.maximumHeight( ) <= 800
window.show_task_progress('测试任务')
with patch('easy_cidaren.ui.main_window.show_error') as critical:
    window.on_task_error('无法跳过题目')
    assert '无法跳过题目' in critical.call_args.args
assert not window.progress_card.isVisible( )

calls = []
window.token_login = lambda: calls.append(window.token_input.text( ))
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
dialog.show_status('请在目标客户端手动设置 HTTP/HTTPS 代理为 127.0.0.1:8888，结束后恢复原设置。')
dialog.show_status('请在客户端信任 mitmproxy 证书：/tmp/test-cert.cer')
app.processEvents( )
assert dialog.height( ) < 600
assert dialog.maximumHeight( ) == dialog.height( )
assert dialog.subtitle_label.y( ) <= dialog.title_label.y( ) + dialog.title_label.height( ) + 20
assert dialog.instructions.y( ) <= dialog.subtitle_label.y( ) + dialog.subtitle_label.height( ) + 20
steps = dialog.instructions.text( )
assert '127.0.0.1:8888' in steps
assert '/tmp/test-cert.cer' in steps
assert steps.index('127.0.0.1:8888') < steps.index('/tmp/test-cert.cer') < steps.index('公众号')
assert not hasattr(dialog, 'details')
dialog.show_status('请在微信中打开词达人学生端，等待获取 token。')
assert '等待获取' in dialog.status_label.text( )
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
