import httpx

from notif.models import PushPlusConfig


class PushPlusSender:
	def __init__(self, config: PushPlusConfig):
		"""
		初始化 PushPlus 发送器

		Args:
			config: PushPlus 配置
		"""
		self.config = config

	async def send(self, title: str, content: str):
		"""
		发送 PushPlus 消息

		Args:
			title: 消息标题
			content: 消息内容
		"""
		data = {
			'token': self.config.token,
			'title': title,
			'content': content,
			'template': 'html'
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			await client.post('http://www.pushplus.plus/send', json=data)
