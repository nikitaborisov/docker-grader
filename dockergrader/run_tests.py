from . import config
import logging


class RunTest:

    def __init__(self, testcase_name):
        self.testcase_name = testcase_name
        self.containers = {}
        self.network = None

    @property
    def network_name(self):
        return "dockergrader-testnet-{}".format(self.testcase_name)

    def create_network(self, internal=False):
        self.network = config.docker.create_network(
            self.network_name, internal=internal)

    def remove_network(self):
        config.docker.remove_network(self.network["Id"])

    def add_command(self, image, command, name=None, ports=None, binds=[]):
        """
        Arguments:
            `binds`  a list of docker-style "-v" parameters; e.g., /tmp/foo:/bar:rw
        """
        host_config = None
        container_name = "{}-{}-{}".format(self.testcase_name, len(self.containers), name)
        if binds:
            # FIXME: do copies
            host_config = config.docker.create_host_config(binds=binds)
        network_config = None
        if self.network:
            network_config = config.docker.create_networking_config({
                self.network_name: config.docker.create_endpoint_config()})
        container = config.docker.create_container(
            image=image,
            command=command,
            name=container_name,
            ports=ports,
            host_config=host_config,
            networking_config = network_config)
        logging.debug("Created container: %s", container)
        self.containers[name] = container

    def run_commands(self, timeout=None):
        for container in self.containers.values():
            config.docker.start(container["Id"])
            logging.debug("Started container: %s", container["Id"])

        logging.debug("Waiting for containers to finish")
        for container in self.containers.values():
            container["StatusCode"] = config.docker.wait(container["Id"], timeout)
        logging.debug("Containers are done")

    def cleanup(self):
        for container in self.containers.values():
            config.docker.remove_container(container["Id"])
        if self.network:
            self.remove_network()
