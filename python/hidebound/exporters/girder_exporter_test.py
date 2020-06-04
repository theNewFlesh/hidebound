import unittest

from girder_client import HttpError

from hidebound.exporters.girder_exporter import GirderExporter
# ------------------------------------------------------------------------------


class MockGirderClient:
    def __init__(self, apiUrl=None):
        self.apiUrl = apiUrl
        self._folders = {}
        self._items = {}
        self._files = {}
        self._id = -1

    @property
    def folders(self):
        return {x['name']: x for x in self._folders.values()}

    @property
    def items(self):
        return {x['name']: x for x in self._items.values()}

    @property
    def files(self):
        return {x['name']: x for x in self._files.values()}

    def _get_id(self):
        self._id += 1
        return self._id

    def createFolder(
        self,
        parentId,
        name,
        description='',
        parentType='folder',
        public=None,
        reuseExisting=False,
        metadata=None
    ):
        id_ = None
        if name in self.folders.keys():
            id_ = self.folders[name]['_id']
            if not reuseExisting:
                msg = 'A folder with that name already exists here.'
                url = 'http://0.0.0.0:8080/api/v1/folder'
                raise HttpError(400, msg, url, 'POST')
            else:
                name += ' (1)'
        else:
            id_ = self._get_id()

        temp = metadata or {}
        response = dict(
            _id=id_,
            parentId=parentId,
            name=name,
            metadata=metadata,
            items=temp.get('items', [])
        )
        self._folders[response['_id']] = response
        return response

    def listItem(
        self,
        folderId,
        text=None,
        name=None,
        limit=None,
        offset=None
    ):
        folder = self._folders.get(folderId, None)
        if folder is None:
            return []
        return [self._items[x] for x in folder['items']]

    def createItem(
        self,
        parentFolderId,
        name,
        description='',
        reuseExisting=False,
        metadata=None
    ):
        response = dict(
            _id=self._get_id(),
            parentFolderId=parentFolderId,
            name=name,
            metadata=metadata,
        )
        self._items[response['_id']] = response
        self._folders[parentFolderId]['items'].append(response['_id'])
        return response

    def uploadFileToItem(
        self,
        itemId,
        filepath,
        reference=None,
        mimeType=None,
        filename=None,
        progressCallback=None
    ):
        self._items[itemId]['file_content'] = filepath
        return dict(
            _id=self._get_id()
        )
# ------------------------------------------------------------------------------


class GirderExporterTests(unittest.TestCase):
    def setUp(self):
        self.client = MockGirderClient()
        self.exporter = GirderExporter(
            'api_key',
            'root_id',
            root_type='collection',
            host='0.0.0.0',
            port=8080,
            client=self.client
        )

    def test_init(self):
        expected = 'Invalid root_type. foo is not folder or collection.'
        with self.assertRaisesRegexp(ValueError, expected):
            GirderExporter(
                'api_key',
                'root_id',
                root_type='foo'
            )

        result = GirderExporter(
            'api_key',
            'root_id',
            root_type='collection',
            host='1.2.3.4',
            port=5678,
            client=self.client
        )
        expected = 'http://1.2.3.4:5678/api/v1'
        self.assertEqual(result._url, expected)

    def test_export_dirs(self):
        dirpath = '/foo/bar/baz'
        meta = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=meta)

        result = sorted(self.client.folders.keys())
        self.assertEqual(result, ['bar', 'baz', 'foo'])

        result = self.client.folders
        self.assertIsNone(result['foo']['metadata'])
        self.assertIsNone(result['bar']['metadata'])
        self.assertEqual(result['baz']['metadata'], meta)

    def test_export_dirs_single_dir(self):
        dirpath = '/foo'
        expected = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=expected)
        result = self.client.folders

        self.assertEqual(list(result.keys()), ['foo'])
        self.assertEqual(result['foo']['metadata'], expected)

        with self.assertRaises(HttpError):
            self.exporter._export_dirs(
                dirpath, metadata=expected, exists_ok=False
            )

        expected = dict(pizza='bagel')
        self.exporter._export_dirs(dirpath, metadata=expected, exists_ok=True)
        result = self.client.folders
        self.assertEqual(result['foo (1)']['metadata'], expected)

    def test_export_dirs_exists_ok(self):
        dirpath = '/foo/bar/baz'
        meta = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=meta)

        # test exists_ok = False
        with self.assertRaises(HttpError):
            self.exporter._export_dirs(dirpath, exists_ok=False)

        # test exists_ok = True
        expected = dict(kiwi='taco')
        self.exporter._export_dirs(dirpath, exists_ok=True, metadata=expected)
        result = self.client.folders['baz (1)']['metadata']
        self.assertEqual(result, expected)

    def test_export_asset(self):
        metadata = dict(asset_type='file')
        self.exporter._export_asset(metadata)
        self.assertEqual(self.client.folders, {})
        self.assertEqual(self.client.files, {})

        metadata = dict(
            asset_type='sequence',
            asset_path_relative='foo/bar/baz',
            apple='orange',
        )
        self.exporter._export_asset(metadata)
        result = sorted(list(self.client.folders.keys()))
        self.assertEqual(result, ['bar', 'baz', 'foo'])
        self.assertEqual(self.client.files, {})

        expected = 'foo/bar/baz directory already exists'
        with self.assertRaisesRegexp(HttpError, expected):
            self.exporter._export_asset(metadata)

    def test_export_file(self):
        expected = dict(
            filepath='/root/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_file(expected)

        result = list(sorted(self.client.folders.keys()))
        self.assertEqual(result, ['bar', 'foo'])

        result = self.client.items
        self.assertEqual(result['taco.txt']['metadata'], expected)
        self.assertEqual(
            result['taco.txt']['file_content'], expected['filepath']
        )

    def test_export_file_error(self):
        meta = dict(
            filepath='/root/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_file(meta)

        item = self.client.items['taco.txt']['_id']
        items = self.client.folders['bar']['items']
        self.assertIn(item, items)
