import dockergrader.build
import dockergrader.config
from pathlib import Path
from subprocess import check_output
import unittest
import hashlib
import re


class BuildTestCase(unittest.TestCase):
    def test_build(self):
        mypath = Path(__file__).parent
        dockerfile_str = """
FROM alpine
RUN mkdir -p /a
COPY ./a /a
RUN mkdir -p /b
COPY ./b /b
    """
        image = dockergrader.build.build_custom_image(dockerfile_str,
                                                      {'a': mypath / 'goodmake',
                                                       'b': mypath / 'gccfail'})
        print(image)
        with (mypath / 'goodmake' / 'Makefile').open('rb') as goodmake:
            goodmake_digest = hashlib.sha1(goodmake.read()).hexdigest()
        with (mypath / 'gccfail' / 'Makefile').open('rb') as gccfail:
            gccfail_digest = hashlib.sha1(gccfail.read()).hexdigest()
        output = check_output(["docker", "run", "--rm", image, "sha1sum",
                               "/a/Makefile", "/b/Makefile"])
        pat = r'{}\s+/a/Makefile\n{}\s+/b/Makefile'.format(goodmake_digest,
                                                         gccfail_digest)
        assert re.match(pat, output.decode())
        dockergrader.config.docker.remove_image(image)


if __name__ == "__main__":
    unittest.main()
