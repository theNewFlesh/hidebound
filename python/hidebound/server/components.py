from typing import Any, Dict, List, Optional
import flask

import re

from pandas import DataFrame
import dash
from dash import dash_table, dcc, html
import dash_cytoscape as cyto
import rolling_pin.blob_etl as blob_etl
# ------------------------------------------------------------------------------


COLOR_SCHEME = dict(
    dark1='#040404',
    dark2='#141414',
    bg='#181818',
    grey1='#242424',
    grey2='#444444',
    light1='#A4A4A4',
    light2='#F4F4F4',
    dialog1='#444459',
    dialog2='#5D5D7A',
    red1='#F77E70',
    red2='#DE958E',
    orange1='#EB9E58',
    orange2='#EBB483',
    yellow1='#E8EA7E',
    yellow2='#E9EABE',
    green1='#8BD155',
    green2='#A0D17B',
    cyan1='#7EC4CF',
    cyan2='#B6ECF3',
    blue1='#5F95DE',
    blue2='#93B6E6',
    purple1='#C98FDE',
    purple2='#AC92DE',
)  # type: Dict[str, str]
COLORS = [
    'cyan1',
    'red1',
    'green1',
    'blue1',
    'purple1',
    'orange1',
    'yellow1',
    'light1',
    'cyan2',
    'red2',
    'blue2',
    'green2',
]  # type: List[str]
FONT_FAMILY = 'sans-serif, "sans serif"'  # type: str


# APP---------------------------------------------------------------------------
def get_dash_app(server, storage_type='memory'):
    # type: (flask.Flask, str) -> dash.Dash
    '''
    Generate Dash Flask app instance.

    Args:
        server (Flask): Flask instance.
        storage_type (str): Storage type (used for testing). Default: memory.

    Returns:
        Dash: Dash app instance.
    '''
    store = dcc.Store(id='store', storage_type=storage_type)

    tab_style = {
        'padding': '4px',
        'background': COLOR_SCHEME['bg'],
        'color': COLOR_SCHEME['light1'],
        'border': '0px',
    }
    tab_selected_style = {
        'padding': '4px',
        'background': COLOR_SCHEME['grey1'],
        'color': COLOR_SCHEME['cyan2'],
        'border': '0px',
    }
    tabs = dcc.Tabs(
        id='tabs',
        className='tabs',
        value='data',
        children=[
            dcc.Tab(
                id='logo',
                className='tab',
                label='HIDEBOUND',
                value='',
                disabled_style=tab_style,
                disabled=True,
            ),
            dcc.Tab(
                className='tab',
                label='data',
                value='data',
                style=tab_style,
                selected_style=tab_selected_style,
            ),
            dcc.Tab(
                className='tab',
                label='graph',
                value='graph',
                style=tab_style,
                selected_style=tab_selected_style,
            ),
            dcc.Tab(
                className='tab',
                label='config',
                value='config',
                style=tab_style,
                selected_style=tab_selected_style,
            ),
            dcc.Tab(
                className='tab',
                label='api',
                value='api',
                style=tab_style,
                selected_style=tab_selected_style,
            ),
            dcc.Tab(
                className='tab',
                label='docs',
                value='docs',
                style=tab_style,
                selected_style=tab_selected_style,
            )
        ],
    )
    content = dcc.Loading(
        id="content",
        className='content',
        type="dot",
        style={
            'align-items': 'center',
            'opacity': '50%',
            'background': COLOR_SCHEME['bg'],
        },
        fullscreen=True,
        color=COLOR_SCHEME['cyan2'],
    )

    app = dash.Dash(
        name='hidebound',
        title='Hidebound',
        server=server,
        external_stylesheets=['/static/style.css'],
    )
    app.layout = html.Div(id='layout', children=[store, tabs, content])
    app.config['suppress_callback_exceptions'] = True

    return app


# TABS--------------------------------------------------------------------------
def get_data_tab(query=None):
    # type: (Optional[str]) -> List
    '''
    Get tab element for Hidebound data.

    Args:
        query (str, optional): Query string. Default: None.

    Return:
        list: List of elements for data tab.
    '''
    # dummies muist go first for element props behavior to work
    return [*get_dummy_elements(), get_searchbar(query)]


def get_config_tab(config):
    # type: (Dict) -> List
    '''
    Get tab element for Hidebound config.

    Args:
        config (dict): Configuration to be displayed.

    Return:
        list: List of elements for config tab.
    '''
    # dummies muist go first for element props behavior to work
    return [*get_dummy_elements(), get_configbar(config)]


