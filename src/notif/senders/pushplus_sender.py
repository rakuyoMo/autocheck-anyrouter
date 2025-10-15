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

	async def send(self, title: str, content: str, context_data: dict | None = None):
		"""
		发送 PushPlus 消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		data = {
			'token': self.config.token,
			'title': title,
			'content': content,
			'template': 'html',
		}
		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post('http://www.pushplus.plus/send', json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'PushPlus 推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
