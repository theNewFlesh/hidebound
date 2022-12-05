from typing import Any, Dict, List, Optional  # noqa F401

from girder_client import HttpError

from hidebound.exporters.girder_exporter import GirderExporter
# ------------------------------------------------------------------------------


'''
This module contains all the mock classes for working with Girder exporters and
clients.
'''


class MockGirderExporter:
    '''
    A mock version of the GirderExporter class.
    '''

    @staticmethod
    def from_config(config):
        # type: (Dict[str, Any]) -> GirderExporter
        '''
        Construct a GirderExporter from a given config.

        Args:
            config (dict): Config dictionary.

        Returns:
            GirderExporter: GirderExporter instance with MockGirderClient.
        '''
        return GirderExporter\
            .from_config(config, client=MockGirderClient(add_suffix=False))
# ------------------------------------------------------------------------------


class MockGirderClient:
    '''
    A mock client for Girder.
    '''
    def __init__(self, apiUrl=None, add_suffix=True):
        # type: (Optional[str], bool) -> None
        '''
        Constructs mock client.

        Args:
            apiUrl (str, optional): URL to Girder REST API.
            add_suffix (bool, optional): Whether to add suffices to prexisting
                folder names. Default: False.
        '''
        self.apiUrl = apiUrl  # type: Optional[str]
        self._folders = {}  # type: Dict
        self._items = {}  # type: Dict
        self._files = {}  # type: Dict[str, Any]
        self._id = -1  # type: int
        self._add_suffix = add_suffix  # type: bool

    @property
    def folders(self):
        # type: () -> Dict[str, Any]
        '''
        Convenience property that returns a name, folder dictionary of folders.
        '''
        return {x['name']: x for x in self._folders.values()}

    @property
    def items(self):
        # type: () -> Dict[str, Any]
        '''
        Convenience property that returns a name, item dictionary of items.
        '''
        return {x['name']: x for x in self._items.values()}

    @property
    def files(self):
        # type: () -> Dict[str, Any]
        '''
        Convenience property that returns a name, file dictionary of files.
        '''
        return {x['name']: x for x in self._files.values()}

    def _get_id(self):
        # type: () -> int
        '''
        Convenience property that returns a number that increments with each
        call.
        '''
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
        # type: (str, str, str, str, Optional[str], bool, Optional[Dict]) -> Dict[str, Any]
        '''
        Creates and returns a folder.

        Args:
            parentId (str): The id of the parent resource to create the folder
                in.
            name (str): The name of the folder.
            description (str, optional): A description of the folder.
                Default: ''.
            parentType (str, optional): One of ('folder', 'user', 'collection').
                Default: 'folder'.
            public (str, optional): Whether the folder should be marked as
                public. Default: None.
            reuseExisting (bool, optional): Whether to return an existing folder
                if one with the same name exists. Default: False.
            metadata (dict, optional): JSON metadata to set on the folder.
                Default: None

        Raises:
            HttpError: If folder with the given name already exists and
                reuseExisting id set to False.

        Returns:
            dict: Response.
        '''
        id_ = None
        if name in self.folders.keys():
            id_ = self.folders[name]['_id']
            if not reuseExisting:
                msg = 'A folder with that name already exists here.'
                url = 'http://0.0.0.0:8180/api/v1/folder'
                raise HttpError(400, msg, url, 'POST')
            elif self._add_suffix:
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
        # type: (str, Any, Any, Any, Any) -> List
        '''
        Returns all items under a given folder.

        Args:
            folderId (str): The parent folder's ID.
            text (str, optional): Query for full text search of items.
                Default: None.
            name (str, optional): Query for exact name match of items.
                Default: None.
            limit (str, optional): If requesting a specific slice, the length of
                the slice. Default: None.
            offset (str, optional): Starting offset into the list.
                Default: None.

        Returns:
            list[dict]: List if item dicts.
        '''
        folder = self._folders.get(folderId, None)  # type: Any
        if folder is None:
            return []
        return [self._items[x] for x in folder['items']]

    def createItem(
        self,
        parentFolderId,
        name,
        description='',
        reuseExisting=False,
        metadata=None,
    ):
        # type: (str, str, str, bool, Optional[str]) -> Dict[str, Any]
        '''
        Creates and returns an item.

        Args:
            parentFolderId (str): The folder this item should be created in.
            name (str): The item name.
            description (str, optional): A description of the item. Default: ''.
            reuseExisting (str, optional): Whether to return an existing item if
                one with same name already exists. Default: False.
            metadata (str, optional): JSON metadata to set on item.
                Default: None.

        Returns:
            dict: Response.
        '''
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
        # type: (str, str, Any, Any, Any, Any) -> Dict
        '''
        Uploads a file to an item, in chunks.
        If the file already exists in the item with the same name and size.
        Or if the file has 0 bytes, no uploading will be performed.

        Args:
            itemId (str): ID of parent item for file.
            filepath (str): Path to file on disk.
            reference (str, optional): Optional reference to send along with the
                upload. Default: None.
            mimeType (str, optional): MIME type for the file. Will be guessed if
                not passed. Default: None.
            filename (str, optional): Path with filename used in Girder.
                Defaults to basename of filepath. Default: None.
            progressCallback (str, optional): If passed, will be called after
                each chunk with progress information. It passes a single
                positional argument to the callable which is a dict of
                information about progress. Default: None.

        Returns:
            dict: Response.
        '''
        self._items[itemId]['file_content'] = filepath
        return dict(
            _id=self._get_id()
        )
