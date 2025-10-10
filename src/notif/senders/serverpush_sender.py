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

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		data = {
			'title': title,
			'desp': content,
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(
				f'https://sctapi.ftqq.com/{self.config.send_key}.send',
				json=data,
			)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'Server 酱推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
