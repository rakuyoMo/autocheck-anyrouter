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

	async def send(self, title: str, content: str):
		"""
		发送企业微信消息

		Args:
			title: 消息标题
			content: 消息内容

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 检查 markdown_style 配置（确保 platform_settings 不为 None）
		platform_settings = self.config.platform_settings or {}
		markdown_style = platform_settings.get('markdown_style', 'markdown')

		# 根据 markdown_style 选择消息格式
		# 如果 markdown_style 包含 'markdown'，则直接作为消息类型；否则使用 text 模式
		if markdown_style and 'markdown' in str(markdown_style):
			data = {
				'msgtype': markdown_style,
				markdown_style: {
					'content': f'**{title}**\n{content}'
				}
			}
		else:
			data = {
				'msgtype': 'text',
				'text': {'content': f'{title}\n{content}'}
			}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'企业微信推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
