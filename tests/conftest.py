import pytest

from lib.drivers.controller import LEDController
from lib.drivers.mock_driver import MockDriver


@pytest.fixture
def driver() -> MockDriver:
    return MockDriver(60)


@pytest.fixture
def led(driver: MockDriver) -> LEDController:
    return LEDController(driver)
