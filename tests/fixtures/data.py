from collections.abc import Callable

import pytest

from core.models import NotificationData
from tests.tools.data_builders import (
	create_account_result_data,
	create_notification_data as build_notification_data,
)


@pytest.fixture
def create_account_result() -> Callable:
	"""创建账号结果的工厂函数"""
	return create_account_result_data


@pytest.fixture
def create_notification_data() -> Callable:
	"""创建通知数据的工厂函数"""
	return build_notification_data


@pytest.fixture
def single_success_data(create_account_result: Callable, create_notification_data: Callable) -> NotificationData:
	"""单账号成功的测试数据"""
	return create_notification_data([
		create_account_result(name='Account-1'),
	])


@pytest.fixture
def single_failure_data(create_account_result: Callable, create_notification_data: Callable) -> NotificationData:
	"""单账号失败的测试数据"""
	return create_notification_data([
		create_account_result(
			name='Account-1',
			status='failed',
			error='Connection timeout',
		)
	])


@pytest.fixture
def multiple_mixed_data(create_account_result: Callable, create_notification_data: Callable) -> NotificationData:
	"""多账号混合的测试数据"""
	return create_notification_data([
		create_account_result(name='Account-1', quota=25.0, used=5.0),
		create_account_result(name='Account-2', quota=30.0, used=10.0),
		create_account_result(name='Account-3', status='failed', error='Authentication failed'),
	])
