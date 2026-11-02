"""Readable console formatting and configurable log levels."""

import copy
import logging

CONSOLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
FILE_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_CONSOLE_MESSAGE = 400


def console_level(value):
    """Use DEBUG by default; invalid values do not disable diagnostics."""
    return {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }.get((value or '').strip( ).upper( ), logging.DEBUG)


class ConsoleFilter(logging.Filter):
    def filter(self, record):
        return not getattr(record, 'file_only', False)


class ConsoleFormatter(logging.Formatter):
    def __init__(self):
        super( ).__init__(CONSOLE_FORMAT, datefmt = DATE_FORMAT)
    
    def format(self, record):
        # Do not truncate errors or mutate the record used by the file handler.
        if record.levelno < logging.WARNING:
            message = record.getMessage( )
            if len(message) > MAX_CONSOLE_MESSAGE:
                record = copy.copy(record)
                record.msg = message[:MAX_CONSOLE_MESSAGE] + '…（内容过长，详见日志文件）'
                record.args = ()
        return super( ).format(record)
