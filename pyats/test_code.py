import logging
from pyats import aetest
from pydantic import ValidationError
from restsession.exceptions import (InvalidParameterError, InitializationError)
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

# from restsession import HttpSessionClass, HttpSessionSingletonClass

logger = logging.getLogger(__name__)

normal_class: None
singleton_class: None


def get_class(path, class_name):
    logger.info(sys.modules[path])
    return getattr(sys.modules[path], class_name)


class TestObjectCreation(aetest.Testcase):
    @aetest.test
    def test_object_is_not_singleton(self):
        test_class = self.parameters["test_class"]
        if "Singleton" not in str(test_class):
            test_instance = test_class()
            if hasattr(test_instance.__class__, "_instances"):
                test_instance.__class__._instances = {}

            object_one = test_class()
            object_two = test_class()

            logger.info("Object one: %s", object_one)
            logger.info("Object two: %s", object_two)

            assert object_one is not object_two
        else:
            self.skipped("Singleton class received as a param - not testing...")

    @aetest.test
    def test_object_is_singleton(self):
        test_class = self.parameters["test_class"]
        if "Singleton" in str(test_class):
            test_instance = test_class()
            if hasattr(test_instance.__class__, "_instances"):
                test_instance.__class__._instances = {}

            object_one = test_class()
            object_two = test_class()

            logger.info("Object one: %s", object_one)
            logger.info("Object two: %s", object_two)

            assert object_one is object_two

            logger.info("Dir of object is:\n%s", dir(object_one))
            logger.info("Current count of instances: %s", test_instance.__class__._instances)
            test_class._instances = {}
            logger.info("Current count of instances: %s", test_instance.__class__._instances)
        else:
            self.skipped("Non-singleton class received as param - not testing.")


class TestObjectParameters(aetest.Testcase):
    @aetest.test
    def test_object_with_context_manager(self, default_parameters):
        test_class = self.parameters["test_class"]
        if hasattr(test_class.__class__, "_instances"):
            test_class.__class__._instances = {}

        with test_class() as class_instance:
            if hasattr(test_class, "_instances"):
                logger.info("Instances: %s", test_class._instances)
                assert test_class._instances != {}
            non_hook_params = {k: v for k, v in class_instance._session_params.dict().items() if k in default_parameters}
            assert non_hook_params == default_parameters

        if hasattr(class_instance.__class__, "_instances"):
            assert test_class.__class__._instances == {}

    @aetest.test
    def test_default_parameters(self, default_parameters):
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        try:
            logger.info("Calling test class '%s' with no parameters", str(test_class))
            test_result = test_class()
            object_parameters = test_result._session_params.model_dump()
            non_hook_params = {k: v for k, v in object_parameters.items() if k in default_parameters}
            logger.info("Expecting parameters:\n%s", default_parameters)
            logger.info("Retrieved object parameters:\n%s", non_hook_params)

            assert non_hook_params == default_parameters, "Defaults not set"
        except (InitializationError, InvalidParameterError):
            self.failed("Exception caught on expected valid input")
        except ValidationError:
            self.failed("Pydantic ValidationError caught on valid input")
        else:
            self.passed("Params retrieves")

    @aetest.test
    def test_custom_parameters(self, default_parameters, custom_parameters):
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        try:
            logger.info("Calling test class '%s' with custom parameters:\n%s", str(test_class), custom_parameters)
            test_result = test_class()
            for param_name, param_val in custom_parameters.items():
                setattr(test_result, param_name, param_val)
            object_parameters = test_result._session_params.model_dump()
            non_hook_params = {k: v for k, v in object_parameters.items() if k in default_parameters}
            logger.info("Expecting parameters:\n%s", custom_parameters)
            logger.info("Retrieved object parameters:\n%s", non_hook_params)

            assert non_hook_params == custom_parameters, "Custom params not set"
            logger.info("URL is: %s", test_result._session_params.base_url)
        except (InitializationError, InvalidParameterError):
            self.failed("Exception caught on expected valid input")
        except ValidationError:
            self.failed("Pydantic ValidationError caught on valid input")
        else:
            # self.passed(f"Params retrieves")
            if "Singleton" in str(test_class):
                logger.info("Double checking singleton.")
                logger.info("Calling test class '%s' with default parameters:\n%s", str(test_class), default_parameters)
                new_result = test_class()
                new_result.timeout = custom_parameters["timeout"]
                new_params = new_result._session_params.model_dump()
                non_hook_params = {k: v for k, v in new_params.items() if k in default_parameters}
                # new_result.timeout = 6
                logger.info("Got new object params:\n%s", new_params)
                logger.info("Explicit retrieve of timeout: %s", new_result.timeout)
                assert non_hook_params == custom_parameters, "No match on second instance"
                assert new_result is test_result, "Not a singleton."
            self.passed("Params retrieved")

    @aetest.test
    def test_bad_parameters(self, invalid_parameters, default_parameters):
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        try:
            logger.info("Calling test class '%s' with parameters:\n%s", str(test_class), invalid_parameters)
            test_result = test_class(**invalid_parameters)
            # object_parameters = test_result._session_params.dict()
            # non_hook_params = {k: v for k, v in object_parameters.items() if k in default_parameters}
            # logger.info("Expecting parameters:\n%s", default_parameters)
            # logger.info("Retrieved object parameters:\n%s", non_hook_params)
            #
            # assert non_hook_params == default_parameters, "Defaults not set"
        except (InitializationError, InvalidParameterError) as err:
            self.passed(f"Exception caught on expected valid input:\n{err}")
        # except ValidationError:
        #     self.passed("Pydantic ValidationError caught on valid input")
        # except Exception as err:
        #     self.passed(f"Exception was raised when invalid parameters were passed:\n{err}")
        else:
            self.failed("Bad parameters did NOT generate an exception!")


class TestObjectAttributes(aetest.Testcase):
    @aetest.setup
    def mark_test_for_looping(self, custom_parameters):
        aetest.loop.mark(self.test_object_attributes,
                         attribute_kv_pairs=[(k, v) for k, v in custom_parameters.items()])

    @aetest.test
    def test_object_attributes(self, section, attribute_kv_pairs):
        section.uid = f"test_object_attributes-{attribute_kv_pairs[0]}"
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        try:
            attr_name, attr_value = attribute_kv_pairs
            test_result = test_class()
            setattr(test_result, attr_name, attr_value)
            assert getattr(test_result, attr_name) == attr_value, "Value doesn't match"
        except AttributeError:
            self.failed("Invalid attribute: %s", attr_name)
        else:
            self.passed("Attribute value matched expected")
