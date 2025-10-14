import pytest

from tests.fixtures.mock_dependencies import MockDependencies


@pytest.fixture
def mocked_service_dependencies():
	"""提供统一的 service 依赖 mock 对象"""
	return MockDependencies()
