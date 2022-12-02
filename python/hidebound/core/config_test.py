import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from schematics.exceptions import ValidationError, DataError

import hidebound.core.config as cfg
# ------------------------------------------------------------------------------


class ValidatorsTests(unittest.TestCase):
    def test_is_specification_file(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications1.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)
            cfg.is_specification_file(filepath)

    def test_import(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications2.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                BIG DUMB ERROR

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} could not be imported.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_has_specifications_attribute(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} has no SPECIFICATIONS attribute.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_is_specification_file_not_list(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications4.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = {'spec001': Spec001}'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} SPECIFICATIONS attribute is not '
            expected += 'a list.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_is_specification_file_bad_subclasses(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications5.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001:
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = 'are not subclasses of SpecificationBase.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)


# CONFIG------------------------------------------------------------------------
class ConfigTests(unittest.TestCase):
    def write_good_spec(self, temp):
        filepath = Path(temp, 'good_spec.py')

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.core.specification_base import SpecificationBase

            class Spec001(SpecificationBase):
                foo = ListType(IntType(), required=True)
                bar = ListType(StringType(), required=True)

            SPECIFICATIONS = [Spec001]'''
        text = re.sub('            ', '', text)
        with open(filepath, 'w') as f:
            f.write(text)
        return filepath.as_posix()

    def write_bad_spec(self, temp):
        filepath = Path(temp, 'bad_spec.py')

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.core.specification_base import SpecificationBase

            class Spec001(SpecificationBase):
                foo = ListType(IntType(), required=True)
                bar = ListType(StringType(), required=True)

            SPECIFICATIONS = ['Foobar']'''
        text = re.sub('            ', '', text)
        with open(filepath, 'w') as f:
            f.write(text)
        return filepath.as_posix()

    def set_data(self, temp):
        self.ingress = Path(temp, 'root').as_posix()
        self.staging = Path(temp, 'hidebound').as_posix()
        self.target_dir = Path(temp, 'target').as_posix()
        self.config = dict(
            ingress_directory=self.ingress,
            staging_directory=self.staging,
            specification_files=[],
            include_regex='foo',
            exclude_regex='bar',
            write_mode='copy',
            dask={},
            workflow=['update', 'create', 'export', 'delete'],
        )
    # --------------------------------------------------------------------------

    def test_config(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)
            cfg.Config(self.config).validate()

    def test_config_root(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.staging)

            expected = 'ingress_directory.*is not a directory or does not exist'
            with self.assertRaisesRegex(DataError, expected):
                cfg.Config(self.config).validate()

    def test_config_staging(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)

            expected = 'staging_directory.*is not a directory or does '
            expected += 'not exist'
            with self.assertRaisesRegex(DataError, expected):
                cfg.Config(self.config).validate()

    def test_write_mode(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)

            self.config['write_mode'] = 'copy'
            cfg.Config(self.config).validate()

            self.config['write_mode'] = 'move'
            cfg.Config(self.config).validate()

            self.config['write_mode'] = 'shuffle'
            expected = r"shuffle is not in \['copy', 'move'\]"
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_specification_files_good(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)

            spec = self.write_good_spec(temp)
            self.config['specification_files'] = [spec]

            cfg.Config(self.config).validate()

    def test_specification_files_bad(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)

            good = self.write_good_spec(temp)
            bad = self.write_bad_spec(temp)
            self.config['specification_files'] = [good, bad]

            expected = 'Foobar.* are not subclasses of SpecificationBase'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_workflow(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)

            expected = 'bar.*foo.*are not legal workflow steps'
            self.config['workflow'] = ['create', 'foo', 'update', 'bar']
            with self.assertRaisesRegex(DataError, expected):
                cfg.Config(self.config).validate()

    # EXPORTERS-----------------------------------------------------------------
    def add_exporters_to_config(self, root):
        self.set_data(root)
        os.makedirs(self.ingress)
        os.makedirs(self.staging)
        self.config['exporters'] = [
            dict(
                name='girder',
                api_key='api_key',
                root_id='root_id',
                root_type='collection',
                host='http://1.0.1.0',
                port=2020,
                metadata_types=['asset', 'file'],
            ),
            dict(
                name='s3',
                access_key='foo',
                secret_key='bar',
                bucket='bucket',
                region='us-west-2',
                metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk'],
            ),
            dict(
                name='disk',
                target_directory=self.target_dir,
                metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk'],
            )
        ]

    def test_exporters(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            cfg.Config(self.config).validate()

    def test_exporters_bad_girder(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            self.config['exporters'][0]['root_type'] = 'pizza'
            expected = r"pizza is not in \[\'collection\', \'folder\'\]"
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()
            self.config['exporters'][0]['root_type'] = 'collection'

    def test_exporters_bad_s3(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            self.config['exporters'][1]['bucket'] = 'BadBucket'
            expected = 'is not a valid bucket name'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_exporters_bad_disk(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            self.config['exporters'][2]['target_directory'] = 'bad/dir'
            expected = 'is not a legal directory path.'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_exporters_bad_config(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            self.config['exporters'] = [dict(bagel='lox')]
            expected = 'Rogue field'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_exporters_no_girder(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            del self.config['exporters'][0]
            expected = self.config['exporters']
            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['exporters']
            self.assertEqual(result, expected)

    def test_exporters_no_s3(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            del self.config['exporters'][1]
            expected = self.config['exporters']
            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['exporters']
            self.assertEqual(result, expected)

    def test_exporters_no_disk(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            del self.config['exporters'][2]
            expected = self.config['exporters']
            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['exporters']
            self.assertEqual(result, expected)

    def test_exporters_empty(self):
        with TemporaryDirectory() as root:
            self.add_exporters_to_config(root)
            del self.config['exporters']
            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['exporters']
            self.assertEqual(result, [])

    # WEBHOOKS------------------------------------------------------------------
    def add_webhooks_to_config(self, root):
        self.set_data(root)
        os.makedirs(self.ingress)
        os.makedirs(self.staging)
        self.config['webhooks'] = [
            dict(
                url='http://foobar.com/api/user?',
                method='get',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                params=dict(
                    id='123',
                    other=dict(
                        stuff='things'
                    )
                )
            ),
            dict(
                url='http://foobar.com/api/user?',
                method='put',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                data=dict(
                    id='123',
                    name='john',
                )
            ),
            dict(
                url='http://foobar.com/api/user?',
                method='post',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                data=dict(
                    id='123',
                    name='john',
                ),
                json=dict(
                    foo='bar'
                )
            )
        ]

    def test_webhooks(self):
        with TemporaryDirectory() as temp:
            self.add_webhooks_to_config(temp)
            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['webhooks']
            self.assertEqual(result, self.config['webhooks'])

    def test_webhooks_empty(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.ingress)
            os.makedirs(self.staging)

            result = cfg.Config(self.config)
            result.validate()
            result = result.to_primitive()['webhooks']
            self.assertEqual(result, [])

    def test_webhooks_url(self):
        with TemporaryDirectory() as temp:
            self.add_webhooks_to_config(temp)
            self.config['webhooks'][0]['url'] = 'not-valid-url.com'
            expected = 'Not a well-formed URL.'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

            # allow invalid fqdns for kubernetes
            self.config['webhooks'][0]['url'] = 'http://foo.invalid-fqdn/bar'
            cfg.Config(self.config).validate()

    def test_webhooks_method(self):
        with TemporaryDirectory() as temp:
            self.add_webhooks_to_config(temp)
            self.config['webhooks'][0]['method'] = 'trace'
            expected = 'trace is not a legal HTTP method.'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()
