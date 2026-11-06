import datetime
import glob
import logging
import os

from easy_cidaren.app_logging.format import ConsoleFilter, ConsoleFormatter, DATE_FORMAT, FILE_FORMAT, console_level
from easy_cidaren.paths import LOG_DIR

# 创建logs目录（如果不存在）
log_dir = str(LOG_DIR)
os.makedirs(log_dir, exist_ok = True)


# 清理旧的日志文件，只保留最近的200个
def clean_old_logs( ):
    log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
    log_files.sort(key = os.path.getmtime, reverse = True)
    for old_file in log_files[200:]:
        try:
            os.remove(old_file)
        except OSError:
            pass  # 如果删除失败，忽略错误


# 执行清理操作
clean_old_logs( )

# 生成带时间戳的日志文件名
timestamp = datetime.datetime.now( ).strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(log_dir, f"app_{timestamp}.log")


def setup_logger( ):
    """
    配置日志格式和处理器
    """
    logger_instance = logging.getLogger( )
    logger_instance.setLevel(logging.DEBUG)
    
    # 只替换本项目的处理器，避免影响宿主或其他库的日志配置
    for handler in logger_instance.handlers[:]:
        if handler.name in ('easy_cidaren.file', 'easy_cidaren.console'):
            logger_instance.removeHandler(handler)
            handler.close( )
    
    formatter = logging.Formatter(
            FILE_FORMAT, datefmt = DATE_FORMAT
    )
    
    file_handler = logging.FileHandler(log_filename, encoding = "utf-8")
    file_handler.name = 'easy_cidaren.file'
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger_instance.addHandler(file_handler)
    
    console_handler = logging.StreamHandler( )
    console_handler.name = 'easy_cidaren.console'
    console_handler.setLevel(console_level(os.environ.get('EASY_CIDAREN_LOG_LEVEL')))
    console_handler.addFilter(ConsoleFilter( ))
    console_handler.setFormatter(ConsoleFormatter( ))
    logger_instance.addHandler(console_handler)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


# 初始化日志
setup_logger( )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
