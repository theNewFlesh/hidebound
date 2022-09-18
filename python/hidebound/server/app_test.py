import os

import dash
import pytest

import hidebound.server.app as application
import hidebound.server.components as components
import hidebound.server.server_tools as hst
# ------------------------------------------------------------------------------


def test_liveness(app_setup, client):
    result = client.get('/healthz/live').status_code
    assert result == 200


def test_readiness(app_setup, client):
    result = client.get('/healthz/ready').status_code
    assert result == 200


@pytest.mark.skipif('SKIP_SLOW_TESTS' in os.environ, reason='slow test')
def test_get_app(app_setup, client):
    result = application.get_app(testing=True)
    assert isinstance(result, dash.Dash)


def test_serve_stylesheet(app_setup, client):
    params = dict(
        COLOR_SCHEME=components.COLOR_SCHEME,
        FONT_FAMILY=components.FONT_FAMILY,
    )
    expected = hst.render_template('style.css.j2', params)
    result = next(client.get('/static/style.css').response)
    assert result == expected
