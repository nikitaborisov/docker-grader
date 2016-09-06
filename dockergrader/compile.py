import config
import shutil
import os
from pathlib import Path

def compile(src, dst, mp):
    shutil.copytree(src, dst + "/compile")

    ret = config.docker.create_container(image=config.container_name(mp,"compile"), 
        host_config=config.docker.create_host_config(binds={ os.path.abspath(dst + "/compile"): { 'bind': "/compile", 'mode': 'rw' }}))
    return ret

if __name__ == "__main__":
    import sys
    src,dst,mp = sys.argv[1:]
    print(compile(src, dst, mp))
