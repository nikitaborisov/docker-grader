TEST_IMAGE="nikitab/dockergrader-testcompile"

import unittest
import unittest.mock
import dockergrader.compile
import dockergrader.config
import tempfile
import os

class TestCompile(unittest.TestCase):
    @unittest.mock.patch('dockergrader.config.container_name', return_value=TEST_IMAGE)
    def test_compile(self, cont_func):
        mypath = os.path.dirname(os.path.realpath(__file__))
        with tempfile.TemporaryDirectory() as tmpdir:
            ret = dockergrader.compile.compile(mypath + "/goodmake", tmpdir, "testmp")
        assert ret["Warnings"] is None
        assert cont_func.call_args[0][0] == "testmp"

if __name__ == "__main__":
    unittest.main()
