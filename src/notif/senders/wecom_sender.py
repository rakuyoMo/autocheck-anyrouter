import httpx

from notif.models import WebhookConfig


class WeComSender:
	def __init__(self, config: WebhookConfig):
		"""
		初始化企业微信发送器

		Args:
			config: 企业微信 Webhook 配置
		"""
		self.config = config

	async def send(self, title: str, content: str, context_data: dict | None = None):
		"""
		发送企业微信消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 检查 message_type 配置（确保 platform_settings 不为 None）
		platform_settings = self.config.platform_settings or {}
		message_type = platform_settings.get('message_type', 'markdown')

		# 根据 message_type 选择消息格式
		# 如果 message_type 包含 'markdown'，则直接作为消息类型；否则使用 text 模式
		if message_type and 'markdown' in str(message_type):
			data = {
				'msgtype': message_type,
				message_type: {
					'content': f'**{title}**\n{content}',
				},
			}
		else:
			data = {
				'msgtype': 'text',
				'text': {
					'content': f'{title}\n{content}',
				},
			}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'企业微信推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
