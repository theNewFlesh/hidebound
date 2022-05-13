from typing import Any, Dict, List, Optional, Tuple, Union

from pathlib import Path
import uuid

from pyparsing import ParseException
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import IntType, ListType, StringType

from hidebound.core.parser import AssetNameParser
import hidebound.core.tools as hbt
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


'''
Contains the abstract base classes for all Hidebound specifications.
'''


_INDICATOR_LUT = dict(
    project=AssetNameParser.PROJECT_INDICATOR,
    specification=AssetNameParser.SPECIFICATION_INDICATOR,
    descriptor=AssetNameParser.DESCRIPTOR_INDICATOR,
    version=AssetNameParser.VERSION_INDICATOR,
    coordinate=AssetNameParser.COORDINATE_INDICATOR,
    frame=AssetNameParser.FRAME_INDICATOR,
    extension=AssetNameParser.EXTENSION_INDICATOR,
)


class SpecificationBase(Model):
    '''
    The base class for all Hidebound specifications.

    Attributes:
        asset_type (str): Type of asset. Options include: file, sequence, complex.
        filename_fields (list[str]): List of fields found in the asset filenames.
        asset_name_fields (list[str]): List of fields found in the asset name.
        project (str): Project name.
        descriptor (str): Asset descriptor.
        version (int): Asset version.
        extension (str): File extension.
    '''
    asset_type = 'specification'  # type: str
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'extension'
    ]  # type: List[str]
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']  # type: List[str]
    project = ListType(
        StringType(), required=False, validators=[vd.is_project]
    )  # type: ListType
    specification = ListType(StringType())  # type: ListType
    descriptor = ListType(
        StringType(), required=False, validators=[vd.is_descriptor]
    )  # type: ListType
    version = ListType(
        IntType(), required=False, validators=[vd.is_version]
    )  # type: ListType
    extension = ListType(
        StringType(), required=True, validators=[vd.is_extension]
    )  # type: ListType
    file_traits = {}  # type: Dict[str, Any]

    def __init__(self, data={}):
        # type: (Optional[Dict[str, Any]]) -> None
        '''
        Returns a new specification instance.

        Args:
            data (dict, optional): Dictionary of asset data.
        '''
        super().__init__(raw_data=data)

    def get_asset_name(self, filepath):
        # type: (Union[str, Path]) -> str
        '''
        Returns the expected asset name give a filepath.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            str: Asset name.
        '''
        filepath = Path(filepath)
        data = AssetNameParser(self.filename_fields).parse(filepath.name)  # type: dict
        output = AssetNameParser(self.asset_name_fields).to_string(data)  # type: str
        return output

    def get_asset_path(self, filepath):
        # type: (Union[str, Path]) -> Path
        '''
        Returns the expected asset path given a filepath.

        Args:
            filepath (str or Path): filepath to asset file.

        Raises:
            NotImplementedError: If method not defined in subclass.

        Returns:
            Path: Asset path.
        '''
        msg = 'Method must be implemented in subclasses of SpecificationBase.'
        raise NotImplementedError(msg)

    def get_asset_id(self, filepath):
        # type: (Union[str, Path]) -> str
        '''
        Returns a hash UUID of the asset directory or file, depending of asset
        type.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            str: Asset id.
        '''
        return str(uuid.uuid3(
            uuid.NAMESPACE_URL, self.get_asset_path(filepath).as_posix()
        ))

    def validate_filepath(self, filepath):
        # type: (Union[str, Path]) -> None
        '''
        Attempts to parse the given filepath.

        Args:
            filepath (str or Path): filepath to asset file.

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

    def get_filename_traits(self, filepath):
        # type: (Union[str, Path]) -> Dict[str, Any]
        '''
        Returns a dictionary of filename traits from given filepath.
        Returns error in filename_error key if one is encountered.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            dict: Traits.
        '''
        try:
            return AssetNameParser(self.filename_fields)\
                .parse(Path(filepath).name)
        except ParseException as e:
            return dict(filename_error=hbt.error_to_string(e))

    def get_file_traits(self, filepath):
        # type: (Union[str, Path]) -> Dict
        '''
        Returns a dictionary of file traits from given filepath.
        Returns error in respective key if one is encountered.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            dict: Traits.
        '''
        output = {}
        for name, func in self.file_traits.items():
            try:
                output[name] = func(filepath)
            except Exception as e:
                output[name + '_error'] = hbt.error_to_string(e)
        return output

    def get_traits(self, filepath):
        # type: (Union[str, Path]) -> Dict[str, Any]
        '''
        Returns a dictionary of file and filename traits from given filepath.
        Errors are captured in their respective keys.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            dict: Traits.
        '''
        traits = self.get_filename_traits(filepath)
        traits.update(self.get_file_traits(filepath))
        return traits

    def get_name_patterns(self):
        # type: () -> Tuple[str, str]
        '''
        Generates asset name and filename patterns from class fields.

        Returns:
            tuple(str): Asset name pattern, filename pattern.
        '''
        def get_patterns(fields):
            output = []
            c_pad = AssetNameParser.COORDINATE_PADDING
            f_pad = AssetNameParser.FRAME_PADDING
            v_pad = AssetNameParser.VERSION_PADDING
            sep = AssetNameParser.TOKEN_SEPARATOR
            for field in fields:
                item = _INDICATOR_LUT[field]
                if field == 'version':
                    item += '{' + field + f':0{v_pad}d' + '}'
                elif field == 'frame':
                    item += '{' + field + f':0{f_pad}d' + '}'
                elif field == 'coordinate':
                    temp = []
                    for i, _ in enumerate(self.coordinate[0]):
                        temp.append('{' + f'{field}[{i}]:0{c_pad}d' + '}')
                    temp = sep.join(temp)
                    item += temp
                else:
                    item += '{' + field + '}'
                output.append(item)
            return output

        asset = get_patterns(self.asset_name_fields)  # type: Any
        asset = AssetNameParser.FIELD_SEPARATOR.join(asset)

        patterns = get_patterns(self.filename_fields)
        filename = ''
        if self.filename_fields[-1] == 'extension':
            filename = AssetNameParser.FIELD_SEPARATOR.join(patterns[:-1])
            filename += patterns[-1]
        else:
            filename = AssetNameParser.FIELD_SEPARATOR.join(patterns)
        return asset, filename

    def _to_filepaths(self, root, pattern):
        # type: (Union[str, Path], str) -> List[str]
        '''
        Generates a complete list of filepaths given a root directory and
        filepath pattern.

        Args:
            root (str or Path): Directory containing asset.
            pattern (str): Filepath pattern.

        Returns:
            list[str]: List of filepaths.
        '''
        filepaths = []
        for i, _ in enumerate(self.extension):
            fields = set(self.asset_name_fields).union(self.filename_fields)  # type: Any
            fields = {k: getattr(self, k)[i] for k in fields}
            filepath = pattern.format(**fields)
            filepath = Path(root, filepath).as_posix()
            filepaths.append(filepath)
        return filepaths


class FileSpecificationBase(SpecificationBase):
    '''
    The base class for asset that consist of a single file.

    Attributes:
        asset_type (str): File.
    '''
    asset_type = 'file'  # type: str

    def get_asset_path(self, filepath):
        # type: (Union[str, Path]) -> Path
        '''
        Returns the filepath.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            Path: Asset path.
        '''
        return Path(filepath)

    def to_filepaths(self, root):
        # type: (Union[str, Path]) -> List[str]
        '''
        Generates a complete list of filepaths given a root directory and
        filepath pattern.

        Args:
            root (str or Path): Directory containing asset.
            pattern (str): Filepath pattern.

        Returns:
            list[str]: List of filepaths.
        '''
        _, filename = self.get_name_patterns()
        return self._to_filepaths(root, filename)


class SequenceSpecificationBase(SpecificationBase):
    '''
    The base class for assets that consist of a sequence of files under a single
    directory.

    Attributes:
        asset_type (str): Sequence.
    '''
    asset_type = 'sequence'  # type: str

    def get_asset_path(self, filepath):
        # type: (Union[str, Path]) -> Path
        '''
        Returns the directory containing the asset files.

        Args:
            filepath (str or Path): filepath to asset file.

        Returns:
            Path: Asset path.
        '''
        return Path(filepath).parents[0]

    def to_filepaths(self, root):
        # type: (Union[str, Path]) -> List[str]
        '''
        Generates a complete list of filepaths given a root directory and
        filepath pattern.

        Args:
            root (str or Path): Directory containing asset.
            pattern (str): Filepath pattern.

        Returns:
            list[str]: List of filepaths.
        '''
        asset, filename = self.get_name_patterns()
        pattern = Path(asset, filename).as_posix()
        return self._to_filepaths(root, pattern)


class ComplexSpecificationBase(SpecificationBase):
    '''
    The base class for assets that consist of multiple directories of files.

    Attributes:
        asset_type (str): Complex.
    '''
    asset_type = 'complex'  # type: str
