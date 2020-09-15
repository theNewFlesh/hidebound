from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import OpenEXR as openexr
import skimage.io

import hidebound.core.traits as traits
# ------------------------------------------------------------------------------


class TraitsTests(unittest.TestCase):
    def write_exr(self, root, shape):
        x, y = shape
        header = openexr.Header(x, y)
        exr = root + '/foo.exr'
        output = openexr.OutputFile(exr, header)
        data = dict(
            R=np.ones((y, x, 1), dtype=np.float32).tobytes(),
            G=np.zeros((y, x, 1), dtype=np.float32).tobytes(),
            B=np.zeros((y, x, 1), dtype=np.float32).tobytes(),
        )
        output = openexr.OutputFile(exr, header)
        output.writePixels(data)
        return exr

    def test_get_image_width(self):
        with TemporaryDirectory() as root:
            img = np.zeros((2, 4, 3))
            filepath = Path(root, 'foo.png')
            skimage.io.imsave(filepath.as_posix(), img)
            result = traits.get_image_width(filepath)
            self.assertEqual(result, 4)

            filepath = self.write_exr(root, (4, 2))
            result = traits.get_image_width(filepath)
            self.assertEqual(result, 4)

    def test_get_image_height(self):
        with TemporaryDirectory() as root:
            img = np.zeros((2, 4, 3))
            filepath = Path(root, 'foo.png')
            skimage.io.imsave(filepath.as_posix(), img)
            result = traits.get_image_height(filepath)
            self.assertEqual(result, 2)

            filepath = self.write_exr(root, (4, 2))
            result = traits.get_image_height(filepath)
            self.assertEqual(result, 2)

    def test_get_image_channels(self):
        with TemporaryDirectory() as root:
            img = np.zeros((2, 4, 3))
            filepath = Path(root, 'foo.png')
            skimage.io.imsave(filepath.as_posix(), img)
            result = traits.get_image_channels(filepath)
            self.assertEqual(result, 3)

            img = np.zeros((2, 4))
            filepath = Path(root, 'bar.jpg')
            skimage.io.imsave(filepath.as_posix(), img)
            result = traits.get_image_channels(filepath)
            self.assertEqual(result, 1)

            filepath = self.write_exr(root, (4, 2))
            result = traits.get_image_channels(filepath)
            self.assertEqual(result, 3)
