import unittest
import dockergrader.run_tests
import dockergrader.config
import logging


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

    def test_container(self):
        run_test = dockergrader.run_tests.RunTest("testcase")

        containers_before = dockergrader.config.docker.containers(all=True,quiet=True)

        run_test.add_command(image="ubuntu", command="true", name="true")
        run_test.add_command(image="ubuntu", command="false", name="false")

        run_test.run_commands()

        assert run_test.containers["true"]["StatusCode"] == 0
        assert run_test.containers["false"]["StatusCode"] == 1

        run_test.cleanup()

        containers_after = dockergrader.config.docker.containers(all=True, quiet=True)

        # Make sure all containers are clenaed up
        assert containers_before == containers_after
