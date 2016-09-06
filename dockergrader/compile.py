from . import config
import shutil
import os
import logging
from requests.exceptions import ReadTimeout
from pathlib import Path

def compile(src, dst, mp, timeout=config.TIMEOUT):
    shutil.copytree(src, dst + "/compile")

    container = config.docker.create_container(image=config.container_name(mp,"compile"),
        host_config=config.docker.create_host_config(binds={ os.path.abspath(dst + "/compile"): { 'bind': "/compile", 'mode': 'rw' }}))
    if not container["Warnings"] is None:
        logging.warning("Warning starting container: {}".format(container["Warnings"]))
    config.docker.start(container["Id"])
    try:
        exitCode = config.docker.wait(container["Id"], timeout=timeout)
    except ReadTimeout: # timeout
        logging.warning("Timeout running compilation")
        return False
    return exitCode == 0

if __name__ == "__main__":
    import sys
    src,dst,mp = sys.argv[1:]
    print(compile(src, dst, mp))
