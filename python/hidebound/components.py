import json

from dash_ace_editor import DashAceEditor
from flasgger import Swagger
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import jinja2

import hidebound.tools as tools


# TOOLS-------------------------------------------------------------------------
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
)
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
]
FONT_FAMILY = 'sans serif'


def render_template(filename, parameters):
    '''
    Renders a jinja2 template given by filename with given parameters.

    Args:
        filename (str): Filename of template.
        parameters (dict): Dictionary of template parameters.

    Returns:
        str: HTML string.
    '''
    tempdir = tools.relative_path(__file__, '../../templates').as_posix()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(tempdir),
        keep_trailing_newline=True
    )
    output = env.get_template(filename).render(parameters).encode('utf-8')
    return output


# APP---------------------------------------------------------------------------
def get_app(storage_type='memory'):
    '''
    Generate Dash Flask app instance.

    Args:
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
        'min-width': '200px',
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
            # dcc.Tab(
            #     className='tab',
            #     label='metrics',
            #     value='metrics',
            #     style=tab_style,
            #     selected_style=tab_selected_style,
            # ),
            dcc.Tab(
                className='tab',
                label='config',
                value='config',
                style=tab_style,
                selected_style=tab_selected_style,
            )
        ],
    )
    content = html.Div(id='content', className='content')

    app = dash.Dash(
        __name__,
        external_stylesheets=['http://0.0.0.0:5000/static/style.css']
    )
    Swagger(app.server)
    app.layout = html.Div(id='layout', children=[store, tabs, content])
    app.config['suppress_callback_exceptions'] = True
    app.server._database = None
    app.server._config = {}
    app.server._config_path = ''

    return app


# TABS--------------------------------------------------------------------------
def get_data_tab():
    '''
    Get tab element for Hidebound data.

    Return:
        list: List of elements for data tab.
    '''
    return [get_searchbar()]


def get_config_tab(config):
    '''
    Get tab element for Hidebound config.

    Args:
        config (dict): Configuration to be displayed.

    Return:
        list: List of elements for config tab.
    '''
    return [get_configbar(config)]


# MENUBARS----------------------------------------------------------------------
def get_searchbar():
    '''
    Get a row of elements used for querying Hidebound data.

    Returns:
        Div: Div with query field, buttons and dropdown.
    '''
    spacer = html.Div(className='col spacer')
    query = dcc.Input(
        id='query',
        className='col query',
        value='SELECT * FROM data',
        placeholder='SQL query that uses "FROM data"',
        type='text'
    )
    dropdown = get_dropdown(['file', 'asset'])

    search = get_button('search')
    init = get_button('init')
    update = get_button('update')
    create = get_button('create')
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
            delete,
        ],
    )
    row1 = html.Div(className='row-spacer')
    row2 = html.Div(id='table-content', children=[])
    searchbar = html.Div(
        id='searchbar', className='menubar', children=[row0, row1, row2]
    )
    return searchbar


def get_configbar(config):
    '''
    Get a row of elements used for configuring Hidebound.

    Args:
        config (dict): Configuration to be displayed.

    Returns:
        Div: Div with buttons and JSON editor.
    '''
    expander = html.Div(className='col expander')
    spacer = html.Div(className='col spacer')

    upload = get_button('upload')
    validate = get_button('validate')
    write = get_button('write')

    row0 = html.Div(
        className='row',
        children=[expander, spacer, upload, spacer, validate, spacer, write],
    )
    row1 = html.Div(
        className='row-spacer'
    )
    row2 = html.Div(
        id='json-editor-row',
        className='row json-editor-row',
        children=[get_json_editor(config)]
    )
    configbar = html.Div(
        id='configbar', className='menubar', children=[row0, row1, row2]
    )
    return configbar


# ELEMENTS----------------------------------------------------------------------
def get_dropdown(options):
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
            'width': '90px',
        }
    )


def get_button(title):
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


def get_json_editor(value={}):
    '''
    Gets a JSON editor element.

    Args:
        value (dict, optional): Dictionary to be edited. Default: {}.

    Returns:
        DashAceEditor: JSON editor.
    '''
    return DashAceEditor(
        id='json-editor',
        value=json.dumps(value, indent=4, sort_keys=True),
        height='100%',
        width='100%',
        showLineNumbers=True,
        tabSize=4,
        enableLiveAutocompletion=False,
        enableBasicAutocompletion=False
    )


def get_datatable(data):
    '''
    Gets a Dash DataTable element using given data.
    Assumes dict element has all columns of table as keys.

    Args:
        data (list[dict]): List of dicts.

    Returns:
        DataTable: Table of data.
    '''
    cols = []
    if len(data) > 0:
        cols = data[0].keys()
    cols = [{'name': x, 'id': x} for x in cols]

    return dash_table.DataTable(
        data=data,
        columns=cols,
        id='datatable',
        # fixed_rows={'headers': True},
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
            'fontWeight': 'bold'
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
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'color': COLOR_SCHEME['light1'],
                'background': COLOR_SCHEME['grey1']
            },
            {
                'if': {'row_index': 'even'},
                'color': COLOR_SCHEME['light1'],
                'background': COLOR_SCHEME['bg']
            }
        ]
    )
