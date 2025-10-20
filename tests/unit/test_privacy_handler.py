import pytest

from core.privacy_handler import PrivacyHandler


class TestPrivacyHandler:
	"""测试 PrivacyHandler 类"""

	@pytest.mark.parametrize(
		'repo_visibility,show_sensitive,account,expected_safe_name,should_mask',
		[
			# 公开仓库，自定义名称（会被脱敏）
			('public', None, {'name': '我的账号', 'cookies': 'test', 'api_user': 'user1'}, '我', True),
			# 公开仓库，默认名称（不会被脱敏）
			('public', None, {'cookies': 'test', 'api_user': 'user2'}, '账号 2', False),
			# 私有仓库（不脱敏）
			('private', None, {'name': '我的账号', 'cookies': 'test', 'api_user': 'user1'}, '我的账号', False),
			# 强制显示敏感信息（不脱敏）
			('public', 'true', {'name': '我的账号', 'cookies': 'test', 'api_user': 'user1'}, '我的账号', False),
			# Emoji 账号名称
			('public', None, {'name': '😀测试账号', 'cookies': 'test', 'api_user': 'user1'}, '😀', True),
			# 超长账号名称（测试边界）
			(
				'public',
				None,
				{'name': '这是一个非常非常长的账号名称' * 10, 'cookies': 'test', 'api_user': 'user1'},
				'这',
				True,
			),
		],
	)
	def test_account_name_handling(
		self,
		monkeypatch: pytest.MonkeyPatch,
		repo_visibility: str,
		show_sensitive: str | None,
		account: dict[str, str],
		expected_safe_name: str,
		should_mask: bool,
	) -> None:
		"""测试账号名称处理（自定义/默认/脱敏/边界条件）"""
		monkeypatch.setenv('REPO_VISIBILITY', repo_visibility)
		if show_sensitive:
			monkeypatch.setenv('SHOW_SENSITIVE_INFO', show_sensitive)
		else:
			monkeypatch.delenv('SHOW_SENSITIVE_INFO', raising=False)

		handler = PrivacyHandler(show_sensitive_info=PrivacyHandler.should_show_sensitive_info())

		safe_name = handler.get_safe_account_name(account, 1)
		full_name = handler.get_full_account_name(account, 1)

		if should_mask:
			# 脱敏后：首字符 + hash 后 4 位
			assert safe_name.startswith(expected_safe_name)
			assert len(safe_name) >= len(expected_safe_name)
			if 'name' in account:
				assert full_name == account['name']
		else:
			assert safe_name == expected_safe_name
			if 'name' in account:
				assert full_name == account['name']
			else:
				assert full_name == expected_safe_name

	@pytest.mark.parametrize(
		'repo_visibility,show_sensitive,quota,used,expected_has_numbers',
		[
			# 公开仓库（隐藏余额）
			('public', None, 50.0, 10.0, False),
			# 私有仓库（显示余额）
			('private', None, 50.0, 10.0, True),
			# 强制显示
			('public', 'true', 50.0, 10.0, True),
			# 大数字边界测试
			('private', None, 999999.99, 888888.88, True),
			# 零值测试
			('private', None, 0.0, 0.0, True),
		],
	)
	def test_balance_display(
		self,
		monkeypatch: pytest.MonkeyPatch,
		repo_visibility: str,
		show_sensitive: str | None,
		quota: float,
		used: float,
		expected_has_numbers: bool,
	) -> None:
		"""测试余额显示（显示/隐藏/边界值）"""
		monkeypatch.setenv('REPO_VISIBILITY', repo_visibility)
		if show_sensitive:
			monkeypatch.setenv('SHOW_SENSITIVE_INFO', show_sensitive)
		else:
			monkeypatch.delenv('SHOW_SENSITIVE_INFO', raising=False)

		handler = PrivacyHandler(show_sensitive_info=PrivacyHandler.should_show_sensitive_info())

		display = handler.get_safe_balance_display(quota=quota, used=used)

		if expected_has_numbers:
			# 应该包含具体数字
			assert str(quota) in display or f'{quota:.1f}' in display or f'{quota:.2f}' in display
		else:
			# 应该隐藏数字
			assert '余额正常' in display or ':money:' in display
			assert str(quota) not in display
