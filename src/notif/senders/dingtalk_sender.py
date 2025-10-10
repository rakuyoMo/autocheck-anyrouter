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

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		data = {
			'msgtype': 'text',
			'text': {
				'content': f'{title}\n{content}'
			}
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'钉钉推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
