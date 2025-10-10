import httpx

from notif.models import ServerPushConfig


class ServerPushSender:
	def __init__(self, config: ServerPushConfig):
		"""
		初始化 Server 酱发送器

		Args:
			config: Server 酱配置
		"""
		self.config = config

	async def send(self, title: str, content: str):
		"""
		发送 Server 酱消息

		Args:
			title: 消息标题
			content: 消息内容
		"""
		data = {
			'title': title,
			'desp': content
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			await client.post(
				f'https://sctapi.ftqq.com/{self.config.send_key}.send',
				json=data
			)
