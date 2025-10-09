import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.account_result import AccountResult
from src.core.models.notification_data import NotificationData
from src.core.models.notification_stats import NotificationStats
from src.notif.notify import NotificationKit


class TestIntegration:
	"""集成测试 - 测试端到端流程"""

	@pytest.fixture
	def notification_kit_from_env(self):
		"""从环境变量创建 NotificationKit 实例（用于集成测试）"""
		return NotificationKit()

	@pytest.fixture
	def test_notification_data(self):
		"""创建测试用的通知数据"""
		return NotificationData(
			accounts=[
				AccountResult(
					name='测试账号',
					status='success',
					quota=25.0,
					used=5.0,
					error=None
				)
			],
			stats=NotificationStats(success_count=1, failed_count=0, total_count=1),
			timestamp='2024-01-01 12:00:00'
		)

	@pytest.mark.asyncio
	async def test_real_notification_with_env_config(self, notification_kit_from_env, test_notification_data):
		"""
		真实接口测试 - 需要在 .env.local 文件中配置 ENABLE_REAL_TEST=true

		此测试会实际发送通知到配置的平台，用于验证端到端流程。
		"""
		if os.getenv('ENABLE_REAL_TEST') != 'true':
			pytest.skip('未启用真实接口测试。请在 .env.local 中设置 ENABLE_REAL_TEST=true')

		# 尝试发送通知
		await notification_kit_from_env.push_message('集成测试消息', test_notification_data)

		# 如果没有抛出异常，则测试通过
		# 注意：这个测试不验证通知是否真的成功发送，只验证代码执行流程正确

	@pytest.mark.asyncio
	@patch('src.notif.notify.NotificationKit._send_email_with_template')
	@patch('src.notif.notify.NotificationKit._send_dingtalk_with_template')
	@patch('src.notif.notify.NotificationKit._send_wecom_with_template')
	@patch('src.notif.notify.NotificationKit._send_pushplus_with_template')
	@patch('src.notif.notify.NotificationKit._send_feishu_with_template')
	@patch('src.notif.notify.NotificationKit._send_serverpush_with_template')
	async def test_push_message_routing_logic(
		self,
		mock_serverpush: MagicMock,
		mock_feishu: MagicMock,
		mock_pushplus: MagicMock,
		mock_wecom: MagicMock,
		mock_dingtalk: MagicMock,
		mock_email: MagicMock,
		notification_kit_from_env,
		test_notification_data,
		monkeypatch
	):
		"""测试 push_message 的路由逻辑 - 验证根据配置调用相应平台"""
		# 设置至少一个配置，确保会调用对应的方法
		monkeypatch.setenv('DINGTALK_NOTIF_CONFIG', json.dumps({'webhook': 'https://example.com/webhook'}))

		# 重新创建 NotificationKit 以加载新配置
		kit = NotificationKit()

		await kit.push_message('测试标题', test_notification_data)

		# 验证至少钉钉的方法被调用了（因为我们配置了钉钉）
		assert mock_dingtalk.called