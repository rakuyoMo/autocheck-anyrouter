import os
from pathlib import Path
from typing import Any

import json5
import stencil

from core.models.notification_data import NotificationData
from notif.models import (
	BarkConfig,
	EmailConfig,
	NotificationHandler,
	NotificationTemplate,
	PushPlusConfig,
	ServerPushConfig,
	WebhookConfig,
)
from notif.senders import (
	BarkSender,
	DingTalkSender,
	EmailSender,
	FeishuSender,
	PushPlusSender,
	ServerPushSender,
	WeComSender,
)
from tools.logger import logger


class NotificationKit:
	def __init__(self):
		# 配置文件路径
		self.config_dir = Path(__file__).parent / 'configs'

		# 加载各平台配置
		self.bark_config = self._load_bark_config()
		self.email_config = self._load_email_config()
		self.dingtalk_config = self._load_dingtalk_config()
		self.feishu_config = self._load_feishu_config()
		self.wecom_config = self._load_wecom_config()
		self.pushplus_config = self._load_pushplus_config()
		self.serverpush_config = self._load_serverpush_config()

		# 注册所有通知处理器
		self._handlers = self._register_handlers()

	async def push_message(self, content: NotificationData):
		"""
		发送通知消息

		Args:
			content: 通知数据
		"""
		# 检查是否有可用的通知处理器
		if not self._handlers:
			logger.warning('没有可用的通知处理器，跳过通知提醒')
			return

		# 构建上下文数据
		context_data = self._build_context_data(content)

		# 向所有可用的 handler 发送通知
		for handler in self._handlers:
			if handler.is_available():
				await self._send_to_handler(
					handler=handler,
					context_data=context_data,
				)

	async def _send_to_handler(self, handler: NotificationHandler, context_data: dict):
		"""
		向单个 handler 发送通知

		Args:
			handler: 通知处理器
			context_data: 模板渲染的上下文数据
		"""
		# 类型收窄：确保 config 不是 None
		assert handler.config is not None

		try:
			# 渲染模板
			rendered_title, rendered_content = self._render_template(
				template=handler.config.template,
				context_data=context_data,
			)

			# 发送消息
			await handler.send_func(
				title=rendered_title,
				content=rendered_content,
				context_data=context_data,
			)

			logger.success(f'{handler.name} 消息发送成功！')

		except Exception as e:
			logger.error(
				message=f'消息推送失败！原因：{str(e)}',
				tag=handler.name,
				exc_info=True,
			)

	def _register_handlers(self) -> list[NotificationHandler]:
		"""
		注册所有通知处理器

		Returns:
			通知处理器列表
		"""
		# 平台配置映射表：(平台名称, 配置对象, Sender 类)
		platform_configs = [
			('Bark', self.bark_config, BarkSender),
			('邮箱', self.email_config, EmailSender),
			('PushPlus', self.pushplus_config, PushPlusSender),
			('Server 酱', self.serverpush_config, ServerPushSender),
			('钉钉', self.dingtalk_config, DingTalkSender),
			('飞书', self.feishu_config, FeishuSender),
			('企业微信', self.wecom_config, WeComSender),
		]

		handlers = []
		for name, config, sender_class in platform_configs:
			if config:
				sender = sender_class(config)
				handlers.append(
					NotificationHandler(
						name=name,
						config=config,
						send_func=sender.send,
					)
				)

		return handlers

	def _render_template(self, template: NotificationTemplate, context_data: dict) -> tuple[str | None, str]:
		"""
		渲染模板

		Args:
			template: NotificationTemplate 对象
			context_data: 上下文数据

		Returns:
			(title, content) 元组，title 可能为 None（表示不展示标题）

		注意: Stencil 模板引擎有以下限制:
		1. 不支持比较操作符 (==, !=, <, > 等)
		2. 不支持字典的点访问，只能访问对象属性
		因此我们提供分组的账号列表和对象形式的数据
		"""
		context = stencil.Context(context_data)

		# 分别渲染 title 和 content
		# 渲染失败时自动返回原始模板字符串
		rendered_title = self._render_text(
			text=template.title,
			context=context,
			field_name='标题',
		)

		rendered_content = self._render_text(
			text=template.content,
			context=context,
			field_name='内容',
		)

		# content 不能为 None，如果为 None 则使用原始模板或空字符串
		if rendered_content is None:
			rendered_content = template.content if template.content else ''

		return (rendered_title, rendered_content)

	def _render_text(
		self,
		text: str | None,
		context: stencil.Context,
		field_name: str | None = None,
	) -> str | None:
		"""
		渲染单个文本模板

		Args:
			text: 模板字符串，None 或空字符串表示不渲染
			context: Stencil 上下文对象
			field_name: 字段名称，用于错误日志（可选）

		Returns:
			渲染后的文本，渲染失败时返回原始文本，如果输入为 None 或空字符串则返回 None
		"""
		# 如果文本为 None 或空字符串，直接返回 None
		if not text:
			return None

		try:
			# 渲染模板
			template_obj = stencil.Template(text)
			rendered = template_obj.render(context)

			# 检查渲染结果
			if rendered is None:
				raise ValueError('模板渲染返回了 None')

			# 处理换行符：将 \n 转换为真正的换行符
			return rendered.replace('\\n', '\n')

		except Exception as e:
			# 如果提供了 field_name，输出错误日志
			if field_name:
				logger.error(
					message=f'{field_name}模板渲染失败：{e}',
					exc_info=True,
				)

			# 返回原始模板字符串
			return text

	def _build_context_data(self, data: NotificationData) -> dict:
		"""
		构建模板渲染的上下文数据

		Args:
			data: 通知数据

		Returns:
			上下文数据字典
		"""
		# 分组账号（因为 Stencil 不支持 == 比较）
		success_accounts = [acc for acc in data.accounts if acc.status == 'success']
		failed_accounts = [acc for acc in data.accounts if acc.status != 'success']

		# 余额变化相关分组
		balance_changed_accounts = [
			acc for acc in data.accounts
			if acc.balance_changed is True
		]
		balance_unchanged_accounts = [
			acc for acc in data.accounts
			if acc.balance_changed is False
		]

		# 计算可判断余额的账号数量（排除 balance_changed=None 的账号）
		balance_determinable_count = len(balance_changed_accounts) + len(balance_unchanged_accounts)

		return {
			'timestamp': data.timestamp,
			'stats': data.stats,  # dataclass 对象，支持 {{ stats.success_count }}
			# 提供分组的账号列表（AccountResult 对象）
			'success_accounts': success_accounts,
			'failed_accounts': failed_accounts,
			# 保留完整列表供需要的模板使用
			'accounts': data.accounts,  # AccountResult 对象列表
			# 便利变量：布尔标志（使用 stats 进行判断，确保与 NotificationData 的属性一致）
			'has_success': data.stats.success_count > 0,
			'has_failed': data.stats.failed_count > 0,
			'all_success': data.stats.failed_count == 0,
			'all_failed': data.stats.success_count == 0,
			'partial_success': data.stats.success_count > 0 and data.stats.failed_count > 0,
			# 余额变化相关的新变量
			'balance_changed_accounts': balance_changed_accounts,
			'balance_unchanged_accounts': balance_unchanged_accounts,
			'has_balance_changed': len(balance_changed_accounts) > 0,
			'has_balance_unchanged': len(balance_unchanged_accounts) > 0,
			'all_balance_changed': balance_determinable_count > 0 and len(balance_unchanged_accounts) == 0,
			'all_balance_unchanged': balance_determinable_count > 0 and len(balance_changed_accounts) == 0,
		}

	def _load_email_config(self) -> EmailConfig | None:
		"""加载邮箱配置"""
		email_notif_config = os.getenv('EMAIL_NOTIF_CONFIG')
		if not email_notif_config:
			return None

		parsed = self._parse_env_config(email_notif_config)
		if not isinstance(parsed, dict):
			return None

		# 验证必需字段
		if not self._validate_required_fields(
			parsed=parsed,
			fields=['user', 'pass', 'to'],
		):
			return None

		# 加载模板
		template = self._load_template(
			platform='email',
			parsed=parsed,
		)

		return EmailConfig(
			user=parsed['user'],
			password=parsed['pass'],
			to=parsed['to'],
			smtp_server=parsed.get('smtp_server'),
			platform_settings=self._load_platform_settings(
				platform='email',
				parsed=parsed,
			),
			template=template,
		)

	def _load_bark_config(self) -> BarkConfig | None:
		"""加载 Bark 配置"""
		bark_notif_config = os.getenv('BARK_NOTIF_CONFIG')
		if not bark_notif_config:
			return None

		parsed = self._parse_env_config(bark_notif_config)
		if not isinstance(parsed, dict):
			return None

		# 验证必需字段
		if not self._validate_required_fields(
			parsed=parsed,
			fields=['server_url', 'device_key'],
		):
			return None

		# 加载模板
		template = self._load_template(
			platform='bark',
			parsed=parsed,
		)

		return BarkConfig(
			server_url=parsed['server_url'],
			device_key=parsed['device_key'],
			platform_settings=self._load_platform_settings(
				platform='bark',
				parsed=parsed,
			),
			template=template,
		)

	def _load_dingtalk_config(self) -> WebhookConfig | None:
		"""加载钉钉配置"""
		return self._load_webhook_config(
			platform='dingtalk',
			notif_config_key='DINGTALK_NOTIF_CONFIG',
		)

	def _load_feishu_config(self) -> WebhookConfig | None:
		"""加载飞书配置"""
		return self._load_webhook_config(
			platform='feishu',
			notif_config_key='FEISHU_NOTIF_CONFIG',
		)

	def _load_wecom_config(self) -> WebhookConfig | None:
		"""加载企业微信配置"""
		return self._load_webhook_config(
			platform='wecom',
			notif_config_key='WECOM_NOTIF_CONFIG',
		)

	def _load_pushplus_config(self) -> PushPlusConfig | None:
		"""加载 PushPlus 配置"""
		return self._load_token_based_config(
			platform='pushplus',
			env_key='PUSHPLUS_NOTIF_CONFIG',
			config_class=PushPlusConfig,
			token_field='token',
		)

	def _load_serverpush_config(self) -> ServerPushConfig | None:
		"""加载 Server 酱配置"""
		return self._load_token_based_config(
			platform='serverpush',
			env_key='SERVERPUSH_NOTIF_CONFIG',
			config_class=ServerPushConfig,
			token_field='send_key',
		)

	def _load_webhook_config(self, platform: str, notif_config_key: str) -> WebhookConfig | None:
		"""加载 Webhook 配置的通用方法"""
		notif_config = os.getenv(notif_config_key)
		if not notif_config:
			return None

		parsed = self._parse_env_config(notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 验证必需字段
			if not self._validate_required_fields(
				parsed=parsed,
				fields=['webhook'],
			):
				return None

			# 加载模板
			template = self._load_template(
				platform=platform,
				parsed=parsed,
			)

			return WebhookConfig(
				webhook=parsed['webhook'],
				platform_settings=self._load_platform_settings(
					platform=platform,
					parsed=parsed,
				),
				template=template,
			)

		# 纯字符串，当做 webhook URL，使用默认配置
		default_config = self._load_default_config(platform)
		template_value = default_config.get('template') if default_config else None
		template = NotificationTemplate.from_value(template_value)
		platform_settings = default_config.get('platform_settings') if default_config else None

		return WebhookConfig(
			webhook=parsed,
			platform_settings=platform_settings,
			template=template,
		)

	def _load_token_based_config(
		self,
		platform: str,
		env_key: str,
		config_class: type,
		token_field: str,
	):
		"""
		加载基于 token 的配置的通用方法（PushPlus、ServerPush 等）

		Args:
			platform: 平台名称
			env_key: 环境变量键名
			config_class: 配置类
			token_field: token 字段名（如 'token' 或 'send_key'）

		Returns:
			配置对象，如果配置不存在则返回 None
		"""
		notif_config = os.getenv(env_key)
		if not notif_config:
			return None

		parsed = self._parse_env_config(notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 验证必需字段
			if not self._validate_required_fields(
				parsed=parsed,
				fields=[token_field],
			):
				return None

			# 加载模板
			template = self._load_template(
				platform=platform,
				parsed=parsed,
			)

			return config_class(
				**{token_field: parsed[token_field]},
				platform_settings=self._load_platform_settings(
					platform=platform,
					parsed=parsed,
				),
				template=template,
			)

		# 纯字符串，当做 token，使用默认配置
		default_config = self._load_default_config(platform)
		template_value = default_config.get('template') if default_config else None
		template = NotificationTemplate.from_value(template_value)
		platform_settings = default_config.get('platform_settings') if default_config else None

		return config_class(
			**{token_field: parsed},
			platform_settings=platform_settings,
			template=template,
		)

	def _load_template(self, platform: str, parsed: dict) -> NotificationTemplate | None:
		"""
		加载模板配置，支持 title 和 content 分别合并

		Args:
			platform: 平台名称
			parsed: 解析后的配置字典

		Returns:
			NotificationTemplate 对象，如果没有配置则返回 None
		"""
		# 加载默认配置
		default_config = self._load_default_config(platform)
		default_template_value = default_config.get('template') if default_config else None

		# 获取用户配置
		user_template_value = parsed.get('template')

		# 如果两者都不存在，返回 None
		if user_template_value is None and default_template_value is None:
			return None

		# 如果用户没有配置，使用默认配置
		if user_template_value is None:
			return NotificationTemplate.from_value(default_template_value)

		# 如果用户配置是字符串格式（向后兼容），直接使用
		if isinstance(user_template_value, str):
			return NotificationTemplate.from_value(user_template_value)

		# 如果用户配置是字典格式，需要分别合并 title 和 content
		if isinstance(user_template_value, dict):
			# 获取默认的 title 和 content
			default_title = None
			default_content = ''

			if isinstance(default_template_value, dict):
				default_title = default_template_value.get('title')
				default_content = default_template_value.get('content', '')

			# 获取用户的 title 和 content，如果用户没有设置，使用默认值
			merged_title = user_template_value.get('title', default_title)
			merged_content = user_template_value.get('content', default_content)

			# 构建合并后的模板配置
			merged_template_value = {
				'title': merged_title,
				'content': merged_content,
			}

			return NotificationTemplate.from_value(merged_template_value)

		# 其他情况，使用用户配置
		return NotificationTemplate.from_value(user_template_value)

	def _load_platform_settings(self, platform: str, parsed: dict) -> dict[str, Any] | None:
		"""
		加载平台特定设置，支持与默认配置深度合并

		Args:
			platform: 平台名称
			parsed: 解析后的配置字典

		Returns:
			合并后的 platform_settings，如果都没有则返回 None
		"""
		# 加载默认配置
		default_config = self._load_default_config(platform)
		default_platform_settings = default_config.get('platform_settings') if default_config else None

		# 获取用户配置
		user_platform_settings = parsed.get('platform_settings')

		# 如果两者都不存在，返回 None
		if user_platform_settings is None and default_platform_settings is None:
			return None

		# 如果用户没有配置，使用默认配置
		if user_platform_settings is None:
			return default_platform_settings

		# 如果默认配置不存在，使用用户配置
		if default_platform_settings is None:
			return user_platform_settings

		# 深度合并用户配置和默认配置
		return self._deep_merge_dict(
			default=default_platform_settings,
			override=user_platform_settings,
		)

	def _validate_required_fields(self, parsed: dict, fields: list[str]) -> bool:
		"""
		验证多个必需字段是否都存在且非空

		Args:
			parsed: 解析后的配置字典
			fields: 字段名列表

		Returns:
			所有字段都存在且非空返回 True，否则返回 False
		"""
		return all(field in parsed and parsed[field] for field in fields)

	def _deep_merge_dict(
		self,
		default: dict[str, Any],
		override: dict[str, Any] | None,
	) -> dict[str, Any]:
		"""
		深度合并字典，override 中的值会覆盖 default 中的值

		Args:
			default: 默认配置字典
			override: 用户配置字典（会覆盖默认配置）

		Returns:
			合并后的字典
		"""
		if override is None:
			return default.copy()

		result = default.copy()

		for key, value in override.items():
			# 如果两边都是字典，递归合并
			if key in result and isinstance(result[key], dict) and isinstance(value, dict):
				result[key] = self._deep_merge_dict(
					default=result[key],
					override=value,
				)
			else:
				# 否则直接覆盖
				result[key] = value

		return result

	def _load_default_config(self, platform: str) -> dict[str, Any] | None:
		"""加载默认配置文件"""
		config_file = self.config_dir / f'{platform}.json5'
		if config_file.exists():
			try:
				with open(config_file, 'r', encoding='utf-8') as f:
					return json5.load(f)
			except Exception as e:
				logger.warning(f'加载默认配置文件 {config_file} 失败：{e}')
		return None

	def _parse_env_config(self, env_value: str) -> Any:
		"""解析环境变量配置"""
		try:
			# 尝试解析为 JSON
			return json5.loads(env_value)
		except Exception:
			# 如果不是 JSON，就当做纯字符串（Token 或 Webhook URL）
			return env_value
