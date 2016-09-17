from . import config

class RunTest:
    def __init__(self, testcase_name):
        self.testcase_name = testcase_name

    @property
    def network_name(self):
        return "dockergrader-testnet-{}".format(self.testcase_name)

    def create_network(self, internal=False):
        self.network = config.docker.create_network(self.network_name, internal=internal)

    def remove_network(self):
        config.docker.remove_network(self.network["Id"])
