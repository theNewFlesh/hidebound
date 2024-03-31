from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from moto import mock_aws
from schematics.exceptions import DataError
import boto3 as boto

from hidebound.exporters.s3_exporter import S3Config, S3Exporter
# ------------------------------------------------------------------------------


class S3ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(
            name='s3',
            access_key='foo',
            secret_key='bar',
            bucket='bucket',
            region='us-west-2',
        )

    def test_validate(self):
        S3Config(self.config).validate()

    def test_name(self):
        self.config['name'] = 'foobar'
        with self.assertRaises(DataError):
            S3Config(self.config).validate()

    def test_bucket(self):
        self.config['bucket'] = 'BadBucket'
        with self.assertRaises(DataError):
            S3Config(self.config).validate()

    def test_region(self):
        self.config['region'] = 'us-west-3'
        with self.assertRaises(DataError):
            S3Config(self.config).validate()
# ------------------------------------------------------------------------------


class S3ExporterTests(unittest.TestCase):
    @mock_aws
    def setUp(self):
        self.config = dict(
            name='s3',
            access_key='foo',
            secret_key='bar',
            bucket='bucket',
            region='us-west-2',
        )
        self.s3 = boto.session.Session(
            aws_access_key_id=self.config['access_key'],
            aws_secret_access_key=self.config['secret_key'],
            region_name=self.config['region'],
        ).resource('s3')
        self.bucket = self.s3.Bucket(self.config['bucket'])

    @mock_aws
    def test_from_config(self):
        result = S3Exporter.from_config(self.config)
        self.assertIsInstance(result, S3Exporter)

    @mock_aws
    def test_init(self):
        S3Exporter(**self.config)
        buckets = self.s3.buckets.all()
        buckets = [x.name for x in buckets]
        self.assertIn(self.config['bucket'], buckets)
        self.assertEqual(len(buckets), 1)

    @mock_aws
    def test_init_with_bucket(self):
        result = list(self.s3.buckets.all())
        self.assertEqual(result, [])

        S3Exporter(**self.config)
        buckets = self.s3.buckets.all()
        buckets = [x.name for x in buckets]
        self.assertIn(self.config['bucket'], buckets)
        self.assertEqual(len(buckets), 1)

        S3Exporter(**self.config)
        buckets = self.s3.buckets.all()
        buckets = [x.name for x in buckets]
        self.assertIn(self.config['bucket'], buckets)
        self.assertEqual(len(buckets), 1)

    @mock_aws
    def test_export_asset(self):
        exporter = S3Exporter(**self.config)
        id_ = 'abc123'
        expected = dict(asset_id=id_, foo='bar')
        exporter._export_asset(expected)

        with TemporaryDirectory() as root:
            file_ = Path(root, f'{id}.json')
            with open(file_, 'wb') as f:
                self.bucket.download_fileobj(
                    f'hidebound/metadata/asset/{id_}.json',
                    f
                )
            with open(file_, 'r') as f:
                self.assertEqual(json.load(f), expected)

    @mock_aws
    def test_export_content(self):
        with TemporaryDirectory() as root:
            n = 'p-proj001_spec001_d-desc_v001'
            rel_path = f'projects/proj001/spec001/{n}/{n}_f0000.json'
            filepath = Path(root, rel_path)

            content = {'foo': 'bar'}
            os.makedirs(filepath.parent, exist_ok=True)
            with open(Path(root, filepath), 'w') as f:
                json.dump(content, f)

            exporter = S3Exporter(**self.config)
            id_ = 'abc123'
            expected = dict(
                file_id=id_,
                foo='bar',
                filepath=filepath.as_posix(),
                filepath_relative=rel_path,
            )
            exporter._export_content(expected)

            # content
            file_ = Path(root, 'content.json')
            with open(file_, 'wb') as f:
                self.bucket.download_fileobj(f'hidebound/content/{rel_path}', f)
            with open(file_, 'r') as f:
                self.assertEqual(json.load(f), content)

    @mock_aws
    def test_export_file(self):
        with TemporaryDirectory() as root:
            n = 'p-proj001_spec001_d-desc_v001'
            rel_path = f'projects/proj001/spec001/{n}/{n}_f0000.json'
            filepath = Path(root, rel_path)

            content = {'foo': 'bar'}
            os.makedirs(filepath.parent, exist_ok=True)
            with open(Path(root, filepath), 'w') as f:
                json.dump(content, f)

            exporter = S3Exporter(**self.config)
            id_ = 'abc123'
            expected = dict(
                file_id=id_,
                foo='bar',
                filepath=filepath.as_posix(),
                filepath_relative=rel_path,
            )
            exporter._export_file(expected)

            # metadata
            file_ = Path(root, 'metadata.json')
            with open(file_, 'wb') as f:
                self.bucket.download_fileobj(
                    f'hidebound/metadata/file/{id_}.json',
                    f
                )
            with open(file_, 'r') as f:
                self.assertEqual(json.load(f), expected)

    @mock_aws
    def test_export_asset_chunk(self):
        exporter = S3Exporter(**self.config)
        expected = [
            dict(foo='bar'),
            dict(pizza='taco'),
        ]
        exporter._export_asset_chunk(expected)

        keys = [x.key for x in self.bucket.objects.all()]
        key = list(filter(lambda x: 'asset-chunk' in x, keys))[0]
        with TemporaryDirectory() as root:
            temp = Path(root, 'temp.json')
            with open(temp, 'wb') as f:
                self.bucket.download_fileobj(key, f)
            with open(temp, 'r') as f:
                self.assertEqual(json.load(f), expected)

    @mock_aws
    def test_export_file_chunk(self):
        exporter = S3Exporter(**self.config)
        expected = [
            dict(foo='bar'),
            dict(pizza='taco'),
        ]
        exporter._export_file_chunk(expected)

        keys = [x.key for x in self.bucket.objects.all()]
        key = list(filter(lambda x: 'file-chunk' in x, keys))[0]
        with TemporaryDirectory() as root:
            temp = Path(root, 'temp.json')
            with open(temp, 'wb') as f:
                self.bucket.download_fileobj(key, f)
            with open(temp, 'r') as f:
                self.assertEqual(json.load(f), expected)
