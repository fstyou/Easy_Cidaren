"""Application theme selection and system appearance tracking."""

import re

from PyQt6 import QtCore, QtGui, QtWidgets


_DARK_COLORS = {
    '#f4f6f9': '#1e2530', '#ffffff': '#273240', '#dce3ec': '#405267',
    '#263548': '#e1e8f0', '#20344f': '#edf3fa', '#253b57': '#e4edf8',
    '#52657c': '#b2c1d2', '#344b66': '#c7d7e8', '#526b87': '#aec3da',
    '#196b4b': '#79d6a7', '#edf7f1': '#244b3b', '#a73630': '#ff9d98',
    '#fdf0ef': '#572e31', '#855708': '#eec674', '#fcf5e8': '#524222',
    '#cfd9e5': '#506379', '#3971c4': '#76a8f0', '#e5eefb': '#364c68',
    '#f3f6fa': '#303d4d', '#34465d': '#cfdae7', '#edf2f7': '#35465a',
    '#29415f': '#e0ebf7', '#d4deea': '#53677e', '#e1eaf5': '#465c76',
    '#68798e': '#9aabba', '#edf0f4': '#303b48', '#3269bd': '#3978d0',
    '#285aa4': '#4c8de1', '#526984': '#a6b5c8', '#dce5f0': '#36475a',
    '#e3ebf4': '#3b4c60', '#3977cf': '#78aaf1', '#607086': '#adbed1',
    '#f3f7fd': '#303f51', '#e1eaf6': '#465b72', '#315780': '#c7ddf6',
    '#dce7f5': '#43566c', '#edf2f8': '#35465a', '#263d5b': '#e0ebf7',
    '#dce4ee': '#53677e', '#e1ebf8': '#465c76', '#9cabbc': '#98aabc',
    '#30445e': '#d3e0ee', '#65758a': '#a8b9cc',
    '#cbdcf0': '#516982', '#dce8f5': '#465c76',
}


def themed_style(style, dark):
    if not dark:
        return style
    style = re.sub(r'(background(?:-color)?\s*:\s*)white\b', r'\1#273240', style, flags = re.I)

    def replace(match):
        color = match.group(0)
        # White foreground is used on blue buttons and selected rows.
        prefix = style[max(0, match.start( ) - 25):match.start( )]
        if color.lower( ) == '#ffffff' and re.search(r'(?<!background-)color\s*:\s*$', prefix):
            return color
        return _DARK_COLORS.get(color.lower( ), color)

    return re.sub(r'#[0-9a-fA-F]{6}\b', replace, style)


def themed_palette(base, dark):
    palette = QtGui.QPalette(base)
    colors = {
        QtGui.QPalette.ColorRole.Window: '#1e2530' if dark else '#f4f6f9',
        QtGui.QPalette.ColorRole.WindowText: '#e1e8f0' if dark else '#263548',
        QtGui.QPalette.ColorRole.Base: '#273240' if dark else '#ffffff',
        QtGui.QPalette.ColorRole.AlternateBase: '#303d4d' if dark else '#f4f6f9',
        QtGui.QPalette.ColorRole.Text: '#e1e8f0' if dark else '#263548',
        QtGui.QPalette.ColorRole.Button: '#35465a' if dark else '#edf2f7',
        QtGui.QPalette.ColorRole.ButtonText: '#e0ebf7' if dark else '#29415f',
        QtGui.QPalette.ColorRole.Highlight: '#3978d0' if dark else '#3269bd',
        QtGui.QPalette.ColorRole.HighlightedText: '#ffffff',
        QtGui.QPalette.ColorRole.Link: '#8bbcff' if dark else '#3269bd',
        QtGui.QPalette.ColorRole.ToolTipBase: '#273240' if dark else '#ffffff',
        QtGui.QPalette.ColorRole.ToolTipText: '#e1e8f0' if dark else '#263548',
    }
    for role, color in colors.items( ):
        palette.setColor(role, QtGui.QColor(color))
    return palette


class ThemeManager(QtCore.QObject):
    changed = QtCore.pyqtSignal(bool)

    def __init__(self, app, mode = 'system'):
        super( ).__init__(app)
        self.app = app
        self.mode = mode if mode in ('system', 'light', 'dark') else 'system'
        self.system_palette = QtGui.QPalette(app.palette( ))
        self.dark = False
        self._updating = False
        app.installEventFilter(self)
        hints = app.styleHints( )
        hints.colorSchemeChanged.connect(self._system_changed)
        self.apply( )

    def _system_changed(self, *_args):
        if self.mode == 'system':
            self.apply( )

    def set_mode(self, mode):
        self.mode = mode if mode in ('system', 'light', 'dark') else 'system'
        self.apply( )

    def apply(self):
        scheme = self.app.styleHints( ).colorScheme( )
        system_dark = (scheme == QtCore.Qt.ColorScheme.Dark or
                       (scheme == QtCore.Qt.ColorScheme.Unknown and
                        self.system_palette.color(QtGui.QPalette.ColorRole.Window).lightness( ) < 128))
        self.dark = self.mode == 'dark' or (self.mode == 'system' and system_dark)
        palette = themed_palette(self.system_palette, self.dark)
        self.app.setPalette(palette)
        self._updating = True
        try:
            for widget in self.app.allWidgets( ):
                if widget.property('_theme_managed_dialog'):
                    widget.setPalette(palette)
                self._style_widget(widget)
        finally:
            self._updating = False
        self.changed.emit(self.dark)

    def _style_widget(self, widget):
        style = widget.styleSheet( )
        previous = widget.property('_theme_applied')
        original = widget.property('_theme_original')
        if original is None or (style != previous and style != original):
            original = style
            widget.setProperty('_theme_original', original)
        themed = themed_style(original, self.dark)
        widget.setProperty('_theme_applied', themed)
        if style != themed:
            widget.setStyleSheet(themed)

    def eventFilter(self, a0: QtCore.QObject | None, a1: QtCore.QEvent | None) -> bool:
        if (not self._updating and a1 is not None
                and a1.type( ) in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.StyleChange)
                and isinstance(a0, QtWidgets.QWidget)):
            self._updating = True
            try:
                self._style_widget(a0)
            finally:
                self._updating = False
        return False


def manager( ) -> ThemeManager | None:
    app = QtWidgets.QApplication.instance( )
    return app.findChild(ThemeManager) if app else None
