from . import config
import logging
import time
from collections import OrderedDict
import random


class RunTest:

    def __init__(self, testcase_name):
        self.testcase_name = testcase_name
        self.containers = OrderedDict()
        self.network = None
        self.network_name = "dockergrader-testnet-{}-{:05x}".format(
            self.testcase_name, random.randrange(2**20))

    def create_network(self, internal=False):
        self.network = config.docker.create_network(
            self.network_name, internal=internal)

    def remove_network(self):
        config.docker.remove_network(self.network["Id"])

    def add_command(self, image, command, name=None, ports=None, binds=[], caps=[]):
        """
        Arguments:
            `binds`  a list of docker-style "-v" parameters; e.g., /tmp/foo:/bar:rw
        """
        host_config = None
        if not name:
            name = "{}-{}".format(self.testcase_name, len(self.containers))
        if binds or caps:
            # FIXME: do copies
            host_config = config.docker.create_host_config(binds=binds, cap_add=caps)
        network_config = None
        if self.network:
            network_config = config.docker.create_networking_config({
                self.network_name: config.docker.create_endpoint_config()})
        container = config.docker.create_container(
            image=image,
            command=command,
            name=name,
            ports=ports,
            host_config=host_config,
            networking_config=network_config)
        logging.debug("Created container: %s", container)
        self.containers[name] = container

    def run_commands(self, timeout=None, nowait=[], delay=10):
        for i, container in enumerate(self.containers.values()):
            if i > 0:
                # sleep between starting containers to ensure
                # they have time to start up
                time.sleep(delay)
            config.docker.start(container["Id"])
            logging.debug("Started container: %s", container["Id"])

        logging.debug("Waiting for containers to finish")
        for name, container in self.containers.items():
            if name in nowait:
                continue
            try:
                container["StatusCode"] = config.docker.wait(
                    container["Id"], timeout)
            except:
                logging.info("Exception waiting for container %s",
                             container["Id"])
                container["StatusCode"] = -1
                config.docker.stop(container["Id"])
        for name in nowait:
            logging.debug("Stopping container %s", self.containers[name]["Id"])
            config.docker.stop(self.containers[name]["Id"])
        logging.debug("Containers are done")

    def logs(self, name):
        return config.docker.logs(self.containers[name]["Id"])

    def cleanup(self):
        for container in self.containers.values():
            config.docker.remove_container(container["Id"], force=True)
        if self.network:
            self.remove_network()
