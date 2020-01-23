#!/usr/bin/env python
"""
To refresh code coverage stats, get 'coverage' tool from
http://pypi.python.org/pypi/coverage/ and run this file with:

  coverage run run_tests.py
  coverage html -d coverage

"""
import sys
import unittest
import subprocess
from pathlib import Path

import patch

TESTDIR = Path(__file__).parent / 'test_patches'


def tf(name):
    return TESTDIR / name


def read(filename):
    with open(filename) as fp:
        return fp.read()


def readtf(filename):
    return read(tf(filename))


def can_patch(psfile, filename):
    ps = patch.fromfile(tf(psfile))
    return ps.can_patch(filename, readtf(filename))


class TestPatchFiles(unittest.TestCase):

    def _run_test(self, testname):
        """
        boilerplate for running *.patch file tests
        """
        patch_file = tf(testname)
        res = subprocess.run([
            sys.executable,
            TESTDIR.parent / "patch.py",
            f"{patch_file}.patch",
            f"{patch_file}.from"
        ], capture_output=True)

        if res.returncode != 0:
            print('{sep}\nReturn code: {code}\n{stderr}\n{sep}'.format(
                sep='%' * 40,
                code=res.returncode,
                stderr=res.stderr.decode(),
            ))

        self.assertEqual(res.returncode, 0, f"{testname}")

        data = read(f'{patch_file}.to').strip('\n')
        self.assertEqual(data, res.stdout.decode().strip('\n'))

    def test_02uni_newline(self):
        self._run_test('02uni_newline')

    def test_03trail_fname(self):
        self._run_test('03trail_fname')

    def test_04can_patch(self):
        self._run_test('04can_patch')


class TestCheckPatched(unittest.TestCase):

    def test_can_patch_single_source(self):
        self.assertTrue(can_patch("02uni_newline.patch", "02uni_newline.from"))

    def test_can_patch_fails_on_target_file(self):
        self.assertEqual(False, can_patch("03trail_fname.patch", "03trail_fname.to"))
        with self.assertRaises(FileNotFoundError):
            can_patch("03trail_fname.patch", "not_in_source.also")
   
    def test_single_false_on_other_file(self):
        self.assertFalse(can_patch("03trail_fname.patch", "03trail_fname.from"))

    def test_checks_source_filename_even_if_target_can_be_patched(self):
        self.assertFalse(can_patch("04can_patch.patch", "04can_patch.to"))


class TestPatchParse(unittest.TestCase):

    def test_fromstring(self):
        ps = patch.fromstring(readtf("02uni_newline.patch"))
        self.assertEqual(len(ps), 1)

    def test_fromfile(self):
        ps = patch.fromfile(tf("02uni_newline.patch"))
        self.assertNotEqual(ps, False)
        self.assertEqual(len(ps), 1)
        ps = patch.fromfile(tf("data/failing/not-a-patch.log"))
        self.assertFalse(ps)

    def test_no_header_for_plain_diff_with_single_file(self):
        ps = patch.fromfile(tf("03trail_fname.patch"))
        self.assertEqual(ps.patches[0].header, [])

    def test_hunk_desc(self):
        ps = patch.fromfile(tf('data/git-changed-file.diff'))
        self.assertEqual(ps.patches[0].hunks[0].desc, 'class JSONPluginMgr(object):')

    def test_fail_missing_hunk_line(self):
        data = readtf("data/failing/missing-hunk-line.diff")
        ps = patch.PatchSet()
        self.assertNotEqual(ps.parse(data), True)

    def test_fail_context_format(self):
        data = readtf("data/failing/context-format.diff")
        res = patch.PatchSet().parse(data)
        self.assertFalse(res)

    def test_fail_not_a_patch(self):
        data = readtf("data/failing/not-a-patch.log")
        res = patch.PatchSet().parse(data)
        self.assertFalse(res)


class TestPatchApply(unittest.TestCase):

    def test_apply_returns_false_on_failure(self):
        ps = patch.fromfile(tf('data/failing/non-empty-patch-for-empty-file.diff'))
        data = readtf('data/failing/upload.py')
        self.assertFalse(ps.apply(data))

    def test_apply_returns_true_on_success(self):
        ps = patch.fromfile(tf('03trail_fname.patch'))
        result = ps.apply(readtf('03trail_fname.from'))
        self.assertTrue(bool(result))
