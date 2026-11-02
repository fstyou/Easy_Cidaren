"""Initialize and run the application."""
import sys

from PyQt6.QtWidgets import QApplication

from easy_cidaren.core.public_info import PublicInfo
from easy_cidaren.logging.config import Log
from easy_cidaren.ui.main_window import UiMainWindow
from easy_cidaren.ui.task_worker import TaskWorker


def main( ):
    logger = Log("main")
    logger.info("初始化主页面")
    app = QApplication(sys.argv)
    try:
        public_info = PublicInfo( )
        logger.info(f"当前版本号：{public_info.version}")
        window = UiMainWindow(public_info, logger, TaskWorker)
        window.show( )
        return app.exec( )
    except Exception:
        logger.logger.exception("程序异常")
        from easy_cidaren.ui.error_dialog import ErrorDialog
        window = ErrorDialog( )
        window.show( )
        return app.exec( )
