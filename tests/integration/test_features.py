import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from application import Application
from tests.conftest import assert_file_content_contains
from tests.fixtures.data import MIXED_ACCOUNTS
from tests.fixtures.mock_dependencies import MockHttpClient, MockPlaywright, MockSMTP


class TestFeatures:
	"""测试功能特性"""

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'repo_visibility,expected_in_content',
		[
			('public', '账号 2'),  # 公开仓库：默认账号编号
			('private', '自定义名称'),  # 私有仓库：显示完整名称
		],
	)
	async def test_privacy_modes(self, accounts_env, tmp_path, repo_visibility: str, expected_in_content: str):
		"""测试隐私模式（公开/私有仓库）"""
		accounts_env(MIXED_ACCOUNTS)

		app = Application()
		app.balance_manager.balance_hash_file = tmp_path / f'hash_{repo_visibility}.txt'
		summary_file = tmp_path / f'summary_{repo_visibility}.md'

		with patch.dict(
			os.environ,
			{
				'REPO_VISIBILITY': repo_visibility,
				'GITHUB_STEP_SUMMARY': str(summary_file),
			},
		):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)
				MockHttpClient.setup(stack, MockHttpClient.get_success_handler, MockHttpClient.post_success_handler)

				with pytest.raises(SystemExit):
					await app.run()

		assert summary_file.exists()
		assert_file_content_contains(summary_file, expected_in_content)

	@pytest.mark.asyncio
	async def test_notification_template_rendering(
		self,
		config_env_setter,
		create_account_result,
		create_notification_data,
	):
		"""测试通知模板渲染（多平台不同模板格式）"""
		# 配置多个平台的不同模板格式
		config_env_setter('dingtalk', 'https://mock.dingtalk.com')
		config_env_setter(
			'feishu',
			{
				'webhook': 'https://mock.feishu.com',
				'template': {
					'title': '{% if all_success %}全部成功{% else %}部分成功{% endif %}',
					'content': '共 {{ stats.total_count }} 个账号',
				},
			},
		)
		config_env_setter('wecom', {'webhook': 'https://mock.wecom.com', 'template': '简化内容'})
		config_env_setter('pushplus', 'mock_token')
		config_env_setter('email', {'user': 'test@example.com', 'pass': 'pass', 'to': 'to@example.com'})

		from notif import NotificationKit

		kit = NotificationKit()

		# 创建测试数据
		notif_data = create_notification_data([
			create_account_result(name='成功账号', quota=25.0, used=5.0),
			create_account_result(name='失败账号', status='failed', error='超时'),
		])

		with ExitStack() as stack:
			post_counter = {'count': 0}

			async def post_handler(*args, **kwargs):
				post_counter['count'] += 1
				return MockHttpClient.build_response(status=200, json_data={'errcode': 0, 'code': 0})

			MockHttpClient.setup(stack, MockHttpClient.get_success_handler, post_handler)
			MockSMTP.setup(stack)

			await kit.push_message(notif_data)

		assert post_counter['count'] == 4, f'应该向 4 个平台发送通知，实际发送了 {post_counter["count"]} 个'
