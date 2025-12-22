import json
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

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'setup_type,expected_count,expected_cookies',
		[
			('prefix_only', 2, None),  # 仅使用 ANYROUTER_ACCOUNT_* 加载 2 个账号
			('merge', 3, None),  # ANYROUTER_ACCOUNTS(1) + ANYROUTER_ACCOUNT_*(2) = 3 个账号
			('override_by_api_user', 2, 'session=new'),  # 覆盖场景：通过 api_user 匹配
			('override_with_suffix', 1, 'session=new'),  # 覆盖场景：api_user + 可读后缀
			('invalid_prefix', 1, None),  # 无效的 prefix 配置（缺少必要字段）被忽略
		],
	)
	async def test_account_loading_modes(
		self,
		monkeypatch: pytest.MonkeyPatch,
		tmp_path,
		setup_type: str,
		expected_count: int,
		expected_cookies: str | None,
	):
		"""测试账号加载方式（前缀环境变量、合并、覆盖、验证）"""
		# 清理环境变量
		monkeypatch.delenv('ANYROUTER_ACCOUNTS', raising=False)
		for key in list(os.environ.keys()):
			if key.startswith('ANYROUTER_ACCOUNT_'):
				monkeypatch.delenv(key, raising=False)

		# 测试数据
		account_alice = {'name': 'Alice', 'cookies': 'session=alice', 'api_user': 'user_alice'}
		account_bob = {'name': 'Bob', 'cookies': 'session=bob', 'api_user': 'user_bob'}

		if setup_type == 'prefix_only':
			# 仅使用 ANYROUTER_ACCOUNT_* 前缀环境变量
			monkeypatch.setenv('ANYROUTER_ACCOUNT_ALICE', json.dumps(account_alice))
			monkeypatch.setenv('ANYROUTER_ACCOUNT_BOB', json.dumps(account_bob))

		elif setup_type == 'merge':
			# ANYROUTER_ACCOUNTS + ANYROUTER_ACCOUNT_* 合并（无覆盖）
			account_main = {'name': 'Main', 'cookies': 'session=main', 'api_user': 'user_main'}
			monkeypatch.setenv('ANYROUTER_ACCOUNTS', json.dumps([account_main]))
			monkeypatch.setenv('ANYROUTER_ACCOUNT_ALICE', json.dumps(account_alice))
			monkeypatch.setenv('ANYROUTER_ACCOUNT_BOB', json.dumps(account_bob))

		elif setup_type == 'override_by_api_user':
			# 覆盖场景：通过 api_user 匹配并覆盖 cookies
			account_with_api_user = {'name': 'Alice', 'cookies': 'session=old', 'api_user': '12427'}
			monkeypatch.setenv('ANYROUTER_ACCOUNTS', json.dumps([account_with_api_user, account_bob]))
			# 后缀包含 api_user "12427"
			monkeypatch.setenv('ANYROUTER_ACCOUNT_12427', json.dumps({'cookies': 'session=new'}))

		elif setup_type == 'override_with_suffix':
			# 覆盖场景：api_user + 可读后缀
			account_with_api_user = {'name': 'Alice', 'cookies': 'session=old', 'api_user': '12427'}
			monkeypatch.setenv('ANYROUTER_ACCOUNTS', json.dumps([account_with_api_user]))
			# 后缀包含 api_user "12427" 加上可读标识
			monkeypatch.setenv('ANYROUTER_ACCOUNT_12427_ALICE', json.dumps({'cookies': 'session=new'}))

		elif setup_type == 'invalid_prefix':
			# 无效的 prefix 配置（缺少必要字段）被忽略
			monkeypatch.setenv('ANYROUTER_ACCOUNTS', json.dumps([account_alice]))
			monkeypatch.setenv('ANYROUTER_ACCOUNT_99999', json.dumps({'cookies': 'session=bob'}))  # 缺少 api_user

		app = Application()
		app.balance_manager.balance_hash_file = tmp_path / f'hash_{setup_type}.txt'

		# 直接测试 _load_accounts 方法
		accounts = app._load_accounts()
		assert len(accounts) == expected_count, (
			f'{setup_type}: 应该加载 {expected_count} 个账号，实际加载了 {len(accounts)} 个'
		)

		# 验证覆盖是否生效
		if expected_cookies:
			# 查找被覆盖的账号
			target_account = next((a for a in accounts if a.get('name') == 'Alice'), None)
			assert target_account is not None, f'{setup_type}: 应该存在 "Alice" 账号'
			assert target_account['cookies'] == expected_cookies, (
				f'{setup_type}: cookies 应该被覆盖为 {expected_cookies}'
			)
