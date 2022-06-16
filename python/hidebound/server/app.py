from typing import Any, Dict, List, Tuple, Union

from collections import namedtuple
import json
import os

from dash import dash_table, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash
import flask
from flask import current_app
import flask_monitoringdashboard as fmdb
import requests

from hidebound.core.config import Config
import hidebound.server.components as components
import hidebound.server.extensions as ext
import hidebound.server.server_tools as server_tools


TESTING = True
if __name__ == '__main__':
    TESTING = False  # pragma: no cover
# ------------------------------------------------------------------------------


'''
Hidebound service used for displaying and interacting with Hidebound database.
'''


HOST = '0.0.0.0'
PORT = 8080
Endpoints = namedtuple(
    'Endpoints',
    ['api', 'init', 'update', 'create', 'export', 'delete', 'read', 'search'],
)
EP = Endpoints(
    api=f'http://{HOST}:{PORT}/api',
    init=f'http://{HOST}:{PORT}/api/initialize',
    update=f'http://{HOST}:{PORT}/api/update',
    create=f'http://{HOST}:{PORT}/api/create',
    export=f'http://{HOST}:{PORT}/api/export',
    delete=f'http://{HOST}:{PORT}/api/delete',
    read=f'http://{HOST}:{PORT}/api/read',
    search=f'http://{HOST}:{PORT}/api/search',
)


def liveness():
    # type: () -> None
    '''Liveness probe for kubernetes.'''
    pass


def readiness():
    # type: () -> None
    '''
    Readiness probe for kubernetes.
    '''
    pass


def get_app(testing=False):
    # type: (bool) -> dash.Dash
    '''
    Creates a Hidebound app.

    Returns:
        Dash: Dash app.
    '''
    app = flask.Flask('hidebound')  # type: Union[flask.Flask, dash.Dash]
    app.config.update(
        TESTING=testing,
        HEALTHZ=dict(
            live=liveness,
            ready=readiness,
        )
    )

    ext.swagger.init_app(app)
    ext.hidebound.init_app(app)
    ext.healthz.init_app(app)

    # flask monitoring
    fmdb.config.link = 'monitor'
    fmdb.config.monitor_level = 3
    fmdb.config.git = 'https://theNewFlesh.github.io/hidebound/'
    fmdb.bind(app)

    app = components.get_dash_app(app)
    return app


APP = get_app(testing=TESTING)


@APP.server.route('/static/<stylesheet>')
def serve_stylesheet(stylesheet):
    # type: (str) -> flask.Response
    '''
    Serve stylesheet to app.

    Args:
        stylesheet (str): stylesheet filename.

    Returns:
        flask.Response: Response.
    '''
    params = dict(
        COLOR_SCHEME=components.COLOR_SCHEME,
        FONT_FAMILY=components.FONT_FAMILY,
    )
    content = server_tools.render_template(stylesheet + '.j2', params)
    return flask.Response(content, mimetype='text/css')


# EVENTS------------------------------------------------------------------------
# TODO: Find a way to test events.
@APP.callback(
    Output('store', 'data'),
    [
        Input('init-button', 'n_clicks'),
        Input('update-button', 'n_clicks'),
        Input('create-button', 'n_clicks'),
        Input('export-button', 'n_clicks'),
        Input('delete-button', 'n_clicks'),
        Input('search-button', 'n_clicks'),
        Input('dropdown', 'value'),
        Input('query', 'value'),
        Input('upload', 'contents'),
        Input('write-button', 'n_clicks'),
    ],
    [State('store', 'data')]
)
def on_event(*inputs):
    # type: (Tuple[Any, ...]) -> Dict[str, Any]
    '''
    Update Hidebound database instance, and updates store with input data.

    Args:
        inputs (tuple): Input elements.

    Returns:
        dict: Store data.
    '''
    APP.logger.debug(f'on_event called with inputs: {str(inputs)[:50]}')
    hb = current_app.extensions['hidebound']

    store = inputs[-1] or {}  # type: Any
    config = store.get('config', hb.config)  # type: Dict
    conf = json.dumps(config)

    context = dash.callback_context
    inputs_ = {}
    for item in context.inputs_list:
        key = item['id']
        val = None
        if 'value' in item.keys():
            val = item['value']
        inputs_[key] = val

    # convert search dropdown to boolean
    grp = False
    if inputs_['dropdown'] == 'asset':
        grp = True
    inputs_['dropdown'] = grp

    input_id = context.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'init-button':
        response = requests.post(EP.init, json=conf).json()
        if 'error' in response.keys():
            store['/api/read'] = response

    elif input_id == 'update-button':
        if hb.database is None:
            response = requests.post(EP.init, json=conf).json()
            if 'error' in response.keys():
                store['/api/read'] = response

        requests.post(EP.update)

        params = json.dumps({'group_by_asset': grp})
        response = requests.post(EP.read, json=params).json()
        store['/api/read'] = response

    elif input_id == 'create-button':
        requests.post(EP.create)

    elif input_id == 'export-button':
        response = requests.post(EP.export)
        code = response.status_code
        if code < 200 or code >= 300:
            store['/api/read'] = response.json

    elif input_id == 'delete-button':
        requests.post(EP.delete)

    elif input_id == 'search-button':
        query = json.dumps({
            'query': inputs_['query'],
            'group_by_asset': inputs_['dropdown']
        })
        response = requests.post(EP.search, json=query).json()
        store['/api/read'] = response
        store['query'] = inputs_['query']

    elif input_id == 'upload':
        temp = 'invalid'  # type: Any
        try:
            upload = inputs_['upload']  # type: Any
            temp = server_tools.parse_json_file_content(upload)
            Config(temp).validate()
            store['config'] = temp
            store['config_error'] = None
        except Exception as error:
            response = server_tools.error_to_response(error)
            store['config'] = temp
            store['config_error'] = server_tools.error_to_response(error).json

    # elif input_id == 'write-button':
    #     try:
    #         config = store['config']
    #         Config(config).validate()
    #         with open(CONFIG_PATH, 'w') as f:  # type: ignore
    #             json.dump(config, f, indent=4, sort_keys=True)
    #         store['config_error'] = None
    #     except Exception as error:
    #         store['config_error'] = server_tools.error_to_response(error).json

    return store


