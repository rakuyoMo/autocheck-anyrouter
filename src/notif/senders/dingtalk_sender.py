import httpx

from notif.models import WebhookConfig


class DingTalkSender:
	def __init__(self, config: WebhookConfig):
		"""
		初始化钉钉发送器

		Args:
			config: 钉钉 Webhook 配置
		"""
		self.config = config

	async def send(self, title: str, content: str):
		"""
		发送钉钉消息

		Args:
			title: 消息标题
			content: 消息内容
		"""
		data = {
			'msgtype': 'text',
			'text': {
				'content': f'{title}\n{content}'
			}
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			await client.post(self.config.webhook, json=data)