# MENUBARS----------------------------------------------------------------------
def get_searchbar(query=None):
    # type: (Optional[str]) -> html.Div
    '''
    Get a row of elements used for querying Hidebound data.

    Args:
        query (str, optional): Query string. Default: None.

    Returns:
        Div: Div with query field, buttons and dropdown.
    '''
    if query is None:
        query = 'SELECT * FROM data'

    spacer = html.Div(className='col spacer')
    query = dcc.Input(
        id='query',
        className='col query',
        value=query,
        placeholder='SQL query that uses "FROM data"',
        type='text',
        autoFocus=True,
        debounce=True
    )
    dropdown = get_dropdown(['file', 'asset'])

    search = get_button('search')
    init = get_button('init')
    update = get_button('update')
    create = get_button('create')
    export = get_button('export')
    delete = get_button('delete')

    row0 = html.Div(
        className='row',
        children=[
            query,
            spacer,
            search,
            spacer,
            dropdown,
            spacer,
            init,
            spacer,
            update,
            spacer,
            create,
            spacer,
            export,
            spacer,
            delete,
        ],
    )
    row1 = html.Div(className='row-spacer')
    row2 = html.Div(id='table-content', children=[])
    searchbar = html.Div(
        id='searchbar', className='menubar', children=[row0, row1, row2]
    )
    return searchbar


def get_dummy_elements():
    # type: () -> List
    '''
    Returns a list of all elements with callbacks so that the client will not
    throw errors in each tab.

    Returns:
        list: List of html elements.
    '''
    return [
        dcc.Input(className='dummy', id='query', value=None),
        dcc.Dropdown(className='dummy', id='dropdown', value=None),
        html.Div(className='dummy', id='search-button', n_clicks=None),
        html.Div(className='dummy', id='init-button', n_clicks=None),
        html.Div(className='dummy', id='update-button', n_clicks=None),
        html.Div(className='dummy', id='create-button', n_clicks=None),
        html.Div(className='dummy', id='export-button', n_clicks=None),
        html.Div(className='dummy', id='delete-button', n_clicks=None),
        dcc.Upload(className='dummy', id='upload', contents=None),
        html.Div(className='dummy', id='write-button', n_clicks=None),
    ]


def get_configbar(config):
    # type: (Dict) -> html.Div
    '''
    Get a row of elements used for configuring Hidebound.

    Args:
        config (dict): Configuration to be displayed.

    Returns:
        Div: Div with buttons and JSON editor.
    '''
    expander = html.Div(className='col expander')
    spacer = html.Div(className='col spacer')

    upload = dcc.Upload(
        id='upload',
        children=[get_button('upload')]
    )
    write = get_button('write')

    rows = [
        html.Div(
            className='row',
            children=[expander, spacer, upload, spacer, write],
        ),
        html.Div(className='row-spacer'),
        html.Div(id='config-content', children=[
            get_key_value_card(config, header='config', id_='config-card')
        ])
    ]
    configbar = html.Div(id='configbar', className='menubar', children=rows)
    return configbar


# ELEMENTS----------------------------------------------------------------------
def get_dropdown(options):
    # type: (List[str]) -> dcc.Dropdown
    '''
    Gets html dropdown element with given options.

    Args:
        options (list[str]): List of options.

    Raises:
        TypeError: If options is not a list.
        TypeError: If any option is not a string.

    Returns:
        Dropdown: Dropdown element.
    '''
    if not isinstance(options, list):
        msg = f'{options} is not a list.'
        raise TypeError(msg)

    illegal = list(filter(lambda x: not isinstance(x, str), options))
    if len(illegal) > 0:
        msg = f'{illegal} are not strings.'
        raise TypeError(msg)

    return dcc.Dropdown(
        id='dropdown',
        className='col dropdown',
        value=options[0],
        options=[{'label': x, 'value': x} for x in options],
        placeholder=options[0],
        optionHeight=20,
        style={
            'background': COLOR_SCHEME['grey1'],
            'color': COLOR_SCHEME['light1'],
            'border': '0px',
            'width': '100px',
        }
    )


def get_button(title):
    # type: (str) -> html.Button
    '''
    Get a html button with a given title.

    Args:
        title (str): Title of button.

    Raises:
        TypeError: If title is not a string.

    Returns:
        Button: Button element.
    '''
    if not isinstance(title, str):
        msg = f'{title} is not a string.'
        raise TypeError(msg)
    return html.Button(id=f'{title}-button', children=[title], n_clicks=0)


def get_key_value_card(data, header=None, id_='key-value-card'):
    # type: (Dict, Optional[str], str) -> html.Div
    '''
    Creates a key-value card using the keys and values from the given data.
    One key-value pair per row.

    Args:
        data (dict): Dictionary to be represented.
        header (str, optional): Name of header. Default: None.
        id_ (str): Name of id property. Default: "key-value-card".

    Returns:
        Div: Card with key-value child elements.
    '''
    data = blob_etl.BlobETL(data)\
        .set(
            predicate=lambda k, v: re.search(r'<list_\d', k),
            key_setter=lambda k, v: re.sub('<list_|>', '', k))\
        .to_flat_dict()

    children = []  # type: List[Any]
    if header is not None:
        header = html.Div(
            id=f'{id_}-header',
            className='key-value-card-header',
            children=[str(header)]
        )
        children.append(header)

    for i, (k, v) in enumerate(sorted(data.items())):
        even = i % 2 == 0
        klass = 'odd'
        if even:
            klass = 'even'

        key = html.Div(
            id=f'{k}-key', className='key-value-card-key', children=[str(k)]
        )
        sep = html.Div(className='key-value-card-separator')
        val = html.Div(
            id=f'{k}-value', className='key-value-card-value', children=[str(v)]
        )

        row = html.Div(
            id=f'{id_}-row',
            className=f'key-value-card-row {klass}',
            children=[key, sep, val]
        )
        children.append(row)
    children[-1].className += ' last'

    card = html.Div(
        id=f'{id_}',
        className='key-value-card',
        children=children
    )
    return card


