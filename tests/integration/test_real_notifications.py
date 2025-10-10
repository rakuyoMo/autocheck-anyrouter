import os

import pytest

from core.models import AccountResult, NotificationData, NotificationStats
from notif.notify import NotificationKit


class TestIntegration:
	"""集成测试 - 测试端到端流程"""

	@pytest.fixture
	def notification_kit_from_env(self) -> NotificationKit:
		"""从环境变量创建 NotificationKit"""
		return NotificationKit()

	@pytest.fixture
	def test_notification_data(self):
		"""创建测试用的通知数据"""
		accounts = [
			AccountResult(
				name='测试账号',
				status='success',
				quota=25.0,
				used=5.0,
				error=None,
			),
		]
		return NotificationData(
			accounts=accounts,
			stats=NotificationStats(
				success_count=len(accounts),
				failed_count=0,
				total_count=len(accounts),
			),
			timestamp='2024-01-01 12:00:00',
		)

	@pytest.mark.asyncio
	async def test_real_notification_with_env_config(self, notification_kit_from_env, test_notification_data):
		"""
		真实接口测试 - 需要在 .env.test 文件中配置相应平台

		此测试会实际发送通知到配置的平台，用于验证端到端流程。
		使用 ENABLE_REAL_TEST=true 环境变量启用此测试。
		"""
		enable_key = 'ENABLE_REAL_TEST'
		if os.getenv(enable_key) != 'true':
			pytest.skip(f'未启用真实接口测试。请在 `.env.test` 中设置 `{enable_key}=true`')

		# 尝试发送通知（发送到所有已配置的平台）
		await notification_kit_from_env.push_message(
			title='集成测试消息',
			content=test_notification_data,
		)

		# 如果没有抛出异常，则测试通过
		# 注意：这个测试不验证通知是否真的成功发送，只验证代码执行流程正确
