"""About dialog and project links."""

from PyQt6 import QtCore, QtGui, QtWidgets

from easy_cidaren.api.device import get_uuid
from easy_cidaren.ui.dialogs import show_information, show_warning
from easy_cidaren.ui.styles import DIALOG_STYLE

PROJECT_URL = 'https://github.com/fstyou/Easy_Cidaren'


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, version, parent = None):
        super( ).__init__(parent)
        self.setWindowTitle('关于')
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_STYLE)
        device_id = get_uuid( )
        self.info_text = (f'Easy Cidaren\n版本：{version}\n开源协议：GNU GPL v3\n'
                          f'项目地址：{PROJECT_URL}\n设备 ID：{device_id}')
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        title = QtWidgets.QLabel('关于 Easy Cidaren')
        title.setObjectName('title')
        layout.addWidget(title)
        
        card = QtWidgets.QFrame( )
        card.setObjectName('card')
        content = QtWidgets.QVBoxLayout(card)
        content.setContentsMargins(16, 14, 16, 14)
        content.setSpacing(10)
        version_label = QtWidgets.QLabel(f'版本  {version}')
        license_label = QtWidgets.QLabel('开源协议  GNU GPL v3')
        project_label = QtWidgets.QLabel(
                f'项目地址  <a href="{PROJECT_URL}" style="color: #3269bd;">{PROJECT_URL}</a>')
        project_label.setObjectName('projectLink')
        project_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        project_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse |
                                              QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        project_label.setWordWrap(True)
        project_label.linkActivated.connect(self.open_url)
        device_label = QtWidgets.QLabel(f'设备 ID  {device_id}')
        device_label.setObjectName('muted')
        device_label.setWordWrap(True)
        device_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        for label in (version_label, license_label, project_label, device_label):
            content.addWidget(label)
        layout.addWidget(card)
        
        buttons = QtWidgets.QHBoxLayout( )
        buttons.addStretch( )
        copy = QtWidgets.QPushButton('复制信息')
        copy.clicked.connect(self.copy_info)
        confirm = QtWidgets.QPushButton('确定')
        confirm.setObjectName('primaryButton')
        confirm.setDefault(True)
        confirm.clicked.connect(self.accept)
        buttons.addWidget(copy)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        self.adjustSize( )
    
    def open_url(self, address):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(address)):
            show_warning(self, '无法打开网页', '请检查系统默认浏览器设置。')
    
    def copy_info(self):
        QtWidgets.QApplication.clipboard( ).setText(self.info_text)
        show_information(self, '复制成功', '已将相关信息复制到剪贴板')
