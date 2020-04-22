from copy import copy
from pyparsing import delimitedList, Group, Optional, Or, ParseException, Regex, Suppress
# ------------------------------------------------------------------------------


class AssetNameParser:
    '''
    A class for converting asset names to metadata and metadata to asset names,
    according to a dynimcally defined grammar.
    '''
    FIELD_SEPARATOR = '_'
    TOKEN_SEPARATOR = '-'
    PROJECT_INDICATOR = 'p' + TOKEN_SEPARATOR
    SPECIFICATION_INDICATOR = 's' + TOKEN_SEPARATOR
    DESCRIPTOR_INDICATOR = 'd' + TOKEN_SEPARATOR
    VERSION_INDICATOR = 'v'
    COORDINATE_INDICATOR = 'c'
    FRAME_INDICATOR = 'f'
    EXTENSION_INDICATOR = '.'
    LEGAL_FIELDS = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension'
    ]

    VERSION_PADDING = 3
    COORDINATE_PADDING = 3
    FRAME_PADDING = 4

    def __init__(self, fields):
        '''
        Create a AssetNameParser instance with given fields.

        Args:
            fields (list[str]): An ordered list of asset fields.

        Raises:
            ValueError: If fields is empty.
            ValueError: If fields are duplicated.
            ValueError: If illegal fields are given.
            ValueError: If illegal field order given.

        Returns:
            AssetNameParser: instance.
        '''
        # ensure fields is not empty
        if len(fields) == 0:
            msg = 'Fields cannot be empty.'
            raise ValueError(msg)

        # ensure fields are ot duplicated
        if len(fields) != len(set(fields)):
            msg = 'Fields cannot contain duplicates.'
            raise ValueError(msg)

        # ensure fields are legal
        illegal_fields = list(filter(lambda x: x not in self.LEGAL_FIELDS, fields))
        if len(illegal_fields) > 0:
            msg = f'Illegal fields found: {illegal_fields}. '
            msg += f'Legal fields include: {self.LEGAL_FIELDS}.'
            raise ValueError(msg)

        # ensure extension is last field
        if 'extension' in fields and fields[-1] != 'extension':
            msg = 'Illegal field order: Extension field must be last if it is included in fields.'
            raise ValueError(msg)

        self._fields = fields

    @staticmethod
    def _raise_field_error(field, part):
        def raise_error(field, string, instance):
            expr = None
            if hasattr(instance, 'expr'):
                expr = instance.expr
            else:
                expr = instance.pattern

            msg = f'Illegal {field} field {part} in "{string}". '
            msg += f'Expecting: {expr}'
            raise ParseException(msg)
        return lambda s, l, i, e: raise_error(field, s, i)

    def parse(self, string, ignore_order=False):
        '''
        Create a parser based on the given fields.

        Args:
            fields (list[str]): A list of fields.
            ignore_order (bool, optional): Whether to ignore the field order.
                Default: False.

        Returns:
            Group: parser.
        '''
        fields = copy(self._fields)

        # setup grammar
        field_sep = Suppress(self.FIELD_SEPARATOR)
        # ----------------------------------------------------------------------

        project = Regex(r'[a-z]{3,4}\d{1,3}')\
            .setResultsName('project')\
            .setFailAction(self._raise_field_error('project', 'token'))

        specification = Regex(r'[a-z]{3,4}\d\d\d')\
            .setResultsName('specification')\
            .setFailAction(self._raise_field_error('specification', 'token'))

        descriptor = Regex(r'[a-z0-9][a-z0-9-]*')\
            .setResultsName('descriptor')\
            .setFailAction(self._raise_field_error('descriptor', 'token'))

        version = Regex(r'\d{' + str(self.VERSION_PADDING) + '}')\
            .setParseAction(lambda s, l, t: int(t[0]))\
            .setResultsName('version')\
            .setFailAction(self._raise_field_error('version', 'token'))

        coord = Regex(r'\d{' + str(self.COORDINATE_PADDING) + '}')\
            .setParseAction(lambda s, l, t: int(t[0]))
        t_sep = Suppress(self.TOKEN_SEPARATOR)
        coordinate = Group(coord + Optional(t_sep + coord) + Optional(t_sep + coord))\
            .setResultsName('coordinate')\
            .setFailAction(self._raise_field_error('coordinate', 'token'))

        frame = Regex(r'\d{' + str(self.FRAME_PADDING) + '}')\
            .setParseAction(lambda s, l, t: int(t[0]))\
            .setResultsName('frame')\
            .setFailAction(self._raise_field_error('frame', 'token'))

        extension = Regex(r'[a-zA-Z0-9]+')\
            .setResultsName('extension')\
            .setFailAction(self._raise_field_error('extension', 'token'))
        # ----------------------------------------------------------------------

        project_indicator = Suppress(self.PROJECT_INDICATOR)\
            .setFailAction(self._raise_field_error('project', 'indicator'))

        specification_indicator = Suppress(self.SPECIFICATION_INDICATOR)\
            .setFailAction(self._raise_field_error('specification', 'indicator'))

        descriptor_indicator = Suppress(self.DESCRIPTOR_INDICATOR)\
            .setFailAction(self._raise_field_error('descriptor', 'indicator'))

        version_indicator = Suppress(self.VERSION_INDICATOR)\
            .setFailAction(self._raise_field_error('version', 'indicator'))

        coordinate_indicator = Suppress(self.COORDINATE_INDICATOR)\
            .setFailAction(self._raise_field_error('coordinate', 'indicator'))

        frame_indicator = Suppress(self.FRAME_INDICATOR)\
            .setFailAction(self._raise_field_error('frame', 'indicator'))

        extension_indicator = Suppress(self.EXTENSION_INDICATOR)\
            .setFailAction(self._raise_field_error('extension', 'indicator'))
        # ----------------------------------------------------------------------

        lut = {
            'project': project_indicator + project,
            'specification': specification_indicator + specification,
            'descriptor': descriptor_indicator + descriptor,
            'version': version_indicator + version,
            'coordinate': coordinate_indicator + coordinate,
            'frame': frame_indicator + frame,
            'extension': extension_indicator + extension,
        }

        # if only extension was given
        if fields == ['extension']:
            return Group(extension).parseString(string)[0].asDict()

        # create unordered parser
        has_ext = fields[-1] == 'extension'
        if has_ext:
            fields.pop()

        field = Or([lut[x] for x in fields])
        unordered_parser = delimitedList(field, delim=self.FIELD_SEPARATOR)
        if has_ext:
            unordered_parser += lut['extension']
        unordered_parser = Group(unordered_parser)

        # create ordered parser
        last = fields.pop()
        temp = []
        for field in fields:
            temp.append(lut[field])
            temp.append(field_sep)
        temp.append(lut[last])

        if has_ext:
            temp.append(lut['extension'])

        parser = Suppress(Regex('^'))
        for item in temp:
            parser += item
        parser += Suppress(Regex('$'))

        parser = Group(parser)

        # parse string
        if ignore_order:
            return unordered_parser.parseString(string)[0].asDict()

        else:
            try:
                unordered_parser.parseString(string)
                parsable = True
            except ParseException:
                parsable = False

            try:
                return parser.parseString(string)[0].asDict()
            except ParseException as msg:
                if parsable:
                    msg = f'Incorrect field order in "{string}". '
                    msg += f'Given field order: {self._fields}.'
                raise ParseException(msg)

    def to_string(self, dict_):
        '''
        Converts a given dictionary to a string.

        Args:
            dict_ (dict): Dictionary.

        Returns:
            str: Asset name.
        '''
        fields = copy(self._fields)
        has_extension = False
        if fields[-1] == 'extension':
            has_extension = True
            fields.pop()

        output = []
        for field in fields:
            if field in dict_.keys():
                indicator = getattr(self, field.upper() + '_INDICATOR')

                token = dict_[field]
                if field == 'version':
                    token = str(token).zfill(self.VERSION_PADDING)

                elif field == 'coordinate':
                    token = [str(x).zfill(self.COORDINATE_PADDING) for x in token]
                    token = self.TOKEN_SEPARATOR.join(token)

                elif field == 'frame':
                    token = str(token).zfill(self.FRAME_PADDING)

                output.append(indicator + token)
        output = self.FIELD_SEPARATOR.join(output)

        if has_extension:
            output += self.EXTENSION_INDICATOR + dict_['extension']
        return output
