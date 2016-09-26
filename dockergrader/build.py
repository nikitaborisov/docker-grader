from . import config
import tarfile
from tempfile import NamedTemporaryFile, TemporaryFile
from pathlib import Path
import re
import logging

log = logging.getLogger(__name__)

BUILD_SUCCESSFUL = re.compile(r'Successfully built ([0-9a-f]+)')

def _parse_build_output(stream):
    output = list(stream)
    m = re.search(BUILD_SUCCESSFUL, output[-1].decode())
    if m:
        image = m.group(1)
        log.debug("Built image %s, output %s", m, output)
        return image
    else:
        log.error("Could not build image: %s", output)
        raise RuntimeError("Could not build image: {}".format(output))

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
