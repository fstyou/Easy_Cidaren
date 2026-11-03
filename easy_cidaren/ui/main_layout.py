"""Construct the main window and its controls."""

import os
from typing import TYPE_CHECKING, cast

from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon

from easy_cidaren.paths import ASSETS_DIR
from easy_cidaren.ui.user_info import UserInfoWidget


if TYPE_CHECKING:
    from easy_cidaren.ui.main_window import UiMainWindow


class MainWindowUi:
    """Own the controls constructed for the main window."""
    
    def __init__(self, window: "UiMainWindow"):
        MainWindow = window
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 250)
        MainWindow.setMinimumSize(800, 250)
        icon_path = str(ASSETS_DIR / 'icon.ico')
        if os.path.exists(icon_path):
            MainWindow.setWindowIcon(QIcon(icon_path))
        self.scroll_area = QtWidgets.QScrollArea(parent = MainWindow)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.centralwidget = QtWidgets.QWidget( )
        self.centralwidget.setObjectName("centralwidget")
        page = QtWidgets.QVBoxLayout(self.centralwidget)
        page.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        page.setContentsMargins(20, 16, 20, 16)
        page.setSpacing(12)
        
        title = QtWidgets.QLabel("Easy Cidaren")
        title.setObjectName("pageTitle")
        header = QtWidgets.QHBoxLayout( )
        header.addWidget(title)
        header.addStretch( )
        self.settings_button = QtWidgets.QPushButton("设置")
        self.settings_button.clicked.connect(window.open_settings)
        header.addWidget(self.settings_button)
        self.export_logs_button = QtWidgets.QPushButton("导出日志")
        self.export_logs_button.clicked.connect(window.export_logs)
        header.addWidget(self.export_logs_button)
        self.help_button = QtWidgets.QPushButton("查看帮助")
        self.help_button.clicked.connect(window.open_readme)
        header.addWidget(self.help_button)
        self.about_button = QtWidgets.QPushButton("关于")
        self.about_button.clicked.connect(window.show_about)
        header.addWidget(self.about_button)
        page.addLayout(header)
        
        self.account_card = QtWidgets.QFrame( )
        self.account_card.setObjectName("card")
        self.account_card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                        QtWidgets.QSizePolicy.Policy.Fixed)
        account_layout = QtWidgets.QVBoxLayout(self.account_card)
        account_layout.setContentsMargins(16, 12, 16, 12)
        account_layout.setSpacing(8)
        self.label = QtWidgets.QLabel("账号登录")
        self.label.setObjectName("sectionTitle")
        account_layout.addWidget(self.label)
        self.login_hint = QtWidgets.QLabel("请获取 Token 并登录，或输入已有的 Token")
        self.login_hint.setObjectName("loginHint")
        self.login_hint.setWordWrap(True)
        account_layout.addWidget(self.login_hint)
        token_row = QtWidgets.QHBoxLayout( )
        self.token_input = QtWidgets.QLineEdit( )
        self.token_input.setPlaceholderText("输入或获取 Token")
        self.token_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.token_input.returnPressed.connect(window.token_login)
        self.capture_button = QtWidgets.QPushButton("获取 Token")
        self.capture_button.clicked.connect(window.toggle_token_capture)
        self.login = QtWidgets.QPushButton("登录")
        self.login.setObjectName("primaryButton")
        self.login.clicked.connect(window.token_login)
        token_row.addWidget(self.token_input, 1)
        token_row.addWidget(self.capture_button)
        token_row.addWidget(self.login)
        account_layout.addLayout(token_row)
        self.warn_info = QtWidgets.QLabel("")
        self.warn_info.setWordWrap(True)
        self.warn_info.hide( )
        account_layout.addWidget(self.warn_info)
        self.user_info = UserInfoWidget( )
        self.user_info.hide( )
        account_layout.addWidget(self.user_info)
        page.addWidget(self.account_card)
        
        content = QtWidgets.QVBoxLayout( )
        content.setSpacing(12)
        page.addLayout(content, 1)
        self.task_card = QtWidgets.QFrame( )
        self.task_card.setObjectName("card")
        task_layout = QtWidgets.QVBoxLayout(self.task_card)
        task_layout.setContentsMargins(16, 12, 16, 12)
        task_layout.setSpacing(8)
        task_header = QtWidgets.QHBoxLayout( )
        self.label_6 = QtWidgets.QLabel("任务列表")
        self.label_6.setObjectName("sectionTitle")
        self.learn_task = QtWidgets.QRadioButton("学习任务")
        self.learn_task.setChecked(True)
        self.learn_task.clicked.connect(window.get_task_list)
        self.test_task = QtWidgets.QRadioButton("测试任务")
        self.test_task.clicked.connect(window.get_task_list)
        task_header.addWidget(self.label_6)
        task_header.addStretch( )
        task_header.addWidget(self.learn_task)
        task_header.addWidget(self.test_task)
        task_layout.addLayout(task_header)
        self.task_list = QtWidgets.QTableWidget( )
        self.task_list.setMinimumHeight(68)
        task_list_policy = self.task_list.sizePolicy( )
        task_list_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Ignored)
        self.task_list.setSizePolicy(task_list_policy)
        self.task_list.setColumnCount(6)
        self.task_list.setHorizontalHeaderLabels(["", "任务", "开始时间", "截止时间", "进度", "得分"])
        vertical_header = cast(QtWidgets.QHeaderView, self.task_list.verticalHeader( ))
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(36)
        self.task_list.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.task_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.task_list.setShowGrid(False)
        self.task_list.setWordWrap(False)
        horizontal_header = cast(QtWidgets.QHeaderView, self.task_list.horizontalHeader( ))
        for column in range(6):
            mode = (QtWidgets.QHeaderView.ResizeMode.Stretch if column == 1
                    else QtWidgets.QHeaderView.ResizeMode.Fixed)
            horizontal_header.setSectionResizeMode(column, mode)
        self.task_list.setColumnWidth(0, 36)
        self.task_list.setColumnWidth(2, 135)
        self.task_list.setColumnWidth(3, 135)
        self.task_list.setColumnWidth(4, 66)
        self.task_list.setColumnWidth(5, 78)
        self.task_radio_group = QtWidgets.QButtonGroup(window)
        self.task_radio_group.setExclusive(True)
        self.task_list.itemClicked.connect(window.on_task_item_clicked)
        task_layout.addWidget(self.task_list, 1)
        actions = QtWidgets.QHBoxLayout( )
        self.start_task = QtWidgets.QPushButton("开始任务")
        self.start_task.setObjectName("primaryButton")
        self.start_task.clicked.connect(window.start)
        self.batch_start = QtWidgets.QPushButton("一键刷题")
        self.batch_start.clicked.connect(window.start_batch)
        self.stop_task = QtWidgets.QPushButton("停止任务")
        self.stop_task.setEnabled(False)
        self.stop_task.hide( )
        self.stop_task.clicked.connect(window.stop_current_task)
        actions.addWidget(self.start_task)
        actions.addWidget(self.batch_start)
        actions.addWidget(self.stop_task)
        actions.addStretch( )
        task_layout.addLayout(actions)
        content.addWidget(self.task_card, 1)
        self.task_card.hide( )
        
        self.progress_card = QtWidgets.QFrame( )
        self.progress_card.setObjectName("card")
        self.progress_card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                         QtWidgets.QSizePolicy.Policy.Fixed)
        progress_layout = QtWidgets.QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(10)
        progress_title = QtWidgets.QLabel("任务进度")
        progress_title.setObjectName("sectionTitle")
        progress_header = QtWidgets.QHBoxLayout( )
        progress_header.addWidget(progress_title)
        progress_header.addStretch( )
        self.progress_label = QtWidgets.QLabel("")
        self.progress_label.setObjectName("progressCount")
        progress_header.addWidget(self.progress_label)
        progress_layout.addLayout(progress_header)
        self.progress_task_label = QtWidgets.QLabel("正在准备任务…")
        self.progress_task_label.setObjectName("progressTask")
        self.progress_task_label.setWordWrap(True)
        progress_layout.addWidget(self.progress_task_label)
        self.progress_bar = QtWidgets.QProgressBar( )
        self.progress_bar.setObjectName("taskProgress")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        stats = QtWidgets.QHBoxLayout( )
        stats.setSpacing(8)
        self.progress_right_label = QtWidgets.QLabel("")
        self.progress_wrong_label = QtWidgets.QLabel("")
        self.progress_skip_label = QtWidgets.QLabel("")
        self.progress_right_label.setObjectName("progressCorrect")
        self.progress_wrong_label.setObjectName("progressWrong")
        self.progress_skip_label.setObjectName("progressSkipped")
        for label in (self.progress_right_label, self.progress_wrong_label, self.progress_skip_label):
            stats.addWidget(label)
        stats.addStretch( )
        progress_layout.addLayout(stats)
        content.addWidget(self.progress_card)
        self.progress_card.hide( )
        self.scroll_area.setWidget(self.centralwidget)
        MainWindow.setCentralWidget(self.scroll_area)
        MainWindow.setStyleSheet("""
            QMainWindow, QWidget#centralwidget { background: #f4f6f9; color: #263548; }
            QFrame#card { background: #ffffff; border: 1px solid #dce3ec; border-radius: 10px; }
            QLabel { color: #263548; font-size: 13px; }
            QLabel#pageTitle { font-size: 22px; font-weight: 600; color: #20344f; }
            QLabel#sectionTitle { font-size: 15px; font-weight: 600; color: #253b57; }
            QLabel#loginHint { color: #52657c; font-size: 13px; }
            QLabel#progressTask { color: #344b66; font-size: 13px; font-weight: 500; }
            QLabel#progressCount { color: #526b87; font-size: 12px; }
            QLabel#progressCorrect, QLabel#progressWrong, QLabel#progressSkipped {
                border-radius: 5px; padding: 4px 8px; font-size: 12px;
            }
            QLabel#progressCorrect { color: #196b4b; background: #edf7f1; }
            QLabel#progressWrong { color: #a73630; background: #fdf0ef; }
            QLabel#progressSkipped { color: #855708; background: #fcf5e8; }
            QLineEdit, QTextBrowser, QTableWidget { background: #ffffff; border: 1px solid #cfd9e5; border-radius: 6px; padding: 7px; color: #263548; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #3971c4; }
            QTableWidget { selection-background-color: #e5eefb; selection-color: #20344f; }
            QHeaderView::section { background: #f3f6fa; border: none; padding: 7px; color: #52657c; font-size: 12px; }
            QRadioButton { color: #34465d; font-size: 13px; }
            QPushButton { background: #edf2f7; color: #29415f; border: 1px solid #d4deea; border-radius: 6px; padding: 7px 14px; font-size: 13px; }
            QPushButton:hover { background: #e1eaf5; }
            QPushButton:disabled { color: #68798e; background: #edf0f4; }
            QPushButton#primaryButton { background: #3269bd; border-color: #3269bd; color: #ffffff; font-weight: 600; }
            QPushButton#primaryButton:hover { background: #285aa4; }
            QPushButton#primaryButton:disabled { color: #526984; background: #dce5f0; border-color: #dce5f0; }
            QProgressBar#taskProgress { border: 0; border-radius: 4px; background: #e3ebf4; height: 8px; }
            QProgressBar#taskProgress::chunk { border-radius: 4px; background: #3977cf; }
        """)
