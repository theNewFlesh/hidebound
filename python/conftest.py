import logging
import os

from selenium.webdriver.chrome.options import Options
import lunchbox.tools as lbt
import pytest

import hidebound.server.app as app
# ------------------------------------------------------------------------------


CONFIG_PATH = '/tmp/hidebound/hidebound/resources/test_config.json'
if 'REPO_ENV' in os.environ.keys():
    CONFIG_PATH = lbt \
        .relative_path(__file__, '../resources/test_config.json').as_posix()


def pytest_setup_options():
    '''
    Configures Chrome webdriver.
    '''
    options = Options()
    options.add_argument('--no-sandbox')
    return options


@pytest.fixture(scope='function')
def run_app():
    '''
    Pytest fixture used to run hidebound Dash app.
    Sets config_path to resources/test_config.json.
    '''
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(app.APP, CONFIG_PATH, debug=False, test=True)
    yield app.APP, app.APP.client
