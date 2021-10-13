from typing import Any, List, Optional, Union

from datetime import datetime
from pathlib import Path
import json
import logging
import logging.handlers
import os

import json_logging
# ------------------------------------------------------------------------------


class ProgressLogger:
    '''
    Logs progress to quasi-JSON files.
    '''
    def __init__(self, name, filepath, level=logging.INFO):
        # type: (str, Union[str, Path], int) -> None
        '''
        Create ProgressLogger instance.

        Args:
            name (str): Logger name.
            filepath (str or Path): Log filepath.
            level (int, optional): Log level. Default: INFO.
        '''
        filepath = Path(filepath)
        os.makedirs(filepath.parent, exist_ok=True)
        filepath = filepath.as_posix()
        self._filepath = filepath
        self._logger = self._get_logger(name, filepath, level=level)

    @staticmethod
    def _get_logger(name, filepath, level=logging.INFO):
        # type: (str, Union[str, Path], int) -> logging.Logger
        '''
        Creates a JSON logger.

        Args:
            name (str): Name of logger.
            filepath (str or Path): Filepath of JSON log.
            level (int, optional): Log level. Default: INFO.

        Returns:
            Logger: JSON logger.
        '''
        class Formatter(json_logging.JSONLogFormatter):
            def format(self, record):
                # get progress numbers
                progress = None
                step = None
                total = None
                if hasattr(record, 'props') and isinstance(record.props, dict):
                    step = record.props.get('step', None)
                    total = record.props.get('total', None)

                message = record.getMessage()
                orig = message
                if step is not None and total is not None:
                    progress = float(step) / total
                    pct = progress * 100
                    message = f'Progress: {pct:.2f}% ({step} of {total})'
                    message += f' - {orig}'

                log = dict(
                    args=record.args,
                    created=record.created,
                    exc_info=record.exc_info,
                    exc_text=record.exc_text,
                    message=message,
                    level_name=record.levelname,
                    level_number=record.levelno,
                    msecs=record.msecs,
                    original_message=orig,
                    name=record.name,
                    process=record.process,
                    process_name=record.processName,
                    relative_created=record.relativeCreated,
                    stack_info=record.stack_info,
                    thread=record.thread,
                    thread_name=record.threadName,
                    timestamp=datetime.fromtimestamp(record.created).isoformat(),
                    progress=progress,
                    step=step,
                    total=total,
                )
                return json.dumps(log)

        json_logging.init_non_web(enable_json=True, custom_formatter=Formatter)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            encoding='utf-8',
            maxBytes=10 * 2**10,
            backupCount=10,
        )
        logger.addHandler(handler)
        return logger

    @staticmethod
    def read(filepath):
        # type: (Union[str, Path]) -> List[dict]
        '''
        Read a given progress log file.

        Args:
            filepath (str or Path): Log path.

        Returns:
            list[dict]: Logs.
        '''
        with open(filepath) as f:
            log = list(map(json.loads, f.readlines()))
        return log

    @property
    def filepath(self):
        # type: () -> str
        '''
        str: Filepath of progress log.
        '''
        return self._filepath

    @property
    def logs(self):
        # type: () -> List[dict]
        '''
        list[dict]: Logs read from filepath.
        '''
        return self.read(self.filepath)

    def log(self, level, message, step=None, total=None, **kwargs):
        # type: (int, str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with given level.

        Args:
            level (int): Log level.
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self._logger.log(
            level,
            message,
            extra=dict(props=dict(step=step, total=total)),
            **kwargs,
        )

    def info(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with INFO log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.INFO, message, step=step, total=total, **kwargs)

    def warning(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with WARNING log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.WARNING, message, step=step, total=total, **kwargs)

    def error(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with ERROR log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.ERROR, message, step=step, total=total, **kwargs)

    def debug(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with DEBUG log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.DEBUG, message, step=step, total=total, **kwargs)

    def fatal(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with FATAL log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.FATAL, message, step=step, total=total, **kwargs)

    def critical(self, message, step=None, total=None, **kwargs):
        # type: (str, Optional[int], Optional[int], Any) -> None
        '''
        Log given message with CRITICAL log level.

        Args:
            message (str): Log message.
            step (int, optional): Step in progress. Default: None.
            total (int, optional): Total number of steps. Default: None.
        '''
        self.log(logging.CRITICAL, message, step=step, total=total, **kwargs)
