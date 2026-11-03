"""About dialog and project links."""

from PyQt6 import QtCore, QtGui, QtWidgets

from easy_cidaren.ui.dialogs import show_warning
from easy_cidaren.ui.styles import DIALOG_STYLE

PROJECT_URL = 'https://github.com/fstyou/Easy_Cidaren'


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, version, parent = None):
        super( ).__init__(parent)
        self.setWindowTitle('关于')
        self.setStyleSheet(DIALOG_STYLE)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        title = QtWidgets.QLabel('Easy Cidaren')
        title.setObjectName('title')
        layout.addWidget(title)
        
        card = QtWidgets.QFrame( )
        card.setObjectName('card')
        content = QtWidgets.QFormLayout(card)
        content.setContentsMargins(12, 14, 12, 14)
        content.setHorizontalSpacing(8)
        content.setVerticalSpacing(12)
        content.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        content.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        content.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        version_label = QtWidgets.QLabel(version)
        license_label = QtWidgets.QLabel('GNU GPL v3')
        project_label = QtWidgets.QLabel(
                f'<a href="{PROJECT_URL}" style="color: #3269bd;">{PROJECT_URL}</a>')
        project_label.setObjectName('projectLink')
        project_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        project_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag(
                QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse.value |
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse.value))
        project_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        project_label.setWordWrap(False)
        project_label.linkActivated.connect(self.open_url)
        for label, value in (('版本', version_label), ('开源协议', license_label), ('项目地址', project_label)):
            heading = QtWidgets.QLabel(label)
            heading.setObjectName('muted')
            content.addRow(heading, value)
        layout.addWidget(card)
        
        buttons = QtWidgets.QHBoxLayout( )
        buttons.addStretch( )
        confirm = QtWidgets.QPushButton('确定')
        confirm.setObjectName('primaryButton')
        confirm.setDefault(True)
        confirm.clicked.connect(self.accept)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        width = max(400, layout.sizeHint( ).width( ), layout.minimumSize( ).width( ))
        self.setFixedWidth(width)
        height = layout.totalHeightForWidth(width) if layout.hasHeightForWidth( ) else layout.sizeHint( ).height( )
        self.setFixedHeight(max(height, layout.minimumSize( ).height( )))
    
    def open_url(self, address):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(address)):
            show_warning(self, '无法打开网页', '请检查系统默认浏览器设置')
