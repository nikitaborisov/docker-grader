from . import config
import tarfile
from tempfile import NamedTemporaryFile, TemporaryFile
from pathlib import Path
import re
import logging
import json

log = logging.getLogger(__name__)

BUILD_SUCCESSFUL = re.compile(r'Successfully built ([0-9a-f]+)')


class BuildError(Exception):
    def __init__(self, error, output):
        self.error = error
        self.output = output

def _parse_build_output(stream):
    decstream = list(json.loads(l) for s in stream for l in
                     s.decode().split('\n') if l)   # capture output
    output = [x["stream"] for x in decstream if "stream" in x]
    m = re.search(BUILD_SUCCESSFUL, output[-1])
    if m:
        image = m.group(1)
        log.debug("Built image %s, output %s", m, output)
        return image
    else:
        error = [x for x in decstream if "error" in x]
        if len(error) == 1:
            error = error[0]
        log.error("Could not build image: %s; %s", error, output)
        raise BuildError(error, output)


def build_custom_image(dockerfile_str, path, tag=None):
    """ Specifies a dockerfile as a string, and a path to create a custom context """
    with TemporaryFile() as context_file:
        tar = tarfile.open(fileobj=context_file, mode='w')
        path = Path(path)
        with NamedTemporaryFile('w') as dockerfile:
            dockerfile.write(dockerfile_str)
            dockerfile.flush()
            tar.add(dockerfile.name, arcname="Dockerfile")
        for name in path.glob("*"):
            tar.add(str(name), arcname=str(name.relative_to(path)))
        tar.close()
        context_file.seek(0)
        stream = config.docker.build(fileobj=context_file, custom_context=True,
                                     rm=True, tag=tag)

        return _parse_build_output(stream)


def build_image(path, tag=None):
    """ Builds an image for a path. This is just a simple wrapper around
    docker.Client.build, with output parsing added on """
    stream = config.docker.build(path=path, tag=tag, rm=True)
    return _parse_build_output(stream)
