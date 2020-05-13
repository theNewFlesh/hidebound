import unittest

import jinja2

import hidebound.client as client
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class ClientTests(unittest.TestCase):
    def test_render_template(self):
        tempdir = tools.relative_path(__file__, '../../templates').as_posix()
        params = dict(
            COLOR_SCHEME=client.COLOR_SCHEME,
            FONT_FAMILY=client.FONT_FAMILY,
        )
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(tempdir),
            keep_trailing_newline=True
        )
        expected = env\
            .get_template('style.css.j2')\
            .render(params)\
            .encode('utf-8')

        result = client.render_template('style.css.j2', params)
        self.assertEqual(result, expected)

    def test_get_app(self):
        result = client.get_app()
        self.assertTrue(hasattr(result.server, '_database'))
        self.assertTrue(hasattr(result.server, '_config'))

    def test_get_dropdown(self):
        expected = 'foo is not a list.'
        with self.assertRaisesRegexp(TypeError, expected):
            client.get_dropdown('foo')

        expected = r'\[2, 3\] are not strings\.'
        with self.assertRaisesRegexp(TypeError, expected):
            client.get_dropdown(['foo', 2, 3])

        result = client.get_dropdown(['foo', 'bar'])
        self.assertEqual(result.id, 'drop-down')
        self.assertEqual(result.value, 'foo')
        self.assertEqual(result.placeholder, 'foo')

        expected = ['foo', 'bar']
        expected = [{'label': x, 'value': x} for x in expected]
        self.assertEqual(result.options, expected)

    def test_get_button(self):
        expected = '10 is not a string.'
        with self.assertRaisesRegexp(TypeError, expected):
            client.get_button(10)

        result = client.get_button('foo')
        self.assertEqual(result.id, 'button')
        self.assertEqual(result.children[0], 'foo')

    def test_get_searchbar(self):
        searchbar = client.get_searchbar()
        self.assertEqual(searchbar.id, 'searchbar')

        query = searchbar.children[0].children[0]
        self.assertEqual(query.id, 'query')
        self.assertEqual(query.value, 'SELECT * FROM data WHERE ')
        self.assertEqual(query.placeholder, 'SQL query that uses "FROM data"')

        button = searchbar.children[0].children[2]
        self.assertEqual(button.id, 'button')
        self.assertEqual(button.children[0], 'search')

    def test_get_data_tab(self):
        tab = client.get_data_tab()
        self.assertEqual(tab[0].id, 'searchbar')
