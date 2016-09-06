TEST_IMAGE="nikitab/dockergrader-testcompile"

import unittest
import unittest.mock
import dockergrader.compile
import dockergrader.config
import tempfile
import os
import sys
import pathlib

class TestCompile(unittest.TestCase):
    @unittest.mock.patch('dockergrader.config.container_name', return_value=TEST_IMAGE)
    def test_compile(self, cont_func):
        mypath = os.path.dirname(os.path.realpath(__file__))
        with tempfile.TemporaryDirectory() as tmpdir:
            if sys.platform == "darwin" and tmpdir.startswith("/var"):
                realtmpdir = "/private" + tmpdir # hack to get around docker.mac mount issues
            else:
                realtmpdir = tmpdir
            ret = dockergrader.compile.compile(mypath + "/goodmake", realtmpdir, "testmp")
            assert ret is True
            assert (pathlib.Path(realtmpdir) / 'compile' / 'testfile').exists()
            assert cont_func.call_args[0][0] == "testmp"

        # FIXME: DRY
        with tempfile.TemporaryDirectory() as tmpdir:
            if sys.platform == "darwin" and tmpdir.startswith("/var"):
                realtmpdir = "/private" + tmpdir # hack to get around docker.mac mount issues
            else:
                realtmpdir = tmpdir
            ret = dockergrader.compile.compile(mypath + "/nomakefile", realtmpdir, "testmp")
            assert ret is False

        with tempfile.TemporaryDirectory() as tmpdir:
            if sys.platform == "darwin" and tmpdir.startswith("/var"):
                realtmpdir = "/private" + tmpdir # hack to get around docker.mac mount issues
            else:
                realtmpdir = tmpdir
            ret = dockergrader.compile.compile(mypath + "/gccfail", realtmpdir, "testmp")
            assert ret is False


if __name__ == "__main__":
    unittest.main()
