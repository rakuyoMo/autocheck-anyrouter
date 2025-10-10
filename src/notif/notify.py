import json
import os
from pathlib import Path
from typing import Any, Union

import stencil

from core.models.notification_data import NotificationData
from notif.models import (
	EmailConfig,
	NotificationHandler,
	PushPlusConfig,
	ServerPushConfig,
	WebhookConfig,
)
from notif.senders import (
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
		self.email_config = self._load_email_config()
		self.dingtalk_config = self._load_dingtalk_config()
		self.feishu_config = self._load_feishu_config()
		self.wecom_config = self._load_wecom_config()
		self.pushplus_config = self._load_pushplus_config()
		self.serverpush_config = self._load_serverpush_config()

		# 注册所有通知处理器
		self._handlers = self._register_handlers()

	async def push_message(self, title: str, content: Union[str, NotificationData]):
		"""
		发送通知消息

		Args:
			title: 消息标题
			content: 消息内容，可以是字符串或 NotificationData 结构
		"""
		# 检查是否有可用的通知处理器
		if not self._handlers:
			logger.warning("没有可用的通知处理器，跳过通知提醒")
			return

		for handler in self._handlers:
			# 检查配置是否存在
			if not handler.is_available():
				logger.info("未配置，跳过推送", handler.name)
				continue

			try:
				# 渲染模板
				rendered_content = self._render_content(
					config=handler.config, 
					content=content
				)

				# 发送消息
				await handler.send_func(
					title=title,
					content=rendered_content
				)

				logger.success("消息推送成功！", handler.name)

			except Exception as e:
				logger.error(
					message=f"消息推送失败！原因：{str(e)}",
					tag=handler.name,
					exc_info=True
				)

	def _register_handlers(self) -> list[NotificationHandler]:
		"""
		注册所有通知处理器

		Returns:
			通知处理器列表
		"""
		handlers = []

		# 邮箱
		if self.email_config:
			sender = EmailSender(self.email_config)
			handlers.append(
				NotificationHandler(
					name='邮箱',
					config=self.email_config,
					send_func=sender.send
				)
			)

		# PushPlus
		if self.pushplus_config:
			sender = PushPlusSender(self.pushplus_config)
			handlers.append(
				NotificationHandler(
					name='PushPlus',
					config=self.pushplus_config,
					send_func=sender.send
				)
			)

		# Server 酱
		if self.serverpush_config:
			sender = ServerPushSender(self.serverpush_config)
			handlers.append(
				NotificationHandler(
					name='Server 酱',
					config=self.serverpush_config,
					send_func=sender.send
				)
			)

		# 钉钉
		if self.dingtalk_config:
			sender = DingTalkSender(self.dingtalk_config)
			handlers.append(
				NotificationHandler(
					name='钉钉',
					config=self.dingtalk_config,
					send_func=sender.send
				)
			)

		# 飞书
		if self.feishu_config:
			sender = FeishuSender(self.feishu_config)
			handlers.append(
				NotificationHandler(
					name='飞书',
					config=self.feishu_config,
					send_func=sender.send
				)
			)

		# 企业微信
		if self.wecom_config:
			sender = WeComSender(self.wecom_config)
			handlers.append(
				NotificationHandler(
					name='企业微信',
					config=self.wecom_config,
					send_func=sender.send
				)
			)

		return handlers

	def _render_content(self, config: Any, content: Union[str, NotificationData]) -> str:
		"""
		渲染消息内容（处理模板）

		Args:
			config: 配置对象（需要有 template 属性）
			content: 原始内容

		Returns:
			渲染后的内容
		"""
		if isinstance(content, NotificationData) and config.template:
			return self._render_template(
				template=config.template, 
				data=content
			)
		return str(content)

	def _render_template(self, template: str, data: NotificationData) -> str:
		"""
		渲染模板

		注意: Stencil 模板引擎有以下限制:
		1. 不支持比较操作符 (==, !=, <, > 等)
		2. 不支持字典的点访问，只能访问对象属性
		因此我们提供分组的账号列表和对象形式的数据
		"""
		try:
			# 分组账号（因为 Stencil 不支持 == 比较）
			success_accounts = [acc for acc in data.accounts if acc.status == 'success']
			failed_accounts = [acc for acc in data.accounts if acc.status != 'success']

			context_data = {
				'timestamp': data.timestamp,
				'stats': data.stats,  # dataclass 对象，支持 {{ stats.success_count }}

				# 提供分组的账号列表（AccountResult 对象）
				'success_accounts': success_accounts,
				'failed_accounts': failed_accounts,

				# 保留完整列表供需要的模板使用
				'accounts': data.accounts,  # AccountResult 对象列表

				# 便利变量：布尔标志
				'has_success': len(success_accounts) > 0,
				'has_failed': len(failed_accounts) > 0,
				'all_success': len(failed_accounts) == 0,
				'all_failed': len(success_accounts) == 0,
				'partial_success': len(success_accounts) > 0 and len(failed_accounts) > 0,
			}

			# 解析并渲染模板
			template_obj = stencil.Template(template)
			context = stencil.Context(context_data)
			rendered_result = template_obj.render(context)

			# 检查渲染结果是否为 None
			if rendered_result is None:
				raise ValueError('模板渲染返回了 None')

			# 处理换行符：将 \n 转换为真正的换行符
			rendered_result = rendered_result.replace('\\n', '\n')
			return rendered_result

		except Exception as e:
			logger.error(
				message=f"模板渲染失败：{e}",
				exc_info=True
			)

			# 如果模板渲染失败，返回简单格式
			return f'{data.timestamp}\\n\\n' + '\\n\\n'.join([
				f'[{"成功" if account.status == "success" else "失败"}] {account.name}'
				for account in data.accounts
			])

	def _load_default_config(self, platform: str) -> dict[str, Any] | None:
		"""加载默认配置文件"""
		config_file = self.config_dir / f'{platform}.json'
		if config_file.exists():
			try:
				with open(config_file, 'r', encoding='utf-8') as f:
					return json.load(f)
			except Exception as e:
				logger.warning(f"加载默认配置文件 {config_file} 失败：{e}")
		return None

	def _parse_env_config(self, env_value: str) -> Union[str, dict[str, Any]]:
		"""解析环境变量配置"""
		try:
			# 尝试解析为 JSON
			return json.loads(env_value)
		except json.JSONDecodeError:
			# 如果不是 JSON，就当做纯字符串（Token 或 Webhook URL）
			return env_value

	def _load_email_config(self) -> EmailConfig | None:
		"""加载邮箱配置"""
		email_notif_config = os.getenv('EMAIL_NOTIF_CONFIG')
		if not email_notif_config:
			return None

		# 解析失败
		parsed = self._parse_env_config(email_notif_config)
		if not isinstance(parsed, dict):
			return None

		# 缺少必需字段
		if 'user' not in parsed or 'pass' not in parsed or 'to' not in parsed:
			return None

		# 如果 template 为 None，则使用默认模板
		template = parsed.get('template')
		if template is None:
			default_config = self._load_default_config('email')
			template = default_config.get('template') if default_config else None

		return EmailConfig(
			user=parsed['user'],
			password=parsed['pass'],
			to=parsed['to'],
			smtp_server=parsed.get('smtp_server'),
			platform_settings=parsed.get('platform_settings'),
			template=template
		)

	def _load_webhook_config(self, platform: str, notif_config_key: str) -> WebhookConfig | None:
		"""加载 Webhook 配置的通用方法"""
		notif_config = os.getenv(notif_config_key)
		if not notif_config:
			return None

		parsed = self._parse_env_config(notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 缺少必需字段
			if 'webhook' not in parsed:
				return None

			# 如果 template 为 None，则使用默认模板
			template = parsed.get('template')
			if template is None:
				default_config = self._load_default_config(platform)
				template = default_config.get('template') if default_config else None

			return WebhookConfig(
				webhook=parsed['webhook'],
				platform_settings=parsed.get('platform_settings'),
				template=template
			)

		# 纯字符串，当做 webhook URL，使用默认模板
		default_config = self._load_default_config(platform)
		return WebhookConfig(
			webhook=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=default_config.get('template') if default_config else None
		)

	def _load_dingtalk_config(self) -> WebhookConfig | None:
		return self._load_webhook_config('dingtalk', 'DINGTALK_NOTIF_CONFIG')

	def _load_feishu_config(self) -> WebhookConfig | None:
		return self._load_webhook_config('feishu', 'FEISHU_NOTIF_CONFIG')

	def _load_wecom_config(self) -> WebhookConfig | None:
		return self._load_webhook_config('wecom', 'WECOM_NOTIF_CONFIG')

	def _load_pushplus_config(self) -> PushPlusConfig | None:
		"""加载 PushPlus 配置"""
		pushplus_notif_config = os.getenv('PUSHPLUS_NOTIF_CONFIG')
		if not pushplus_notif_config:
			return None

		parsed = self._parse_env_config(pushplus_notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 缺少必需字段
			if 'token' not in parsed:
				return None

			# 如果 template 为 None，则使用默认模板
			template = parsed.get('template')
			if template is None:
				default_config = self._load_default_config('pushplus')
				template = default_config.get('template') if default_config else None

			return PushPlusConfig(
				token=parsed['token'],
				platform_settings=parsed.get('platform_settings'),
				template=template
			)

		# 纯字符串，当做 token，使用默认模板
		default_config = self._load_default_config('pushplus')
		return PushPlusConfig(
			token=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=default_config.get('template') if default_config else None
		)

	def _load_serverpush_config(self) -> ServerPushConfig | None:
		"""加载 Server 酱配置"""
		serverpush_notif_config = os.getenv('SERVERPUSH_NOTIF_CONFIG')
		if not serverpush_notif_config:
			return None

		parsed = self._parse_env_config(serverpush_notif_config)

		# 字典格式配置
		if isinstance(parsed, dict):
			# 缺少必需字段
			if 'send_key' not in parsed:
				return None

			# 如果 template 为 None，则使用默认模板
			template = parsed.get('template')
			if template is None:
				default_config = self._load_default_config('serverpush')
				template = default_config.get('template') if default_config else None

			return ServerPushConfig(
				send_key=parsed['send_key'],
				platform_settings=parsed.get('platform_settings'),
				template=template
			)

		# 纯字符串，当做 send_key，使用默认模板
		default_config = self._load_default_config('serverpush')
		return ServerPushConfig(
			send_key=parsed,
			platform_settings=default_config.get('platform_settings') if default_config else None,
			template=default_config.get('template') if default_config else None
		)
