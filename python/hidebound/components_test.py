import json
import unittest

import jinja2

import hidebound.components as components
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class ComponentsTests(unittest.TestCase):
    def test_render_template(self):
        tempdir = tools.relative_path(__file__, '../../templates').as_posix()
        params = dict(
            COLOR_SCHEME=components.COLOR_SCHEME,
            FONT_FAMILY=components.FONT_FAMILY,
        )
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(tempdir),
            keep_trailing_newline=True
        )
        expected = env\
            .get_template('style.css.j2')\
            .render(params)\
            .encode('utf-8')

        result = components.render_template('style.css.j2', params)
        self.assertEqual(result, expected)

    def test_get_app(self):
        result = components.get_app()
        self.assertTrue(hasattr(result.server, '_database'))
        self.assertTrue(hasattr(result.server, '_config'))

    def test_get_dropdown(self):
        expected = 'foo is not a list.'
        with self.assertRaisesRegexp(TypeError, expected):
            components.get_dropdown('foo')

        expected = r'\[2, 3\] are not strings\.'
        with self.assertRaisesRegexp(TypeError, expected):
            components.get_dropdown(['foo', 2, 3])

        result = components.get_dropdown(['foo', 'bar'])
        self.assertEqual(result.id, 'dropdown')
        self.assertEqual(result.value, 'foo')
        self.assertEqual(result.placeholder, 'foo')

        expected = ['foo', 'bar']
        expected = [{'label': x, 'value': x} for x in expected]
        self.assertEqual(result.options, expected)

    def test_get_button(self):
        expected = '10 is not a string.'
        with self.assertRaisesRegexp(TypeError, expected):
            components.get_button(10)

        result = components.get_button('foo')
        self.assertEqual(result.id, 'foo-button')
        self.assertEqual(result.children[0], 'foo')

    def test_get_json_editor(self):
        value = {'foo': 'bar'}
        result = components.get_json_editor(value)
        self.assertEqual(result.id, 'json-editor')

        expected = json.dumps(value, indent=4, sort_keys=True)
        self.assertEqual(result.value, expected)

    def test_get_searchbar(self):
        searchbar = components.get_searchbar()
        self.assertEqual(searchbar.id, 'searchbar')

        query = searchbar.children[0].children[0]
        self.assertEqual(query.id, 'query')
        self.assertEqual(query.value, 'SELECT * FROM data WHERE ')
        self.assertEqual(query.placeholder, 'SQL query that uses "FROM data"')

        button = searchbar.children[0].children[2]
        self.assertEqual(button.id, 'search-button')
        self.assertEqual(button.children[0], 'search')

        dropdown = searchbar.children[0].children[4]
        self.assertEqual(dropdown.id, 'dropdown')
        self.assertEqual(dropdown.options[0]['label'], 'file')
        self.assertEqual(dropdown.options[1]['label'], 'asset')

        button = searchbar.children[0].children[6]
        self.assertEqual(button.id, 'init-button')
        self.assertEqual(button.children[0], 'init')

        button = searchbar.children[0].children[8]
        self.assertEqual(button.id, 'update-button')
        self.assertEqual(button.children[0], 'update')

        button = searchbar.children[0].children[10]
        self.assertEqual(button.id, 'create-button')
        self.assertEqual(button.children[0], 'create')

        button = searchbar.children[0].children[12]
        self.assertEqual(button.id, 'delete-button')
        self.assertEqual(button.children[0], 'delete')


    def test_get_configbar(self):
        configbar = components.get_configbar({'foo': 'bar'})
        self.assertEqual(configbar.id, 'configbar')

        row_spacer = configbar.children[1]
        self.assertEqual(row_spacer.className, 'row-spacer')

        editor_row = configbar.children[2]
        self.assertEqual(editor_row.id, 'json-editor-row')

        buttons = configbar.children[0].children

        button = buttons[0]
        self.assertEqual(button.className, 'col expander')

        button = buttons[2]
        self.assertEqual(button.id, 'upload-button')
        self.assertEqual(button.children[0], 'upload')

        button = buttons[4]
        self.assertEqual(button.id, 'validate-button')
        self.assertEqual(button.children[0], 'validate')

        button = buttons[6]
        self.assertEqual(button.id, 'write-button')
        self.assertEqual(button.children[0], 'write')

    def test_get_data_tab(self):
        tab = components.get_data_tab()
        self.assertEqual(tab[0].id, 'searchbar')

    def test_get_config_tab(self):
        tab = components.get_config_tab({'foo': 'bar'})
        self.assertEqual(tab[0].id, 'configbar')

    def test_get_datatable(self):
        data = [
            {'foo': 'pizza', 'bar': 'taco'},
            {'foo': 'kiwi', 'bar': 'potato'},
        ]
        result = components.get_datatable(data)
        self.assertEqual(result.id, 'datatable')
        expected = [
            {'name': 'foo', 'id': 'foo'},
            {'name': 'bar', 'id': 'bar'}
        ]
        self.assertEqual(result.columns, expected)

        result = components.get_datatable([])
        self.assertEqual(result.columns, [])
