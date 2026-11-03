"""Export a snapshot of the current application log."""

import logging
import os
import shutil


def export_log(source, destination):
    source = os.path.abspath(source)
    loggers = [logging.getLogger( )]
    loggers.extend(logger for logger in logging.Logger.manager.loggerDict.values( )
                   if isinstance(logger, logging.Logger))
    for logger in loggers:
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == source:
                handler.flush( )
    shutil.copyfile(source, destination)
