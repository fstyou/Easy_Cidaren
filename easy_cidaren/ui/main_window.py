import os

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from easy_cidaren.api.login import verify_token
from easy_cidaren.core.public_info import PublicInfo
from easy_cidaren.core.task_selection import batch_tasks, load_class_tasks, task_times, unavailable_reason
from easy_cidaren.paths import ASSETS_DIR, CAPTURE_DATA_DIR
from easy_cidaren.token_capture.token_store import load_token
from easy_cidaren.ui.about import AboutDialog
from easy_cidaren.ui.dialogs import confirm_action, create_message, show_error, show_information, show_warning
from easy_cidaren.ui.main_layout import MainWindowUi
from easy_cidaren.ui.request_worker import RequestWorker
from easy_cidaren.ui.settings import SettingsWindow


class UiMainWindow(QMainWindow):
    def __init__(self, public_info, main_logger, task_worker_class):
        super(UiMainWindow, self).__init__( )
        self.public_info = public_info
        self.main_logger = main_logger
        self.task_worker_class = task_worker_class
        self.settings: SettingsWindow | None = None
        self._sound_effect: QSoundEffect | None = None
        self._logged_in = False
        self.token = ''
        self.task_worker = None
        self._batch_mode = False
        self.capture_worker = None
        self.capture_dialog = None
        self._capture_error = False
        self.login_worker = None
        self.task_list_worker = None
        self._captured_token = None
        self._capture_stopping = False
        self._notice_dialog = None
        self._notice_messages = []
        self._capture_warnings = []
        self._screen_signal_connected = False
        self._minimum_height_check_pending = False
        self.ui = MainWindowUi(self)
        self.setWindowTitle(f"Easy Cidaren · {self.public_info.version}")
        previous_token = load_token( )
        if previous_token:
            self.ui.token_input.setText(previous_token)
            self.ui.login_hint.setText("已读取上次获取的 Token，请点击登录")
        self._apply_window_limits( )
    
    
    def show_task_progress(self, task_name):
        was_hidden = self.ui.progress_card.isHidden( )
        self.ui.progress_task_label.setText(task_name)
        self.ui.progress_bar.setRange(0, 0)
        self.ui.progress_label.setText("正在准备题目…")
        self.ui.progress_right_label.setText("正确 0")
        self.ui.progress_wrong_label.setText("错误 0")
        self.ui.progress_skip_label.setText("跳过 0")
        self.ui.progress_card.show( )
        self.ui.stop_task.show( )
        self._apply_window_limits( )
        if was_hidden:
            QtCore.QTimer.singleShot(0, self._fit_expanded_content)
    
    def _fit_expanded_content(self):
        """Grow for newly visible content, keeping the window within the screen."""
        if not self.isVisible( ):
            return
        self.ui.centralwidget.layout( ).invalidate( )
        self.ui.centralwidget.layout( ).activate( )
        screen = self.screen( )
        available = screen.availableGeometry( ) if screen else None
        frame_extra = max(0, self.frameGeometry( ).height( ) - self.height( ))
        maximum = min(self.maximumHeight( ),
                      max(1, available.height( ) - frame_extra)) if available else self.maximumHeight( )
        chrome = max(0, self.height( ) - self.ui.scroll_area.viewport( ).height( ))
        content_height = max(self.ui.centralwidget.minimumSizeHint( ).height( ),
                             self.ui.centralwidget.minimumHeight( ),
                             self.ui.centralwidget.layout( ).minimumSize( ).height( ))
        required = content_height + chrome + 4
        self.setMinimumHeight(max(self.minimumHeight( ), min(required, maximum)))
        # Keep some room for tasks initially; the table can shrink to its minimum later.
        preferred = required + (96 if not self.ui.task_card.isHidden( ) else 0)
        target = max(self.height( ), min(preferred, maximum))
        if target > self.height( ):
            self.resize(self.width( ), target)
        if available:
            frame = self.frameGeometry( )
            if frame.bottom( ) > available.bottom( ):
                self.move(self.x( ), max(available.top( ), self.y( ) - (frame.bottom( ) - available.bottom( ))))
        self._reveal_progress( )
        self._schedule_minimum_height_check( )
    
    def _reveal_progress(self):
        if self.ui.progress_card.isVisible( ):
            self.ui.scroll_area.ensureWidgetVisible(self.ui.progress_card, 0, 8)
    
    def set_logged_in(self, logged_in):
        self._logged_in = logged_in
        self.ui.label.setText('账号信息' if logged_in else '账号登录')
        self.ui.login_hint.setVisible(not logged_in)
        self.ui.user_info.setVisible(logged_in)
        self.ui.task_card.setVisible(logged_in)
        if not logged_in:
            self.ui.progress_card.hide( )
            self.ui.stop_task.hide( )
        self._apply_window_limits( )
        if logged_in:
            QtCore.QTimer.singleShot(0, self._fit_expanded_content)
    
    def _apply_window_limits(self):
        """Use compact limits for each stage, capped by the current screen."""
        running = not self.ui.progress_card.isHidden( )
        logged_in = not self.ui.task_card.isHidden( )
        min_height, max_height = (420, 900) if running else ((360, 800) if logged_in else (260, 380))
        screen = self.screen( )
        if screen:
            available = screen.availableGeometry( )
            frame_width = max(0, self.frameGeometry( ).width( ) - self.width( ))
            frame_height = max(0, self.frameGeometry( ).height( ) - self.height( ))
            max_width = max(1, min(1000, available.width( ) - frame_width))
            max_height = max(1, min(max_height, available.height( ) - frame_height))
        else:
            max_width = 1000
        self.setMinimumSize(min(680, max_width), min(min_height, max_height))
        self.setMaximumSize(max_width, max_height)
    
    def showEvent(self, a0):
        super( ).showEvent(a0)
        handle = self.windowHandle( )
        if handle and not self._screen_signal_connected:
            handle.screenChanged.connect(self._on_screen_changed)
            self._screen_signal_connected = True
        self._apply_window_limits( )
    
    def resizeEvent(self, a0):
        super( ).resizeEvent(a0)
        self._schedule_minimum_height_check( )
    
    def _schedule_minimum_height_check(self):
        if not hasattr(self, 'ui') or self.ui.progress_card.isHidden( ):
            return
        if not self._minimum_height_check_pending:
            self._minimum_height_check_pending = True
            QtCore.QTimer.singleShot(0, self._correct_running_minimum_height)
    
    def _correct_running_minimum_height(self):
        self._minimum_height_check_pending = False
        if not self.isVisible( ) or self.ui.progress_card.isHidden( ):
            return
        overflow = self.ui.scroll_area.verticalScrollBar( ).maximum( )
        if overflow <= 0:
            return
        target = min(self.maximumHeight( ), self.height( ) + overflow + 8)
        if target > self.height( ):
            self.setMinimumHeight(max(self.minimumHeight( ), target))
            screen = self.screen( )
            if screen:
                available = screen.availableGeometry( )
                frame = self.frameGeometry( )
                if frame.bottom( ) > available.bottom( ):
                    self.move(self.x( ), max(available.top( ), self.y( ) - (frame.bottom( ) - available.bottom( ))))
    
    def _on_screen_changed(self, _screen):
        self._apply_window_limits( )
        QtCore.QTimer.singleShot(0, self._fit_expanded_content)
    
    def _hide_task_progress(self):
        self.ui.progress_card.hide( )
        self.ui.stop_task.hide( )
        self._apply_window_limits( )
        QtCore.QTimer.singleShot(0, self._fit_expanded_content)
    
    def show_notice(self, message):
        """Keep task warnings visible without blocking the worker or opening many windows."""
        if self._notice_dialog is None:
            self._notice_messages = []
            self._notice_dialog = create_message(self, "运行提示", "", QMessageBox.Icon.Warning)
            self._notice_dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
            self._notice_dialog.finished.connect(self._notice_closed)
        self._notice_messages.append(str(message))
        prefix = "仅显示最近 20 条提示：\n\n" if len(self._notice_messages) > 20 else ""
        self._notice_dialog.setText(prefix + "\n\n".join(self._notice_messages[-20:]))
        self._notice_dialog.show( )
        self._notice_dialog.raise_( )
    
    def _notice_closed(self):
        dialog = self._notice_dialog
        self._notice_dialog = None
        self._notice_messages = []
        if dialog:
            dialog.deleteLater( )
    
    def token_login(self):
        if self.login_worker:
            return
        self.token = self.ui.token_input.text( ).split('\n')[0].strip( )
        if not self.token:
            show_warning(self, '登录失败', '请输入 Token')
            return
        self.set_logged_in(False)
        self.ui.user_info.clear( )
        self.ui.task_list.setRowCount(0)
        self.set_ui_enabled(False)
        self.ui.stop_task.setEnabled(False)
        self.ui.warn_info.setText('正在登录…')
        self.ui.warn_info.show( )
        self.login_worker = RequestWorker(lambda: verify_token(self.token), self)
        self.login_worker.result_ready.connect(self.on_login_result)
        self.login_worker.finished.connect(self.on_login_finished)
        self.login_worker.start( )
    
    def on_login_result(self, result):
        if isinstance(result, Exception):
            self.main_logger.error('登录失败：%s', result, exc_info = (type(result), result, result.__traceback__))
            result = 7
        if not isinstance(result, dict):
            errors = {1: 'Token 已过期，请重新获取', 2: 'HTTP 请求失败',
                      3: '连接超时', 4: '响应格式错误', 5: 'SSL 连接错误',
                      6: '代理连接错误', 7: '网络连接错误'}
            message = errors.get(result, '服务端响应异常') if isinstance(result, int) else '服务端响应异常'
            self.ui.warn_info.setText('')
            self.ui.warn_info.hide( )
            show_warning(self, '登录失败', message)
            return
        try:
            user = result['data']['user_info']
            self.ui.user_info.set_user(user)
        except (KeyError, TypeError, AttributeError, ValueError):
            self.ui.warn_info.setText('')
            self.ui.warn_info.hide( )
            show_warning(self, '登录失败', '服务端返回的用户信息不完整')
            return
        self.ui.warn_info.setText('')
        self.ui.warn_info.hide( )
        self.set_logged_in(True)
        self.get_task_list( )
    
    def on_login_finished(self):
        worker = self.login_worker
        self.login_worker = None
        self.set_ui_enabled(self.task_list_worker is None)
        if worker:
            worker.deleteLater( )
    
    def get_task_list(self):
        if self.task_list_worker is not None or self.task_worker is not None or self.capture_worker is not None:
            return
        if not self._logged_in:
            return
        self.ui.task_list.setRowCount(0)
        self.public_info.task_list = []
        self.public_info._task_choices = 1 if self.ui.learn_task.isChecked( ) else 2
        PublicInfo.task_type = 'ClassTask'
        PublicInfo.task_type_int = 2
        self.set_ui_enabled(False)
        self.ui.stop_task.setEnabled(False)
        self.ui.warn_info.setText('正在加载任务…')
        self.ui.warn_info.show( )
        worker = RequestWorker(lambda: load_class_tasks(self.public_info), self)
        self.task_list_worker = worker
        worker.result_ready.connect(self.on_task_list_result)
        worker.finished.connect(self.on_task_list_finished)
        worker.start( )
    
    def on_task_list_result(self, result):
        if isinstance(result, Exception):
            self.main_logger.error('获取任务列表失败：%s', result)
            show_warning(self, "获取任务列表失败", str(result))
            return
        if not result:
            show_information(self, "任务列表", "当前没有任务")
            return
        try:
            self.render_task_list( )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            self.main_logger.error('任务列表格式错误：%s', exc)
            self.public_info.task_list = []
            self.ui.task_list.setRowCount(0)
            show_warning(self, '任务列表格式错误', '服务端返回的任务信息不完整，请稍后重试')
    
    def render_task_list(self):
        for task in self.public_info.task_list:
            task_name = task['task_name']
            progress = task.get('progress', 0)
            score = task.get('score') or 0
            over_status = task.get('over_status', 2)
            row = self.ui.task_list.rowCount( )
            self.ui.task_list.insertRow(row)
            # 左侧目标任务单选框（容器+布局使其在格内居中）
            radio = QtWidgets.QRadioButton(self.ui.task_list)
            radio.clicked.connect(lambda checked, r = row: self._select_task_row(r))
            self.ui.task_radio_group.addButton(radio)
            radio_container = QtWidgets.QWidget(self.ui.task_list)
            radio_layout = QtWidgets.QHBoxLayout(radio_container)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            radio_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            radio_layout.addWidget(radio)
            self.ui.task_list.setCellWidget(row, 0, radio_container)
            reason = unavailable_reason(task)
            if reason:
                radio.setEnabled(False)
                radio.setToolTip(reason)
                radio_container.setToolTip(reason)
            score_text = str(score)
            if over_status == 1:
                score_text += " (未开始)"
            start_time, end_time = task_times(task)
            # 每个数据单元格都保存任务，以支持点击任意列选择
            for col, text in enumerate([task_name, start_time, end_time, f"{progress}%", score_text],
                                       start = 1):
                cell = QtWidgets.QTableWidgetItem(text)
                cell.setData(QtCore.Qt.ItemDataRole.UserRole, task)
                if progress >= 100:
                    cell.setForeground(QtGui.QColor("#196b4b"))
                elif reason:
                    cell.setForeground(QtGui.QColor("#65758a"))
                if reason:
                    cell.setToolTip(reason)
                    cell.setFlags(cell.flags( ) & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.ui.task_list.setItem(row, col, cell)
    
    def on_task_list_finished(self):
        worker = self.task_list_worker
        self.task_list_worker = None
        self.ui.warn_info.hide( )
        self.set_ui_enabled(self.login_worker is None)
        if worker:
            worker.deleteLater( )
    
    def _select_task_row(self, row):
        """
        勾选单选框时同步选中表格行
        :param row:
        :return:
        """
        if self.ui.task_list.selectionMode( ) == QtWidgets.QAbstractItemView.SelectionMode.NoSelection:
            return
        item = self.ui.task_list.item(row, 1)
        if item and not unavailable_reason(item.data(QtCore.Qt.ItemDataRole.UserRole)):
            self.ui.task_list.setCurrentItem(item)
    
    def on_task_item_clicked(self, item):
        """
        点击任务行时自动勾选该行单选框
        :param item:
        :return:
        """
        if self.ui.task_list.selectionMode( ) == QtWidgets.QAbstractItemView.SelectionMode.NoSelection:
            return
        try:
            task = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if task and unavailable_reason(task):
                return
            row = item.row( )
            widget = self.ui.task_list.cellWidget(row, 0)
            radio = widget.findChild(QtWidgets.QRadioButton) if widget else None
            if isinstance(radio, QtWidgets.QRadioButton) and not radio.isChecked( ):
                radio.setChecked(True)
        except Exception as e:
            self.main_logger.error(f"选择任务行失败: {e}")
    
    def confirm_task_start(self, details):
        return confirm_action(
                self, "确认开始", details, confirm_text = "开始", default_confirm = True,
                detail = "运行期间请保持程序打开",
        )
    
    def _start_worker(self, tasks, *, batch_mode):
        self.public_info.is_self_built = False
        self.public_info.right_count = 0
        self.public_info.wrong_count = 0
        self.public_info.skip_count = 0
        self._batch_mode = batch_mode
        self.set_ui_enabled(False)
        self.task_worker = self.task_worker_class(self.public_info, tasks, batch_mode = batch_mode)
        self.task_worker.setParent(self)
        self.task_worker.finished.connect(self.task_worker.deleteLater)
        self.task_worker.task_finished.connect(self.on_task_finished)
        self.task_worker.task_error.connect(self.on_task_error)
        self.task_worker.task_progress.connect(self.update_progress)
        self.task_worker.task_notice.connect(self.on_task_notice)
        if batch_mode:
            self.task_worker.batch_finished.connect(self.on_batch_finished)
        label = f"准备执行 {len(tasks)} 个任务…" if batch_mode else tasks[0]['task_name']
        self.show_task_progress(label)
        self.task_worker.start( )
    
    def start(self):
        try:
            current_item = self.ui.task_list.currentItem( )
            if not self.public_info.task_list == [] and not self.public_info.class_task == [] and current_item:
                if self.ui.learn_task.isChecked( ):
                    self.main_logger.info("开始班级学习任务")
                else:
                    self.main_logger.info("开始班级测试任务")
                task_info = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
                reason = unavailable_reason(task_info)
                if reason:
                    show_warning(self, "无法开始任务", reason)
                    return
                task_name = task_info['task_name']
                if self.confirm_task_start(f"开始以下任务？\n\n{task_name}"):
                    self.public_info.class_task = [task_info]
                    self._start_worker([task_info], batch_mode = False)
            else:
                show_information(self, "无法开始任务", "请先登录并选择要执行的任务")
        except Exception as e:
            self.main_logger.error(f"运行出错，错误信息：{e}")
            self._hide_task_progress( )
            self.set_ui_enabled(True)
            show_warning(self, "启动任务失败", str(e))
    
    def start_batch(self):
        """一键刷题：按顺序自动执行列表中所有未完成的任务"""
        try:
            if not self._logged_in:
                show_information(self, "无法开始刷题", "请先登录，再使用一键刷题")
                return
            tasks = batch_tasks(self.public_info.task_list)
            if not tasks:
                show_information(self, "没有可执行的任务", "当前没有已开始且未完成的任务")
                return
            skipped = len(self.public_info.task_list) - len(tasks)
            details = f"开始按顺序执行 {len(tasks)} 个未完成任务？"
            if skipped:
                details += f"\n将跳过 {skipped} 个未开始或已完成的任务。"
            if not self.confirm_task_start(details):
                return
            self._start_worker(tasks, batch_mode = True)
        except Exception as e:
            self.main_logger.error(f"一键刷题启动失败: {e}")
            self._hide_task_progress( )
            self.set_ui_enabled(True)
            show_warning(self, "启动任务失败", str(e))
    
    def update_progress(self, progress_text):
        """
        更新进度
        :param progress_text: 格式 "done/total|right|wrong|skip|index/total|task_name"
        :return:
        """
        # 先按 | 切分(避免 index/total 段中的 / 破坏 done/total 解析)
        segments = progress_text.split('|', 5)
        dt = segments[0].split('/')
        if len(dt) == 2:
            try:
                done = int(dt[0])
                total = int(dt[1])
                self.ui.progress_bar.setRange(0, total)
                self.ui.progress_bar.setValue(done)
                self.ui.progress_label.setText(f"{done}/{total}")
                if len(segments) > 2:
                    self.ui.progress_right_label.setText(f"正确 {segments[1]}")
                    self.ui.progress_wrong_label.setText(f"错误 {segments[2]}")
                    if len(segments) > 3:
                        self.ui.progress_skip_label.setText(f"跳过 {segments[3]}")
                        if len(segments) > 5:
                            self.ui.progress_task_label.setText(f"[{segments[4]}] {segments[5]}")
            except ValueError:
                pass
    
    def on_task_finished(self, message):
        """
        任务完成
        :param message:
        :return:
        """
        self.main_logger.info(f'{message}')
        if self._batch_mode:
            # 批量模式：记录结果，全部结束后再刷新任务列表
            self.show_task_progress("正在准备下一个任务…")
            return
        self.set_ui_enabled(True)
        self._hide_task_progress( )
        self.play_music( )
        show_information(self, "任务完成", message)
        # 自动刷新任务列表，显示最新进度和得分
        QtCore.QTimer.singleShot(1000, self.get_task_list)
        if self.task_worker:
            self.task_worker = None
    
    def on_batch_finished(self, summary):
        """
        一键刷题全部任务执行结束
        :param summary:
        :return:
        """
        self._batch_mode = False
        self.set_ui_enabled(True)
        self._hide_task_progress( )
        self.main_logger.info(summary)
        self.play_music( )
        show_information(self, "一键刷题完成", summary)
        # 等服务端进度落库后再刷新
        QtCore.QTimer.singleShot(1000, self.get_task_list)
        if self.task_worker:
            self.task_worker = None
    
    def on_task_notice(self, message):
        """
        任务执行中的提示信息
        :param message:
        :return:
        """
        self.main_logger.info(message)
        self.show_notice(message)
    
    def on_task_error(self, error_message):
        """
        任务出错
        :param error_message:
        :return:
        """
        self._batch_mode = False
        self.set_ui_enabled(True)
        self._hide_task_progress( )
        self.main_logger.error(f"运行出错，错误信息：{error_message}")
        show_error(self, "任务停止", error_message)
        if self.task_worker:
            self.task_worker = None
    
    def open_readme(self):
        url = QtCore.QUrl("https://github.com/fstyou/Easy_Cidaren#readme")
        if not QtGui.QDesktopServices.openUrl(url):
            show_warning(self, "无法打开帮助", "无法打开浏览器，请检查系统默认浏览器设置")
    
    def open_settings(self, _action = None):
        if self.settings is not None and self.settings.isVisible( ):
            self.settings.raise_( )
            self.settings.activateWindow( )
            return
        settings = SettingsWindow(self.public_info, self)
        self.settings = settings
        settings.show( )
    
    def show_about(self):
        AboutDialog(self.public_info.version, self).exec( )
    
    def export_logs(self):
        from easy_cidaren.ui.log_export import export_logs
        export_logs(self)
    
    def play_music(self):
        """
        播放音乐
        :return:
        """
        if not self.public_info.play_music:
            return
        if self.public_info.music_path:
            if os.path.exists(self.public_info.music_path):
                music_path = self.public_info.music_path
            else:
                music_path = str(ASSETS_DIR / "music.wav")
                self.main_logger.error("自定义音乐文件不存在，使用默认音乐")
        else:
            music_path = str(ASSETS_DIR / "music.wav")
        try:
            effect = QSoundEffect(self)
            self._sound_effect = effect
            effect.setSource(QtCore.QUrl.fromLocalFile(os.path.abspath(music_path)))
            effect.play( )
        except Exception as e:
            self.main_logger.warning(f"播放提示音失败: {e}")
    
    def toggle_token_capture(self):
        if self.capture_worker:
            self._capture_stopping = True
            self.ui.capture_button.setEnabled(False)
            self.capture_worker.stop( )
            return
        from easy_cidaren.ui.token_dialog import CaptureProgressDialog, TokenCaptureWorker
        path = str(CAPTURE_DATA_DIR)
        self._captured_token = None
        self._capture_stopping = False
        self._capture_error = False
        self._capture_warnings = []
        self.capture_dialog = CaptureProgressDialog(self)
        self.capture_dialog.cancel_requested.connect(self.toggle_token_capture)
        self.capture_dialog.finished.connect(self._on_capture_dialog_closed)
        self.capture_worker = TokenCaptureWorker(path)
        self.capture_worker.status_update.connect(self.on_capture_status)
        self.capture_worker.error_occurred.connect(self.on_capture_error)
        self.capture_worker.token_captured.connect(self.on_builtin_token_captured)
        self.capture_worker.finished.connect(self.on_capture_finished)
        self.set_ui_enabled(False)
        self.ui.stop_task.setEnabled(False)
        self.ui.capture_button.setEnabled(True)
        self.ui.capture_button.setText('停止获取')
        self.ui.login.setEnabled(False)
        self.ui.token_input.setEnabled(False)
        self.capture_dialog.open( )
        self.capture_worker.start( )
    
    def on_capture_status(self, message):
        if self.capture_dialog:
            self.capture_dialog.show_status(message)
        if message.startswith(('⛔', '请恢复目标客户端')):
            self._capture_warnings.append(message)
    
    def _on_capture_dialog_closed(self):
        dialog = self.capture_dialog
        self.capture_dialog = None
        if dialog:
            dialog.deleteLater( )
        if self._capture_warnings:
            messages = '\n'.join(self._capture_warnings)
            self._capture_warnings = []
            QtCore.QTimer.singleShot(0, lambda: self.show_notice(messages))
    
    def on_capture_error(self, message):
        self._capture_error = True
        if self.capture_dialog:
            self.capture_dialog.failed(message)
    
    def on_capture_finished(self):
        worker = self.capture_worker
        self.capture_worker = None
        self.set_ui_enabled(True)
        self.ui.capture_button.setText('获取 Token')
        self.ui.login.setEnabled(True)
        self.ui.token_input.setEnabled(True)
        if worker:
            worker.deleteLater( )
        success = bool(self._captured_token and not self._capture_stopping and not self._capture_error)
        if self.capture_dialog:
            self.capture_dialog.finish(success = success, error = self._capture_error)
        if success:
            self.ui.token_input.setText(self._captured_token)
            self._captured_token = None
            self.token_login( )
    
    def on_builtin_token_captured(self, token):
        # Wait for the worker to restore the proxy before attempting login.
        if token:
            self._captured_token = token
            if self.capture_dialog:
                self.capture_dialog.captured( )
    
    def set_ui_enabled(self, enabled):
        self.ui.token_input.setEnabled(enabled)
        self.ui.login.setEnabled(enabled)
        self.ui.capture_button.setEnabled(enabled)
        self.ui.learn_task.setEnabled(enabled)
        self.ui.test_task.setEnabled(enabled)
        self.ui.task_list.setSelectionMode(
                QtWidgets.QAbstractItemView.SelectionMode.SingleSelection if enabled
                else QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        for row in range(self.ui.task_list.rowCount( )):
            container = self.ui.task_list.cellWidget(row, 0)
            radio = container.findChild(QtWidgets.QRadioButton) if container else None
            item = self.ui.task_list.item(row, 1)
            if isinstance(radio, QtWidgets.QRadioButton) and item is not None:
                task = item.data(QtCore.Qt.ItemDataRole.UserRole)
                radio.setEnabled(enabled and not unavailable_reason(task))
        self.ui.start_task.setEnabled(enabled)
        self.ui.batch_start.setEnabled(enabled)
        self.ui.settings_button.setEnabled(enabled)
        self.ui.stop_task.setEnabled(not enabled)
    
    def closeEvent(self, a0):
        if self.task_list_worker and self.task_list_worker.isRunning( ):
            self.task_list_worker.wait( )
        if self.capture_worker and self.capture_worker.isRunning( ):
            self.capture_worker.stop( )
            self.capture_worker.wait( )
        if self.task_worker and self.task_worker.isRunning( ):
            self.task_worker.stop( )
            self.task_worker.wait( )
        if self.login_worker and self.login_worker.isRunning( ):
            self.login_worker.wait( )
        if a0 is not None:
            a0.accept( )
    
    def stop_current_task(self):
        """
        停止当前任务
        :return:
        """
        if self.task_worker and self.task_worker.isRunning( ):
            if confirm_action(self, "确认停止", "确定要停止当前任务吗？", confirm_text = "停止任务"):
                self.task_worker.stop( )
                self.task_worker.quit( )
                self.task_worker.wait( )
                self._batch_mode = False
                self.set_ui_enabled(True)
                self._hide_task_progress( )
                show_information(self, "任务停止", "任务已停止")
                self.task_worker = None
                self.main_logger.info("任务已手动停止")
        else:
            return
