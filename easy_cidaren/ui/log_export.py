"""User interaction for exporting the current log."""

import logging
import shutil
from pathlib import Path

from easy_cidaren.app_logging.config import log_filename
from easy_cidaren.app_logging.export import export_log
from easy_cidaren.ui.dialogs import select_file, show_error, show_information


def export_logs(parent):
    default_path = str(Path.home( ) / Path(log_filename).name)
    destination = select_file(parent, "导出日志", default_path,
                              "日志文件 (*.log);;所有文件 (*)", save = True)
    if not destination:
        return
    logger = logging.getLogger(__name__)
    try:
        export_log(log_filename, destination)
    except (OSError, shutil.Error) as exc:
        logger.exception("导出日志失败")
        show_error(parent, "导出失败", f"无法导出日志：{exc}")
        return
    logger.info("日志已导出到 %s", destination)
    show_information(parent, "导出成功", f"日志已保存至：\n{destination}")
