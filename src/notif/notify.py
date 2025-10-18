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
		handlers = []

		# Bark
		if self.bark_config:
			sender = BarkSender(self.bark_config)
			handlers.append(
				NotificationHandler(
					name='Bark',
					config=self.bark_config,
					send_func=sender.send,
				)
			)

		# 邮箱
		if self.email_config:
			sender = EmailSender(self.email_config)
			handlers.append(
				NotificationHandler(
					name='邮箱',
					config=self.email_config,
					send_func=sender.send,
				)
			)

		# PushPlus
		if self.pushplus_config:
			sender = PushPlusSender(self.pushplus_config)
			handlers.append(
				NotificationHandler(
					name='PushPlus',
					config=self.pushplus_config,
					send_func=sender.send,
				)
			)

		# Server 酱
		if self.serverpush_config:
			sender = ServerPushSender(self.serverpush_config)
			handlers.append(
				NotificationHandler(
					name='Server 酱',
					config=self.serverpush_config,
					send_func=sender.send,
				)
			)

		# 钉钉
		if self.dingtalk_config:
			sender = DingTalkSender(self.dingtalk_config)
			handlers.append(
				NotificationHandler(
					name='钉钉',
					config=self.dingtalk_config,
					send_func=sender.send,
				)
			)

		# 飞书
		if self.feishu_config:
			sender = FeishuSender(self.feishu_config)
			handlers.append(
				NotificationHandler(
					name='飞书',
					config=self.feishu_config,
					send_func=sender.send,
				)
			)

		# 企业微信
		if self.wecom_config:
			sender = WeComSender(self.wecom_config)
			handlers.append(
				NotificationHandler(
					name='企业微信',
					config=self.wecom_config,
					send_func=sender.send,
				)
			)

		return handlers

	def _render_template(
		self,
		template: NotificationTemplate,
		context_data: dict,
	) -> tuple[str | None, str]:
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

		try:
			# 渲染 title（如果有）
			rendered_title = self._render_text(
				text=template.title,
				context=context,
			)

			# 渲染 content
			rendered_content = self._render_text(
				text=template.content,
				context=context,
			)

			# content 不能为 None
			if rendered_content is None:
				raise ValueError('content 模板渲染返回了 None')

			return (rendered_title, rendered_content)

		except Exception as e:
			logger.error(
				message=f'模板渲染失败：{e}',
				exc_info=True,
			)

			# 如果模板渲染失败，返回简单格式
			timestamp = context_data.get('timestamp', '')
			accounts = context_data.get('accounts', [])

			fallback_content = f'{timestamp}\\n\\n' + '\\n\\n'.join([
				f'[{"成功" if account.status == "success" else "失败"}] {account.name}'
				for account in accounts
			])  # fmt: skip
			fallback_title = template.title if template.title else None
			return (fallback_title, fallback_content)

	def _render_text(self, text: str | None, context: stencil.Context) -> str | None:
		"""
		渲染单个文本模板

		Args:
			text: 模板字符串，None 或空字符串表示不渲染
			context: Stencil 上下文对象

		Returns:
			渲染后的文本，如果输入为 None 或空字符串则返回 None
		"""
		# 如果文本为 None 或空字符串，直接返回 None
		if not text:
			return None

		# 渲染模板
		template_obj = stencil.Template(text)
		rendered = template_obj.render(context)

		# 检查渲染结果
		if rendered is None:
			raise ValueError('模板渲染返回了 None')

		# 处理换行符：将 \n 转换为真正的换行符
		return rendered.replace('\\n', '\n')

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
		}

	def _load_template(self, platform: str, parsed: dict) -> NotificationTemplate | None:
		"""
		加载模板配置

		Args:
			platform: 平台名称
			parsed: 解析后的配置字典

		Returns:
			NotificationTemplate 对象，如果没有配置则返回 None
		"""
		template_value = parsed.get('template')
		if template_value is None:
			default_config = self._load_default_config(platform)
			template_value = default_config.get('template') if default_config else None

		return NotificationTemplate.from_value(template_value)

	def _validate_required_field(self, parsed: dict, field: str) -> bool:
		"""
		验证必需字段是否存在且非空

		Args:
			parsed: 解析后的配置字典
			field: 字段名

		Returns:
			字段存在且非空返回 True，否则返回 False
		"""
		return field in parsed and parsed[field]

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

	def _load_email_config(self) -> EmailConfig | None:
		"""加载邮箱配置"""
		email_notif_config = os.getenv('EMAIL_NOTIF_CONFIG')
		if not email_notif_config:
			return None

		parsed = self._parse_env_config(email_notif_config)
		if not isinstance(parsed, dict):
			return None

		# 验证必需字段
		if not self._validate_required_field(
			parsed=parsed,
			field='user',
		):
			return None
		if not self._validate_required_field(
			parsed=parsed,
			field='pass',
		):
			return None
		if not self._validate_required_field(
			parsed=parsed,
			field='to',
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
			platform_settings=parsed.get('platform_settings'),
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
		if not self._validate_required_field(
			parsed=parsed,
			field='server_url',
		):
			return None
		if not self._validate_required_field(
			parsed=parsed,
			field='device_key',
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
			platform_settings=parsed.get('platform_settings'),
			template=template,
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
			if not self._validate_required_field(
				parsed=parsed,
				field='webhook',
			):
				return None

			# 加载模板
			template = self._load_template(
				platform=platform,
				parsed=parsed,
			)

			return WebhookConfig(
				webhook=parsed['webhook'],
				platform_settings=parsed.get('platform_settings'),
				template=template,
			)

		# 纯字符串，当做 webhook URL，使用默认模板
		default_config = self._load_default_config(platform)
		template_value = default_config.get('template') if default_config else None
		template = NotificationTemplate.from_value(template_value)

		return WebhookConfig(
			webhook=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=template,
		)

	def _load_dingtalk_config(self) -> WebhookConfig | None:
		return self._load_webhook_config(
			platform='dingtalk',
			notif_config_key='DINGTALK_NOTIF_CONFIG',
		)

	def _load_feishu_config(self) -> WebhookConfig | None:
		return self._load_webhook_config(
			platform='feishu',
			notif_config_key='FEISHU_NOTIF_CONFIG',
		)

	def _load_wecom_config(self) -> WebhookConfig | None:
		return self._load_webhook_config(
			platform='wecom',
			notif_config_key='WECOM_NOTIF_CONFIG',
		)

	def _load_pushplus_config(self) -> PushPlusConfig | None:
		"""加载 PushPlus 配置"""
		pushplus_notif_config = os.getenv('PUSHPLUS_NOTIF_CONFIG')
		if not pushplus_notif_config:
			return None

		parsed = self._parse_env_config(pushplus_notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 验证必需字段
			if not self._validate_required_field(
				parsed=parsed,
				field='token',
			):
				return None

			# 加载模板
			template = self._load_template(
				platform='pushplus',
				parsed=parsed,
			)

			return PushPlusConfig(
				token=parsed['token'],
				platform_settings=parsed.get('platform_settings'),
				template=template,
			)

		# 纯字符串，当做 token，使用默认模板
		default_config = self._load_default_config('pushplus')
		template_value = default_config.get('template') if default_config else None
		template = NotificationTemplate.from_value(template_value)

		return PushPlusConfig(
			token=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=template,
		)

	def _load_serverpush_config(self) -> ServerPushConfig | None:
		"""加载 Server 酱配置"""
		serverpush_notif_config = os.getenv('SERVERPUSH_NOTIF_CONFIG')
		if not serverpush_notif_config:
			return None

		parsed = self._parse_env_config(serverpush_notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 验证必需字段
			if not self._validate_required_field(
				parsed=parsed,
				field='send_key',
			):
				return None

			# 加载模板
			template = self._load_template(
				platform='serverpush',
				parsed=parsed,
			)

			return ServerPushConfig(
				send_key=parsed['send_key'],
				platform_settings=parsed.get('platform_settings'),
				template=template,
			)

		# 纯字符串，当做 send_key，使用默认模板
		default_config = self._load_default_config('serverpush')
		template_value = default_config.get('template') if default_config else None
		template = NotificationTemplate.from_value(template_value)

		return ServerPushConfig(
			send_key=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=template,
		)
