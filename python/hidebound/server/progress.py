from pathlib import Path

import json

import flask
from hidebound.core.logging import ProgressLogger
# ------------------------------------------------------------------------------


'''
Service used for getting Hidebound app progress.
'''
# TODO: remove this app entirely and replaced with async multiprocess refactoring of db


def get_app():
    # type: () -> flask.Flask
    '''
    Creates a Hidebound progress app.

    Returns:
        Flask: Flask app.
    '''
    app = flask.Flask('hidebound-progress')  # type: flask.Flask
    return app


APP = get_app()


@APP.route('/progress', methods=['GET'])
def create():
    # type: () -> flask.Response
    '''
    Get hidebound app progress.

    Returns:
        Response: Flask Response instance.
    '''
    filepath = Path('/mnt/storage/hidebound/logs/progress/hidebound-progress.log')
    state = {}
    if filepath.is_file():
        state = ProgressLogger.read(filepath)[-1]
    return flask.Response(
        response=json.dumps(state),
        mimetype='application/json'
    )


if __name__ == '__main__':
    APP.run(debug=True, host='0.0.0.0', port=8081)
