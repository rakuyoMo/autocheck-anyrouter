import httpx

from notif.models import WebhookConfig


class FeishuSender:
	def __init__(self, config: WebhookConfig):
		"""
		初始化飞书发送器

		Args:
			config: 飞书 Webhook 配置
		"""
		self.config = config

	async def send(self, title: str, content: str, context_data: dict | None = None):
		"""
		发送飞书消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 检查是否使用卡片模式（确保 platform_settings 不为 None）
		platform_settings = self.config.platform_settings or {}
		use_card = platform_settings.get('use_card', True)
		color_theme = platform_settings.get('color_theme', 'blue')

		if use_card:
			data = {
				'msg_type': 'interactive',
				'card': {
					'elements': [{'tag': 'markdown', 'content': content, 'text_align': 'left'}],
					'header': {'template': color_theme, 'title': {'content': title, 'tag': 'plain_text'}},
				},
			}
		else:
			data = {'msg_type': 'text', 'text': {'content': f'{title}\n{content}'}}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(f'飞书推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}')
