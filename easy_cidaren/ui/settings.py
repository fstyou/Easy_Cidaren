"""Application settings dialog."""

from PyQt6 import QtWidgets

from easy_cidaren.app_logging.config import Log
from easy_cidaren.paths import ASSETS_DIR
from easy_cidaren.ui.dialogs import select_file, show_error, show_warning
from easy_cidaren.ui.styles import DIALOG_STYLE


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, public_info, parent = None):
        super( ).__init__(parent)
        self.public_info = public_info
        self.setWindowTitle('设置')
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_STYLE + '''
            QGroupBox { background: white; border: 1px solid #dce3ec; border-radius: 8px;
                        margin-top: 12px; padding: 16px 12px 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            QSpinBox, QLineEdit { background: white; color: #263548; border: 1px solid #cfd9e5;
                                  border-radius: 5px; padding: 5px; font-size: 13px; }
            QSpinBox { padding-right: 30px; }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border; width: 25px; height: 14px;
                background: #edf2f7; border: 0; border-left: 1px solid #d4deea;
            }
            QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 5px; }
            QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 5px; }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #dce8f5; }
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed { background: #cbdcf0; }
        ''' + '\nQSpinBox::up-arrow { image: url("' + (ASSETS_DIR / 'spin_up.svg').as_posix( ) + '"); }'
                           + '\nQSpinBox::down-arrow { image: url("' + (
                                   ASSETS_DIR / 'spin_down.svg').as_posix( ) + '"); }')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        title = QtWidgets.QLabel('设置')
        title.setObjectName('title')
        layout.addWidget(title)
        
        timing = QtWidgets.QGroupBox('答题')
        timing_layout = QtWidgets.QFormLayout(timing)
        timing_layout.setSpacing(10)
        self.min_time = self._seconds(public_info.min_time)
        self.max_time = self._seconds(public_info.max_time)
        self.min_time_2 = self._seconds(public_info.spend_min_time)
        self.max_time_2 = self._seconds(public_info.spend_max_time)
        timing_layout.addRow('题目间隔', self._range(self.min_time, self.max_time))
        timing_layout.addRow('提交用时', self._range(self.min_time_2, self.max_time_2))
        layout.addWidget(timing)
        
        general = QtWidgets.QGroupBox('其他')
        general_layout = QtWidgets.QVBoxLayout(general)
        general_layout.setSpacing(10)
        self.br_checkBox = QtWidgets.QCheckBox('启用 Brotli 压缩（下次登录时生效）')
        self.br_checkBox.setChecked(public_info.br_choices)
        self.playMusicCheckBox = QtWidgets.QCheckBox('任务完成时播放提示音')
        self.playMusicCheckBox.setChecked(public_info.play_music)
        general_layout.addWidget(self.br_checkBox)
        general_layout.addWidget(self.playMusicCheckBox)
        music_row = QtWidgets.QHBoxLayout( )
        self.musicPathLineEdit = QtWidgets.QLineEdit(public_info.music_path)
        self.musicPathLineEdit.setPlaceholderText('使用默认提示音')
        self.selectMusicBtn = QtWidgets.QPushButton('选择文件')
        self.defaultMusicBtn = QtWidgets.QPushButton('恢复默认')
        self.selectMusicBtn.clicked.connect(self.select_music_file)
        self.defaultMusicBtn.clicked.connect(self.musicPathLineEdit.clear)
        music_row.addWidget(self.musicPathLineEdit, 1)
        music_row.addWidget(self.selectMusicBtn)
        music_row.addWidget(self.defaultMusicBtn)
        general_layout.addLayout(music_row)
        layout.addWidget(general)
        
        buttons = QtWidgets.QHBoxLayout( )
        buttons.addStretch( )
        cancel = QtWidgets.QPushButton('取消')
        cancel.clicked.connect(self.reject)
        save = QtWidgets.QPushButton('保存')
        save.setObjectName('primaryButton')
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.adjustSize( )
    
    @staticmethod
    def _seconds(value):
        spin = QtWidgets.QSpinBox( )
        spin.setRange(0, 86400)
        spin.setSuffix(' 秒')
        spin.setValue(value)
        return spin
    
    @staticmethod
    def _range(minimum, maximum):
        row = QtWidgets.QWidget( )
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(minimum)
        layout.addWidget(QtWidgets.QLabel('至'))
        layout.addWidget(maximum)
        return row
    
    def select_music_file(self):
        path = select_file(self, '选择提示音', '', '音频文件 (*.wav)')
        if path:
            self.musicPathLineEdit.setText(path)
    
    def save(self):
        if self.min_time.value( ) > self.max_time.value( ):
            show_warning(self, '无法保存', '最长间隔不能短于最短间隔')
            return
        if self.min_time_2.value( ) > self.max_time_2.value( ):
            show_warning(self, '无法保存', '最长用时不能短于最短用时')
            return
        compressed = self.br_checkBox.isChecked( )
        try:
            self.public_info.input_info(
                    self.min_time.value( ), self.max_time.value( ),
                    self.min_time_2.value( ), self.max_time_2.value( ), compressed,
                    'gzip, deflate, br' if compressed else 'gzip, deflate',
                    self.playMusicCheckBox.isChecked( ), self.musicPathLineEdit.text( ).strip( ),
            )
        except (OSError, ValueError, TypeError) as exc:
            Log('settings').logger.exception('保存设置失败')
            show_error(self, '保存失败', f'无法保存设置：{exc}')
            return
        Log('settings').logger.info('设置已保存')
        self.accept( )
