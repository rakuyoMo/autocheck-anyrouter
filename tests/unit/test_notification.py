from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notif.models import NotificationHandler, NotificationTemplate
from notif.notify import NotificationKit
from tests.tools.data_builders import create_account_result_data, create_notification_data


@pytest.mark.asyncio
async def test_notificationkit_without_handlers(clean_notification_env):
	"""验证没有配置时不会推送。"""
	kit = NotificationKit()
	kit._handlers = []

	# 创建测试数据
	data = create_notification_data([
		create_account_result_data(name='测试账号', quota=25.0, used=5.0),
	])

	with patch('notif.notify.logger.warning') as mock_warning:
		await kit.push_message(data)

	mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_notificationkit_handler_skip_and_error(clean_notification_env):
	"""验证处理器跳过与异常分支。"""
	kit = NotificationKit()

	data = create_notification_data([
		create_account_result_data(name='账号 A', quota=25.0, used=5.0),
		create_account_result_data(name='账号 B', status='failed', error='超时'),
	])

	skip_handler = NotificationHandler(name='跳过平台', config=None, send_func=AsyncMock())
	error_config = MagicMock()
	error_config.template = NotificationTemplate(title='测试标题', content='{{ stats.success_count }}')
	error_handler = NotificationHandler(
		name='异常平台',
		config=error_config,
		send_func=AsyncMock(side_effect=Exception('发送失败')),
	)

	kit._handlers = [skip_handler, error_handler]

	with (
		patch('notif.notify.logger.error') as mock_error,
		patch('notif.notify.stencil.Template') as mock_template,
	):
		mock_template.side_effect = ValueError('模板错误')
		await kit.push_message(data)

	# 验证 skip_handler 没有被调用（因为 config 是 None）
	skip_handler.send_func.assert_not_called()

	# 验证 error_handler 的异常被捕获并记录
	assert mock_error.call_count >= 1


def test_notification_config_parsing(clean_notification_env, monkeypatch):
	"""验证各平台的配置解析（字典、字符串格式、向后兼容）+ NotificationTemplate。"""
	kit = NotificationKit()

	# PushPlus：字典格式
	monkeypatch.setenv('PUSHPLUS_NOTIF_CONFIG', '{"token": "dict-token"}')
	config_dict = kit._load_pushplus_config()
	assert config_dict is not None
	assert config_dict.token == 'dict-token'

	# PushPlus：字符串格式
	monkeypatch.setenv('PUSHPLUS_NOTIF_CONFIG', 'string-token')
	config_str = kit._load_pushplus_config()
	assert config_str is not None
	assert config_str.token == 'string-token'

	# Email：platform_settings 中的配置解析
	monkeypatch.setenv(
		'EMAIL_NOTIF_CONFIG',
		'{"user": "test@example.com", "pass": "test_pass", "to": "recipient@example.com", "platform_settings": {"message_type": "html"}}',
	)
	email_config = kit._load_email_config()
	assert email_config is not None
	assert email_config.user == 'test@example.com'
	assert email_config.platform_settings is not None
	assert email_config.platform_settings['message_type'] == 'html'

	# 测试 NotificationTemplate.from_value() 的各种格式
	# 1. 对象格式
	template_obj = NotificationTemplate.from_value({'title': '自定义标题', 'content': '自定义内容'})
	assert template_obj is not None
	assert template_obj.title == '自定义标题'
	assert template_obj.content == '自定义内容'

	# 2. 字符串格式（向后兼容）
	template_str = NotificationTemplate.from_value('旧格式内容')
	assert template_str is not None
	assert template_str.title == 'AnyRouter 签到提醒'
	assert template_str.content == '旧格式内容'

	# 3. None 值
	template_none = NotificationTemplate.from_value(None)
	assert template_none is None

	# 4. 对象格式但 title 为 None（表示不展示标题）
	template_no_title = NotificationTemplate.from_value({'content': '只有内容'})
	assert template_no_title is not None
	assert template_no_title.title is None
	assert template_no_title.content == '只有内容'

	# 5. 空字符串 title
	template_empty_title = NotificationTemplate.from_value({'title': '', 'content': '内容'})
	assert template_empty_title is not None
	assert template_empty_title.title == ''
	assert template_empty_title.content == '内容'


