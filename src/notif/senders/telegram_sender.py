import httpx

from notif.models import TelegramConfig


class TelegramSender:
	def __init__(self, config: TelegramConfig):
		"""
		初始化 Telegram 发送器

		Args:
			config: Telegram 配置
		"""
		self.config = config

	async def send(self, title: str | None, content: str, context_data: dict | None = None):
		"""
		发送 Telegram 消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 构建消息文本
		if title:
			message = f'<b>{title}</b>\n\n{content}'
		else:
			message = content

		# 获取 message_type 设置，默认为 HTML
		message_type = 'HTML'
		if self.config.platform_settings:
			message_type = self.config.platform_settings.get('message_type', 'HTML')

		# 构建请求数据
		data = {
			'chat_id': self.config.chat_id,
			'text': message,
			'parse_mode': message_type,
		}

		# 如果有其他平台特定设置，添加到请求中
		if self.config.platform_settings:
			# 支持的可选参数
			optional_params = [
				'disable_web_page_preview',
				'disable_notification',
				'protect_content',
				'reply_to_message_id',
			]
			for param in optional_params:
				if param in self.config.platform_settings:
					data[param] = self.config.platform_settings[param]

		# 构建 API URL
		api_url = f'https://api.telegram.org/bot{self.config.bot_token}/sendMessage'

		# 发送请求
		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(api_url, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(
					f'Telegram 推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}'
				)
