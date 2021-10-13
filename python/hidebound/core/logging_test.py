import unittest
import logging
import json
from tempfile import TemporaryDirectory
from pathlib import Path

from hidebound.core.logging import ProgressLogger
# ------------------------------------------------------------------------------


class ProgressLoggerTests(unittest.TestCase):
    def test_init(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            result = ProgressLogger('foobar', filepath)
            self.assertEqual(result._filepath, filepath)

    def test_get_logger(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log')
            logger = ProgressLogger._get_logger('foobar', filepath)
            expected = 'Some message'
            logger.info(expected)

            # log exists
            self.assertTrue(filepath.is_file())

            # log content
            result = ProgressLogger.read(filepath)[0]['message']
            self.assertEqual(result, expected)

    def test_get_logger_props(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log')
            logger = ProgressLogger._get_logger('foobar', filepath)
            logger.info('foobar')
            logger.info('foobar', extra=dict(props=dict(step=1, total=10)))
            logger.info('foobar', extra=dict(props=dict(step=1, total=None)))
            logger.info('foobar', extra=dict(props=dict(step=None, total=10)))

            results = ProgressLogger.read(filepath)

            # no props
            lut = dict(
                message='foobar',
                original_message='foobar',
                step=None,
                total=None,
                progress=None
            )
            for key, val in lut.items():
                self.assertEqual(results[0][key], val)

            # step and total
            lut = dict(
                message='Progress: 10.00% (1 of 10) - foobar',
                original_message='foobar',
                step=1,
                total=10,
                progress=0.1,
            )
            for key, val in lut.items():
                self.assertEqual(results[1][key], val)

            # step
            lut = dict(
                message='foobar',
                original_message='foobar',
                step=1,
                total=None,
                progress=None
            )
            for key, val in lut.items():
                self.assertEqual(results[2][key], val)

            # total
            lut = dict(
                message='foobar',
                original_message='foobar',
                step=None,
                total=10,
                progress=None
            )
            for key, val in lut.items():
                self.assertEqual(results[3][key], val)

    def test_read(self):
        expected = [dict(foo='bar', i=i) for i in range(3)]
        with TemporaryDirectory() as root:
            log = Path(root, 'test.log')
            with open(log, 'w') as f:
                for line in expected:
                    f.write(json.dumps(line) + '\n')

            result = ProgressLogger.read(log)
            self.assertEqual(result, expected)

    def test_filepath(self):
        with TemporaryDirectory() as root:
            expected = Path(root, 'test.log').as_posix()
            result = ProgressLogger('foobar', expected).filepath
            self.assertEqual(result, expected)

    def test_logs(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('foobar', filepath)
            logger.info('a')
            logger.info('b')
            logger.info('c')
            result = len(logger.logs)
            self.assertEqual(result, 3)

    def test_log(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath)
            logger.log(logging.ERROR, 'foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'ERROR')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_info(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.INFO)
            logger.info('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'INFO')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_warning(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.WARNING)
            logger.warning('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'WARNING')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_error(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.ERROR)
            logger.error('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'ERROR')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_debug(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.DEBUG)
            logger.debug('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'DEBUG')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_fatal(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.FATAL)
            logger.fatal('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'CRITICAL')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)

    def test_critical(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.log').as_posix()
            logger = ProgressLogger('test', filepath, level=logging.CRITICAL)
            logger.critical('foobar', step=4, total=100)
            result = logger.logs[0]

            # level
            self.assertEqual(result['level_name'], 'CRITICAL')

            # message
            expected = 'Progress: 4.00% (4 of 100) - foobar'
            self.assertEqual(result['message'], expected)