def get_datatable(data):
    # type: (List[Dict]) -> dash_table.DataTable
    '''
    Gets a Dash DataTable element using given data.
    Assumes dict element has all columns of table as keys.

    Args:
        data (list[dict]): List of dicts.

    Returns:
        DataTable: Table of data.
    '''
    cols = []  # type: Any
    if len(data) > 0:
        cols = data[0].keys()
    cols = [{'name': x, 'id': x} for x in cols]
    error_cols = [
        'asset_error',
        'file_error',
        'filename_error'
    ]

    return dash_table.DataTable(
        data=data,
        columns=cols,
        id='datatable',
        cell_selectable=False,
        editable=False,
        css=[
            {
                'selector': '.dash-cell div.dash-cell-value',
                'rule': '''display: inline;
                           white-space: inherit;
                           overflow: inherit;
                           text-overflow: inherit;'''
            }
        ],
        style_data={
            'whiteSpace': 'normal',
            'height': 'auto',
            'width': 'auto'

        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'color': COLOR_SCHEME['light1'],
                'background': COLOR_SCHEME['grey1'],
            },
            {
                'if': {'row_index': 'even'},
                'color': COLOR_SCHEME['light1'],
                'background': COLOR_SCHEME['bg']
            },
            {
                'if': {'column_id': error_cols},
                'color': COLOR_SCHEME['red2'],
            }
        ],
        style_table={
            'zIndex': '0',
            'maxWidth': '99.5vw',
            'maxHeight': '95vh',
            'overflowX': 'auto',
            'overflowY': 'auto',
            'padding': '0px 4px 0px 4px',
            'borderWidth': '0px 1px 0px 1px',
            'borderColor': COLOR_SCHEME['grey1'],
        },
        style_header={
            'color': COLOR_SCHEME['light2'],
            'background': COLOR_SCHEME['grey1'],
            'fontWeight': 'bold',
        },
        style_filter={
            'color': COLOR_SCHEME['cyan2'],
            'background': COLOR_SCHEME['bg']
        },
        style_cell={
            'textAlign': 'left',
            # 'minWidth': '105px',
            'maxWidth': '300px',
            'borderColor': COLOR_SCHEME['grey1'],
            'border': '0px',
            'height': '25px',
            'padding': '3px 0px 3px 10px'
        }
    )


def get_asset_graph(data):
    # type: (List[Dict]) -> cyto.Cytoscape
    '''
    Creates asset graph data for cytoscape component.

    Args:
        data (list[dict]): List of dicts.

    Raises:
        KeyError: If asset_valid or asset_path keys not found.

    Returns:
        Cytoscape: Cytoscape graph.
    '''
    data_ = DataFrame(data)  # type: DataFrame
    cols = ['asset_path', 'asset_valid']

    temp = data_.columns.tolist()
    if cols[0] not in temp or cols[1] not in temp:
        msg = f'Rows must contain {cols} keys. Keys found: {temp}.'
        raise KeyError(msg)

    data_ = data_[cols]
    keys = data_.asset_path.tolist()
    vals = data_.asset_valid.apply(lambda x: f'asset_valid: {x}').tolist()
    data_ = dict(zip(keys, vals))
    graph = blob_etl.BlobETL(data_).to_networkx_graph()

    edges = []
    for s, t in list(graph.edges):
        edge = dict(group='edges', source=s, target=t)
        edges.append(edge)

    nodes = []
    for n in list(graph.nodes):
        attrs = graph.nodes.get(n)

        color = COLOR_SCHEME['cyan2']
        val = attrs.get('value', [None])[0]
        if val == 'asset_valid: True':
            color = COLOR_SCHEME['green2']
        elif val == 'asset_valid: False':
            color = COLOR_SCHEME['red2']

        label = attrs['short_name']
        if not label.startswith('"asset_valid'):
            node = dict(id=n, group='nodes', label=label, color=color)
            nodes.append(node)

    nodes.extend(edges)
    data_ = [{'data': x} for x in nodes]

    root = data_[0]['data']['id']
    return cyto.Cytoscape(
        id='asset-graph',
        elements=data_,
        layout={'name': 'breadthfirst', 'roots': [root]},
        style=dict(
            width='98% !important',
            height='98% !important',
            position='relative !important'
        ),
        stylesheet=[
            dict(
                selector='node',
                style={
                    'background-color': 'data(color)',
                    'color': COLOR_SCHEME['bg'],
                    'content': 'data(label)',
                    'padding': '10px 10px 10px 10px',
                    'shape': 'rectangle',
                    'text-halign': 'center',
                    'text-valign': 'center',
                    'width': 'label',
                    'height': 'label',
                    'font-size': '25px',
                }
            ),
            dict(
                selector='edge',
                style={
                    'line-color': COLOR_SCHEME['grey2'],
                }
            )
        ]
    )
