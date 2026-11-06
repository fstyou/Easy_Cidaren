"""Consistent Chinese labels for application dialogs."""

import os
from typing import cast

from PyQt6 import QtCore
from PyQt6.QtWidgets import QAbstractButton, QFileDialog, QMessageBox

from easy_cidaren.ui.styles import DIALOG_STYLE
from easy_cidaren.ui.theme import manager, themed_palette


def _apply_dialog_style(dialog):
    theme = manager( )
    dialog.setProperty('_theme_managed_dialog', True)
    dialog.setPalette(themed_palette(dialog.palette( ), bool(theme and theme.dark)))
    dialog.setStyleSheet(DIALOG_STYLE + '''
        QLineEdit, QComboBox, QAbstractItemView, QHeaderView::section {
            background: white; color: #263548;
        }
        QAbstractItemView { selection-background-color: #3269bd; selection-color: white; }
        QToolButton { background: #edf2f7; color: #29415f; }
    ''')


def create_message(parent, title, message, icon, button_text = "知道了"):
    dialog = QMessageBox(parent)
    _apply_dialog_style(dialog)
    dialog.setWindowTitle(title)
    dialog.setIcon(icon)
    dialog.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    dialog.setText(str(message))
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    cast(QAbstractButton, dialog.button(QMessageBox.StandardButton.Ok)).setText(button_text)
    dialog.setEscapeButton(QMessageBox.StandardButton.Ok)
    return dialog


def show_information(parent, title, message):
    return _exec_message(create_message(parent, title, message, QMessageBox.Icon.Information))


def show_warning(parent, title, message):
    return _exec_message(create_message(parent, title, message, QMessageBox.Icon.Warning))


def show_error(parent, title, message):
    return _exec_message(create_message(parent, title, message, QMessageBox.Icon.Critical))


def _exec_message(dialog):
    try:
        return dialog.exec( )
    finally:
        dialog.deleteLater( )


def confirm_action(parent, title, message, *, confirm_text, detail = "", default_confirm = False):
    dialog = QMessageBox(parent)
    _apply_dialog_style(dialog)
    dialog.setWindowTitle(title)
    dialog.setIcon(QMessageBox.Icon.Question)
    dialog.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    dialog.setText(str(message))
    if detail:
        dialog.setInformativeText(detail)
    dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    cast(QAbstractButton, dialog.button(QMessageBox.StandardButton.Yes)).setText(confirm_text)
    cast(QAbstractButton, dialog.button(QMessageBox.StandardButton.No)).setText("取消")
    dialog.setEscapeButton(QMessageBox.StandardButton.No)
    dialog.setDefaultButton(QMessageBox.StandardButton.Yes if default_confirm else QMessageBox.StandardButton.No)
    return _exec_message(dialog) == QMessageBox.StandardButton.Yes


def select_file(parent, title, path, name_filter, *, save = False):
    dialog = QFileDialog(parent, title)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
    _apply_dialog_style(dialog)
    if save:
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
    dialog.setNameFilter(name_filter)
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, "保存" if save else "打开")
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
    dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "位置：")
    dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名：")
    dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型：")
    if path:
        dialog.selectFile(path)
    try:
        while dialog.exec( ) == QFileDialog.DialogCode.Accepted:
            selected = dialog.selectedFiles( )[0]
            if not save or not os.path.exists(selected) or confirm_action(
                    parent, "确认覆盖", "该文件已存在，是否覆盖？",
                    confirm_text = "覆盖", detail = selected):
                return selected
        return ""
    finally:
        dialog.deleteLater( )
