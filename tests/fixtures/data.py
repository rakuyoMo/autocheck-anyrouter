from collections.abc import Callable

import pytest

from core.models import NotificationData
from tests.tools.data_builders import build_account_result, build_notification_data

# 标准测试账号
STANDARD_ACCOUNTS = [
	{
		'name': '测试账号 A',
		'cookies': 'session=test_a',
		'api_user': 'user_a',
	},
	{
		'name': '测试账号 B',
		'cookies': 'session=test_b',
		'api_user': 'user_b',
	},
]

# 单个测试账号
SINGLE_ACCOUNT = [
	{
		'name': '单个账号',
		'cookies': 'session=single',
		'api_user': 'user_single',
	},
]

# 无名称的测试账号
NAMELESS_ACCOUNT = [
	{
		'cookies': 'session=nameless',
		'api_user': 'user_nameless',
	},
]

# 混合测试账号（有名称和无名称）
MIXED_ACCOUNTS = [
	{
		'name': '自定义名称',
		'cookies': 'session=custom',
		'api_user': 'user_custom',
	},
	{
		'cookies': 'session=default',
		'api_user': 'user_default',
	},
]


@pytest.fixture
def create_account_result() -> Callable:
	"""创建账号结果的工厂函数"""
	return build_account_result


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
