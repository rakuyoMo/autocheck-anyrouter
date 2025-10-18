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

	async def send(self, title: str | None, content: str, context_data: dict | None = None):
		"""
		发送企业微信消息

		Args:
			title: 消息标题，为 None 或空字符串时不展示标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		platform_settings = self.config.platform_settings or {}
		configured_type = platform_settings.get('message_type')

		# 确定消息类型：只接受 markdown 和 markdown_v2，其他情况一律使用 text
		message_type = configured_type if configured_type in ['markdown', 'markdown_v2'] else 'text'

		# 构建消息内容
		if title:
			formatted_title = f'**{title}**' if message_type != 'text' else title
			message_content = f'{formatted_title}\n{content}'
		else:
			message_content = content

		# 构建请求数据
		data = {
			'msgtype': message_type,
			message_type: {
				'content': message_content,
			},
		}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'企业微信推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
