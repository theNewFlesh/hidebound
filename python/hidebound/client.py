import dash
import dash_core_components as dcc
import dash_html_components as html
from flasgger import Swagger
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
FONT_FAMILY = 'Courier'


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


# ELEMENTS----------------------------------------------------------------------
def get_app():
    '''
    Generate Dash Flask app instance.

    Returns:
        Dash: Dash app instance.
    '''
    store = dcc.Store(id='session-store', storage_type='session')

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
            # dcc.Tab(
            #     className='tab',
            #     label='metrics',
            #     value='metrics',
            #     style=tab_style,
            #     selected_style=tab_selected_style,
            # )
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
    app.server._config = None

    return app


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
        id='drop-down',
        className='col drop-down',
        value=options[0],
        options=[{'label': x, 'value': x} for x in options],
        placeholder=options[0],
        optionHeight=20,
        style={
            'background': COLOR_SCHEME['grey1'],
            'color': COLOR_SCHEME['light1'],
            'border': '0px',
            'min-width': '225px',
            'max-width': '550px'
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
    return html.Button(id='button', children=[title])


def get_searchbar():
    '''
    Get a row of elements used for querying Hidebound data.

    Returns:
        Div: Div with query, search button and dropdown elements.
    '''
    spacer = html.Div(className='col spacer')
    query = dcc.Input(
        id='query',
        className='col query',
        value='SELECT * FROM data WHERE ',
        placeholder='SQL query that uses "FROM data"',
        type='text'
    )
    button = get_button('search')
    dropdown = get_dropdown(['file', 'asset'])

    row = html.Div(
        className='row',
        children=[query, spacer, button, spacer, dropdown],
    )
    searchbar = html.Div(id='searchbar', className='searchbar', children=[row])
    return searchbar


def get_logo():
    '''
    Get Hidebound logo for menu bar.

    Returns:
        Div: Hidebound text and logo.
    '''
    return html.Span(
        id='logo',
        className='logo',
        children='hidebound',
    )


def get_data_tab():
    '''
    Get tab element for Hidebound data.

    Return:
        list: List of elements for data tab.
    '''
    return [get_searchbar()]