def test_build_context_data_with_stats_mismatch(clean_notification_env):
	"""
	验证 _build_context_data 使用 stats 而不是 accounts 列表来判断状态。

	这是一个回归测试，用于验证修复 #18 的问题：
	当部分账号成功但无余额变化时，accounts 列表中只包含失败的账号，
	但 stats 显示有成功账号。此时状态判断应该基于 stats 而不是 accounts。

	同时验证余额变化相关的新 Stencil 变量。
	"""
	from core.models import NotificationData, NotificationStats

	kit = NotificationKit()

	# 场景：3 个账号，2 个成功 1 个失败，但 accounts 列表中只有失败的账号
	# 这模拟了真实场景：成功账号在无余额变化时不会被添加到 accounts 列表
	stats = NotificationStats(
		success_count=2,  # 实际有 2 个账号成功
		failed_count=1,
		total_count=3,
	)

	# accounts 列表中只有失败的账号（成功的没有被添加）
	accounts = [
		create_account_result_data(
			name='账号 C',
			status='failed',
			error='超时',
			balance_changed=None,
		),
	]

	data = NotificationData(
		accounts=accounts,
		stats=stats,
		timestamp='2024-01-01 12:00:00',
	)

	# 调用 _build_context_data
	context = kit._build_context_data(data)

	# 验证状态标志基于 stats 而不是 accounts 列表
	assert context['has_success'] is True, '应该基于 stats.success_count > 0 判断'
	assert context['has_failed'] is True, '应该基于 stats.failed_count > 0 判断'
	assert context['all_success'] is False, '应该基于 stats.failed_count == 0 判断'
	assert context['all_failed'] is False, '应该基于 stats.success_count == 0 判断（修复前会错误判断为 True）'
	assert context['partial_success'] is True, '应该基于 stats 判断为部分成功'

	# 验证分组的账号列表（这些基于 accounts 列表）
	assert len(context['success_accounts']) == 0, 'accounts 列表中没有成功的账号'
	assert len(context['failed_accounts']) == 1, 'accounts 列表中只有 1 个失败账号'

	# 验证余额变化相关的新 Stencil 变量（场景 1：只有失败账号）
	assert len(context['balance_changed_accounts']) == 0, '没有余额变化的账号'
	assert len(context['balance_unchanged_accounts']) == 0, '没有余额未变化的账号'
	assert context['has_balance_changed'] is False, '没有账号余额变化'
	assert context['has_balance_unchanged'] is False, '没有账号余额未变化'
	assert context['all_balance_changed'] is False, '不是所有账号余额都变化（列表为空）'
	assert context['all_balance_unchanged'] is False, '不是所有账号余额都未变化（列表为空）'

	# 场景 2：测试余额变化的各种情况
	accounts_with_balance = [
		create_account_result_data(
			name='余额变化账号',
			status='success',
			quota=30.0,
			used=10.0,
			balance_changed=True,
		),
		create_account_result_data(
			name='余额未变化账号',
			status='success',
			quota=25.0,
			used=5.0,
			balance_changed=False,
		),
		create_account_result_data(
			name='失败账号',
			status='failed',
			error='网络错误',
			balance_changed=None,
		),
	]

	data_with_balance = NotificationData(
		accounts=accounts_with_balance,
		stats=NotificationStats(success_count=2, failed_count=1, total_count=3),
		timestamp='2024-01-01 12:00:00',
	)

	context_with_balance = kit._build_context_data(data_with_balance)

	# 验证余额变化分组
	assert len(context_with_balance['balance_changed_accounts']) == 1, '应该有 1 个余额变化的账号'
	assert context_with_balance['balance_changed_accounts'][0].name == '余额变化账号'
	assert len(context_with_balance['balance_unchanged_accounts']) == 1, '应该有 1 个余额未变化的账号'
	assert context_with_balance['balance_unchanged_accounts'][0].name == '余额未变化账号'

	# 验证余额变化标志
	assert context_with_balance['has_balance_changed'] is True, '有账号余额变化'
	assert context_with_balance['has_balance_unchanged'] is True, '有账号余额未变化'
	assert context_with_balance['all_balance_changed'] is False, '不是所有账号余额都变化'
	assert context_with_balance['all_balance_unchanged'] is False, '不是所有账号余额都未变化'

	# 场景 3：所有账号余额都变化
	accounts_all_changed = [
		create_account_result_data(name='账号 1', balance_changed=True),
		create_account_result_data(name='账号 2', balance_changed=True),
	]

	data_all_changed = NotificationData(
		accounts=accounts_all_changed,
		stats=NotificationStats(success_count=2, failed_count=0, total_count=2),
		timestamp='2024-01-01 12:00:00',
	)

	context_all_changed = kit._build_context_data(data_all_changed)

	assert len(context_all_changed['balance_changed_accounts']) == 2
	assert len(context_all_changed['balance_unchanged_accounts']) == 0
	assert context_all_changed['all_balance_changed'] is True, '所有账号余额都变化'
	assert context_all_changed['all_balance_unchanged'] is False

	# 场景 4：所有账号余额都未变化
	accounts_all_unchanged = [
		create_account_result_data(name='账号 1', balance_changed=False),
		create_account_result_data(name='账号 2', balance_changed=False),
	]

	data_all_unchanged = NotificationData(
		accounts=accounts_all_unchanged,
		stats=NotificationStats(success_count=2, failed_count=0, total_count=2),
		timestamp='2024-01-01 12:00:00',
	)

	context_all_unchanged = kit._build_context_data(data_all_unchanged)

	assert len(context_all_unchanged['balance_changed_accounts']) == 0
	assert len(context_all_unchanged['balance_unchanged_accounts']) == 2
	assert context_all_unchanged['all_balance_changed'] is False
	assert context_all_unchanged['all_balance_unchanged'] is True, '所有账号余额都未变化'
