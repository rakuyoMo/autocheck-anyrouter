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

	async def send(self, title: str, content: str, context_data: dict | None = None):
		"""
		发送钉钉消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 获取消息类型
		platform_settings = self.config.platform_settings
		message_type = platform_settings.get('message_type', '') if platform_settings else ''

		# 根据消息类型构造消息体
		if message_type == 'markdown':
			msgtype = 'markdown'
			message_body = {'title': title, 'text': content}
		else:
			# 其他情况都使用纯文本
			msgtype = 'text'
			message_body = {'content': f'{title}\n{content}'}

		# 统一构造最终数据
		data = {
			'msgtype': msgtype,
			msgtype: message_body,
		}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(f'钉钉推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}')
