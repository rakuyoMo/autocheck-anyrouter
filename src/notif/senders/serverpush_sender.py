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

	async def send(self, title: str | None, content: str, context_data: dict | None = None):
		"""
		发送 Server 酱消息

		Args:
			title: 消息标题，Server 酱要求必须提供非空的标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			ValueError: 当 title 为 None 或空字符串时抛出
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		if not title:
			raise ValueError('Server 酱推送需要提供非空的 title 参数，请在通知配置的 template.title 中设置标题')

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