@APP.callback(
    Output('table-content', 'children'),
    [Input('store', 'data')]
)
def on_datatable_update(store):
    # type: (Dict) -> dash_table.DataTable
    '''
    Updates datatable with read information from store.

    Args:
        store (dict): Store data.

    Returns:
        DataTable: Dash DataTable.
    '''
    APP.logger.debug(
        f'on_datatable_update called with store: {str(store)[:50]}'
    )

    if store in [{}, None]:
        raise PreventUpdate
    data = store.get('/api/read', None)
    if data is None:
        raise PreventUpdate

    if 'error' in data.keys():
        return components.get_key_value_card(data, header='error', id_='error')
    return components.get_datatable(data['response'])


@APP.callback(
    Output('content', 'children'),
    [Input('tabs', 'value')],
    [State('store', 'data')]
)
def on_get_tab(tab, store):
    # type: (str, Dict) -> Union[flask.Response, List, None]
    '''
    Serve content for app tabs.

    Args:
        tab (str): Name of tab to render.
        store (dict): Store.

    Returns:
        flask.Response: Response.
    '''
    hb = current_app.extensions['hidebound']

    APP.logger.debug(
        f'on_get_tab called with tab: {tab} and store: {str(store)[:50]}'
    )
    store = store or {}

    if tab == 'data':
        query = store.get('query', None)
        return components.get_data_tab(query)

    elif tab == 'graph':
        data = store.get('/api/read', None)
        if data is None:
            return None

        if 'error' in data.keys():
            return components.get_key_value_card(
                data, header='error', id_='error'
            )
        return components.get_asset_graph(data['response'])

    elif tab == 'config':
        config = store.get('config', hb.config)
        return components.get_config_tab(config)

    elif tab == 'api':
        return dcc.Location(id='api', pathname='/api')

    elif tab == 'docs':
        return dcc.Location(
            id='docs',
            href='https://thenewflesh.github.io/hidebound'
        )


@APP.callback(
    Output('config-content', 'children'),
    [Input('store', 'modified_timestamp')],
    [State('store', 'data')]
)
def on_config_card_update(timestamp, store):
    # type: (int, Dict[str, Any]) -> flask.Response
    '''
    Updates config card with config information from store.

    Args:
        timestamp (int): Store modification timestamp.
        store (dict): Store data.

    Returns:
        flask.Response: Response.
    '''
    if store in [{}, None]:
        raise PreventUpdate

    config = store.get('config', None)
    if config is None:
        raise PreventUpdate

    if config == 'invalid':
        config = {}

    error = store.get('config_error', None)

    output = components.get_key_value_card(config, 'config', 'config-card')
    if error is not None:
        output = [
            output,
            html.Div(className='row-spacer'),
            components.get_key_value_card(error, 'error', 'error')
        ]

    msg = 'on_config_card_update called with'
    msg += f'config: {config} and error: {str(error)[:50]}'
    APP.logger.debug(msg)
    return output
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    debug = 'DEBUG_MODE' in os.environ.keys()
    APP.run_server(debug=debug, host=HOST, port=PORT)
