import os
TEST_DIR = os.path.expanduser("~/tests")
TERM = "fa16"

def container_name(mp,task,term=TERM):
	return "csece438/{}-{}:{}".format(mp,task,term)

from docker import Client
docker = Client()
