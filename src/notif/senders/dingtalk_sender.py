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

	async def send(self, title: str | None, content: str, context_data: dict | None = None):
		"""
		发送钉钉消息

		Args:
			title: 消息标题，`markdown` 模式必须提供非空的标题，纯文本模式下 None 或空字符串则不展示标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			ValueError: 当配置了 markdown 模式但未提供 title 时抛出
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		platform_settings = self.config.platform_settings or {}
		configured_type = platform_settings.get('message_type')

		if configured_type == 'markdown':
			# markdown 模式下必须提供 title
			if not title:
				raise ValueError(
					'钉钉 markdown 模式需要提供非空的 title 参数，请在通知配置的 template.title 中设置标题，或将 message_type 改为纯文本模式'
				)

			# 构建消息体
			msgtype = 'markdown'
			message_body = {
				'title': title,
				'text': content,
			}
		else:
			# 纯文本模式
			msgtype = 'text'
			text_content = f'{title}\n{content}' if title else content
			message_body = {'content': text_content}

		# 构建请求数据
		data = {
			'msgtype': msgtype,
			msgtype: message_body,
		}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(f'钉钉推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}')
