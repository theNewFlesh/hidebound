from typing import Any, Dict, List, Tuple, Union

import os

from dash import dash_table, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash
import flask
from flask import current_app
import flask_monitoringdashboard as fmdb

from hidebound.core.config import Config
import hidebound.core.tools as hbt
import hidebound.server.components as components
import hidebound.server.extensions as ext
import hidebound.server.server_tools as hst


TESTING = True
if __name__ == '__main__':
    TESTING = False  # pragma: no cover

# setup directories in /tmp/mnt
if hbt.str_to_bool(os.environ.get('CREATE_TMP_DIRS', 'False')):
    hst.setup_hidebound_directories('/tmp/mnt')
# ------------------------------------------------------------------------------


'''
Hidebound service used for displaying and interacting with Hidebound database.
'''


EP = hst.EndPoints()


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

    app = components.get_dash_app(app, seconds=0.8)
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
    content = hst.render_template(stylesheet + '.j2', params)
    return flask.Response(content, mimetype='text/css')


# EVENTS------------------------------------------------------------------------
# TODO: Find a way to test events.
@APP.callback(
    output=Output('store', 'data'),
    inputs=[
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
    state=[State('store', 'data')],
    prevent_initial_call=True,
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

    # get context values
    context = dash.callback_context
    store = context.states['store.data'] or {}  # type: dict
    trigger = context.triggered_id
    value = context.triggered[0]['value']
    query = context.inputs['query.value']
    group_by_asset = context.inputs['dropdown.value'] == 'asset'

    if trigger == 'init-button':
        hst.request(store, EP.update, store.get('config', hb.config))

    elif trigger == 'update-button':
        hst.request(store, EP.update)
        store = hst.search(store, query, group_by_asset)

    elif trigger == 'create-button':
        hst.request(store, EP.create)

    elif trigger == 'export-button':
        hst.request(store, EP.export)

    elif trigger == 'delete-button':
        hst.request(store, EP.delete)

    elif trigger == 'search-button':
        store = hst.search(store, query, group_by_asset)

    elif trigger == 'upload':
        temp = 'invalid'  # type: Any
        try:
            temp = hst.parse_json_file_content(value)
            Config(temp).validate()
            store['config'] = temp
            store['config_error'] = None
        except Exception as error:
            store['config'] = temp
            store['config_error'] = hst.error_to_response(error).json()  # type: ignore

    # elif input_id == 'write-button':
    #     try:
    #         config = store['config']
    #         Config(config).validate()
    #         with open(CONFIG_PATH, 'w') as f:  # type: ignore
    #             json.dump(config, f, indent=4, sort_keys=True)
    #         store['config_error'] = None
    #     except Exception as error:
    #         store['config_error'] = hst.error_to_response(error).json

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
    data = store.get('content', None)
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
        data = store.get('content', None)
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


@APP.callback(
    Output('progressbar-container', 'children'),
    [Input('clock', 'n_intervals')],
)
def on_progress(timestamp):
    # type: (int) -> flask.Response
    '''
    Updates progressbar.

    Args:
        timestamp (int): Store modification timestamp.

    Returns:
        flask.Response: Response.
    '''
    return components.get_progressbar(hst.get_progress())
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    debug = 'DEBUG_MODE' in os.environ.keys()
    APP.run_server(debug=debug, host=EP.host, port=EP.port)
