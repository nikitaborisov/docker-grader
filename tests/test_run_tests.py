import unittest
import dockergrader.run_tests
import dockergrader.config


class TestRunTests(unittest.TestCase):
    def test_network_create(self):
        run_test = dockergrader.run_tests.RunTest("testcase")

        for internal in [True,False]:
            # Check network creation
            run_test.create_network(internal=internal)
            networks = {n["Name"]:n for n in
                dockergrader.config.docker.networks()}
            assert run_test.network_name in networks
            assert networks[run_test.network_name]["Internal"] == internal

            # Check network removal
            run_test.remove_network()
            networks = {n["Name"]:n for n in
                dockergrader.config.docker.networks()}
            assert run_test.network_name not in networks
