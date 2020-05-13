import dash
import dash_core_components as dcc
import dash_html_components as html
from flasgger import Swagger
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
# ------------------------------------------------------------------------------


def get_app():
    '''
    Generate dash app container.

    Returns:
        Dash.Dash: Dash app instance.
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
                className='tab',
                label='Data',
                value='data',
                style=tab_style,
                selected_style=tab_selected_style,
            ),
            # dcc.Tab(
            #     className='tab',
            #     label='Metrics',
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
    # app.css.append_css({'external_url': '/static/style.css'})
    app.layout = html.Div(id='layout', children=[store, tabs, content])
    app.config['suppress_callback_exceptions'] = True
    app._hb_database = None
    app._hb_config = None
    return app


def get_dropdown(options):
    return dcc.Dropdown(
        id='drop-down',
        className='col drop-down',
        value=options[0],
        options=[{'label': x, 'value': x} for x in options],
        # multi=True,
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
    return html.Button(id='button', children=[title])


def get_searchbar():
    spacer = html.Div(className='col spacer')
    searchval = dcc.Input(
        id='search-val', className='col search-val', value='', type='text'
    )
    button = get_button('search')
    dropdown = get_dropdown(['file', 'asset'])

    row = html.Div(
        className='row',
        children=[
            searchval,
            spacer,
            button,
            spacer,
            dropdown,
        ],
    )
    searchbar = html.Div(id='searchbar', className='searchbar', children=[row])
    return searchbar


def get_data_tab():
    return [get_searchbar()]
