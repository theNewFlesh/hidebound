import json
import os

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash
import flasgger as swg
import flask

import hidebound.server.api as api
import hidebound.server.components as components
import hidebound.server.server_tools as server_tools
# ------------------------------------------------------------------------------


'''
Hidebound service used for displaying and interacting with Hidebound database.
'''


APP = flask.Flask(__name__)
swg.Swagger(APP)
APP.register_blueprint(api.API)
APP = components.get_dash_app(APP)
CONFIG_PATH = None


@APP.server.route('/static/<stylesheet>')
def serve_stylesheet(stylesheet):
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
        Input('delete-button', 'n_clicks'),
        Input('search-button', 'n_clicks'),
        Input('dropdown', 'value'),
        Input('query', 'value'),
        Input('upload', 'contents'),
        Input('validate-button', 'n_clicks'),
        Input('write-button', 'n_clicks'),
    ],
    [State('store', 'data')]
)
def on_event(*inputs):
    '''
    Update Hidebound database instance, and updates store with input data.

    Args:
        inputs (tuple): Input elements.

    Returns:
        dict: Store data.
    '''
    store = inputs[-1] or {}
    config = store.get('config', api.CONFIG)
    conf = json.dumps(config)

    context = dash.callback_context
    inputs = {}
    for item in context.inputs_list:
        key = item['id']
        val = None
        if 'value' in item.keys():
            val = item['value']
        inputs[key] = val

    # convert search dropdown to boolean
    grp = False
    if inputs['dropdown'] == 'asset':
        grp = True
    inputs['dropdown'] = grp

    input_id = context.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'init-button':
        APP.server.test_client().post('/api/initialize', json=conf)

    elif input_id == 'update-button':
        if api.DATABASE is None:
            APP.server.test_client().post('/api/initialize', json=conf)

        APP.server.test_client().post('/api/update')

        params = json.dumps({'group_by_asset': grp})
        response = APP.server.test_client().post('/api/read', json=params).json
        store['/api/read'] = response

    elif input_id == 'create-button':
        APP.server.test_client().post('/api/create')

    elif input_id == 'delete-button':
        APP.server.test_client().post('/api/delete')

    elif input_id == 'search-button':
        query = json.dumps({
            'query': inputs['query'],
            'group_by_asset': inputs['dropdown']
        })
        response = APP.server.test_client().post('/api/search', json=query).json
        store['/api/read'] = response

    elif input_id == 'upload':
        try:
            store['config'] = server_tools.parse_json_file_content(inputs['upload'])
        except Exception as error:
            store['config'] = server_tools.error_to_response(error).json

    elif input_id == 'validate-button':
        pass

    elif input_id == 'write-button':
        pass

    return store


@APP.callback(
    Output('table-content', 'children'),
    [Input('store', 'data')]
)
def on_datatable_update(store):
    '''
    Updates datatable with read information from store.

    Args:
        store (dict): Store data.

    Returns:
        DataTable: Dash DataTable.
    '''
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
    '''
    Serve content for app tabs.

    Args:
        tab (str): Name of tab to render.
        store (dict): Store.

    Returns:
        flask.Response: Response.
    '''
    if tab == 'data':
        return components.get_data_tab()
    elif tab == 'config':
        store = store or {}
        config = store.get('config', api.CONFIG)
        return components.get_config_tab(config)


@APP.callback(
    Output('json-editor-row', 'children'),
    [Input('store', 'data')]
)
def on_json_editor_update(store):
    '''
    Updates JSON editor with config information from store.

    Args:
        store (dict): Store data.

    Returns:
        flask.Response: Response.
    '''
    if store in [{}, None]:
        raise PreventUpdate
    config = store.get('config', None)
    if config is None:
        raise PreventUpdate
    return components.get_json_editor(config)
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    debug = 'DEBUG_MODE' in os.environ.keys()
    if debug:
        config, config_path = server_tools\
            .setup_hidebound_directory(
                '/tmp',
                config_path='/root/hidebound/resources/test_config.json'
            )
    else:
        config, config_path = server_tools\
            .setup_hidebound_directory('/mnt/storage')
    api.CONFIG = config
    CONFIG_PATH = config_path
    APP.run_server(debug=debug, host='0.0.0.0', port=5000)
