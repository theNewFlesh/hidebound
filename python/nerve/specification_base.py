from pathlib import Path
import uuid

from nerve.validators import ValidationError
from pyparsing import ParseException
from schematics import Model
from schematics.types import StringType, IntType

from nerve.parser import AssetNameParser
import nerve.validators as vd
# ------------------------------------------------------------------------------


'''
Contains the abstract base classes for all Nerve specifications.
'''


class SpecificationBase(Model):
    '''
    The base class for all Nerve specifications.

    Attributes:
        asset_type (str): Type of asset. Options include: file, sequence, complex.
        filename_fields (list[str]): List of fields found in the asset filenames.
        asset_name_fields (list[str]): List of fields found in the asset name.
        project (str): Project name.
        descriptor (str): Asset descriptor.
        version (int): Asset version.
        extension (str): File extension.
    '''
    name = None
    asset_type = 'specification'
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'extension'
    ]
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']
    project = StringType(required=True, validators=[vd.is_project])
    descriptor = StringType(required=True, validators=[vd.is_descriptor])
    version = IntType(required=True, validators=[vd.is_version])
    extension = StringType(required=True, validators=[vd.is_extension])

    def __init__(self, data={}):
        '''
        Returns a new specification instance.

        Args:
            data (dict, optional): Dictionary of asset data.
        '''
        super().__init__(raw_data=data)
        self.name = self.__class__.__name__.lower()

    def get_asset_name(self, filepath):
        '''
        Returns the expected asset name give a filepath.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Returns:
            str: Asset name.
        '''
        filepath = Path(filepath)
        data = AssetNameParser(self.filename_fields).parse(filepath.name)
        return AssetNameParser(self.asset_name_fields).to_string(data)

    def get_asset_path(self, filepath):
        '''
        Returns the expected asset path given a filepath.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Raises:
            NotImplementedError: If method not defined in subclass.

        Returns:
            Path: Asset path.
        '''
        msg = 'Method must be implemented in subclasses of SpecificationBase.'
        raise NotImplementedError(msg)

    def get_asset_id(self, filepath):
        '''
        Returns a hash UUID of the asset directory or file, depending of asset
        type.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Returns:
            str: Asset id.
        '''
        return str(uuid.uuid3(
            uuid.NAMESPACE_URL, self.get_asset_path(filepath).as_posix()
        ))

    def validate_filepath(self, filepath):
        '''
        Attempts to parse the given filepath.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Raises:
            ValidationError: If parse fails.
            ValidationError: If asset directory name is invalid.
        '''
        filepath = Path(filepath)
        try:
            data = AssetNameParser(self.filename_fields).parse(filepath.name)
        except ParseException as e:
            raise ValidationError(repr(e))

        if self.asset_type == 'file':
            return

        parser = AssetNameParser(self.asset_name_fields)
        actual = self.get_asset_path(filepath).name
        try:
            parser.parse(actual)
        except ParseException as e:
            raise ValidationError(repr(e))

        expected = parser.to_string(data)
        if actual != expected:
            msg = 'Invalid asset directory name. '
            msg += f'Expecting: {expected}. Found: {actual} in '
            msg += f'{filepath.as_posix()}.'
            raise ValidationError(msg)

    def get_filename_metadata(self, filepath):
        '''
        Returns a dictionary of filename metadata from given filepath.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Returns:
            dict: Metadata.
        '''
        return AssetNameParser(self.filename_fields).parse(Path(filepath).name)


class FileSpecificationBase(SpecificationBase):
    '''
    The base class for asset that consist of a single file.

    Attributes:
        asset_type (str): File.
    '''
    asset_type = 'file'

    def get_asset_path(self, filepath):
        '''
        Returns the filepath.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Returns:
            Path: Asset path.
        '''
        return Path(filepath)


class SequenceSpecificationBase(SpecificationBase):
    '''
    The base class for assets that consist of a sequence of files under a single
    directory.

    Attributes:
        asset_type (str): Sequence.
    '''
    asset_type = 'sequence'

    def get_asset_path(self, filepath):
        '''
        Returns the directory containing the asset files.

        Args:
            filepath (str or Path): Fullpath to asset file.

        Returns:
            Path: Asset path.
        '''
        return Path(filepath).parents[0]


class ComplexSpecificationBase(SpecificationBase):
    '''
    The base class for assets that consist of multiple directories of files.

    Attributes:
        asset_type (str): Complex.
    '''
    asset_type = 'complex'
