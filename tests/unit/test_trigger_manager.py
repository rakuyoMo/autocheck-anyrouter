import pytest

from notif import NotifyTrigger, NotifyTriggerManager


class TestNotifyTriggerManager:
	"""测试 NotifyTriggerManager 类"""

	@pytest.mark.parametrize(
		'env_value,expected_triggers',
		[
			# 测试默认值（未配置）
			(None, {NotifyTrigger.BALANCE_CHANGED, NotifyTrigger.FAILED}),
			# 测试单个触发器
			('always', {NotifyTrigger.ALWAYS}),
			# 测试多个触发器
			('success,failed', {NotifyTrigger.SUCCESS, NotifyTrigger.FAILED}),
			# 测试带空格
			(' success , balance_changed ', {NotifyTrigger.SUCCESS, NotifyTrigger.BALANCE_CHANGED}),
			# 测试无效触发器（使用默认值）
			('invalid', {NotifyTrigger.BALANCE_CHANGED, NotifyTrigger.FAILED}),
			# 测试空字符串（使用默认值）
			('', {NotifyTrigger.BALANCE_CHANGED, NotifyTrigger.FAILED}),
			# 测试大小写不敏感
			('ALWAYS', {NotifyTrigger.ALWAYS}),
			('Success,Failed', {NotifyTrigger.SUCCESS, NotifyTrigger.FAILED}),
			# 测试混合有效和无效触发器
			('success,invalid,failed', {NotifyTrigger.SUCCESS, NotifyTrigger.FAILED}),
		],
	)
	def test_trigger_parsing(
		self,
		monkeypatch: pytest.MonkeyPatch,
		env_value: str | None,
		expected_triggers: set[NotifyTrigger],
	) -> None:
		"""测试触发器解析逻辑（包括边界情况）"""
		if env_value is None:
			monkeypatch.delenv('NOTIFY_TRIGGERS', raising=False)
		else:
			monkeypatch.setenv('NOTIFY_TRIGGERS', env_value)

		manager = NotifyTriggerManager()
		assert manager.triggers == expected_triggers

	@pytest.mark.parametrize(
		'triggers,has_success,has_failed,has_balance_changed,is_first_run,expected',
		[
			# never 触发器（优先级最高）
			('never', True, True, True, True, False),
			# always 触发器
			('always', False, False, False, False, True),
			('always', True, True, True, True, True),
			# success 触发器
			('success', True, False, False, False, True),
			('success', False, False, False, False, False),
			# failed 触发器
			('failed', False, True, False, False, True),
			('failed', False, False, False, False, False),
			# balance_changed 触发器 - 首次运行
			('balance_changed', True, False, False, True, True),
			# balance_changed 触发器 - 余额变化
			('balance_changed', True, False, True, False, True),
			# balance_changed 触发器 - 余额未变化且非首次
			('balance_changed', True, False, False, False, False),
			# 多触发器组合（OR 关系）- 满足 success
			('success,failed', True, False, False, False, True),
			# 多触发器组合（OR 关系）- 满足 failed
			('success,failed', False, True, False, False, True),
		],
	)
	def test_decision_logic(
		self,
		monkeypatch: pytest.MonkeyPatch,
		triggers: str,
		has_success: bool,
		has_failed: bool,
		has_balance_changed: bool,
		is_first_run: bool,
		expected: bool,
	) -> None:
		"""测试触发器决策逻辑（所有场景）"""
		monkeypatch.setenv('NOTIFY_TRIGGERS', triggers)
		manager = NotifyTriggerManager()

		result = manager.should_notify(
			has_success=has_success,
			has_failed=has_failed,
			has_balance_changed=has_balance_changed,
			is_first_run=is_first_run,
		)

		assert result is expected

	def test_notify_reasons(self, monkeypatch: pytest.MonkeyPatch) -> None:
		"""测试通知原因生成"""
		monkeypatch.setenv('NOTIFY_TRIGGERS', 'success,failed')
		manager = NotifyTriggerManager()

		reasons = manager.get_notify_reasons(
			has_success=True,
			has_failed=True,
			has_balance_changed=False,
			is_first_run=False,
		)

		assert '账号成功' in reasons
		assert '账号失败' in reasons
