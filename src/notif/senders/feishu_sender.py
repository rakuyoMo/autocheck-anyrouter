import httpx
import stencil

from notif.models import WebhookConfig
from tools.logger import logger


class FeishuSender:
	def __init__(self, config: WebhookConfig):
		"""
		初始化飞书发送器

		Args:
			config: 飞书 Webhook 配置
		"""
		self.config = config

	async def send(self, title: str, content: str, context_data: dict | None = None):
		"""
		发送飞书消息

		Args:
			title: 消息标题
			content: 消息内容
			context_data: 模板渲染的上下文数据

		Raises:
			Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 获取消息类型（确保 platform_settings 不为 None）
		platform_settings = self.config.platform_settings or {}
		message_type = platform_settings.get('message_type', 'card')

		# 动态渲染 color_theme（如果包含模板语法）
		# 默认根据签到结果自动选择颜色（全部成功=绿色，部分成功=橙色，全部失败=红色）
		default_color_theme = (
			'{% if all_success %}green{% else %}{% if partial_success %}orange{% else %}red{% endif %}{% endif %}'
		)
		color_theme = platform_settings.get('color_theme') or default_color_theme
		if context_data and ('{%' in color_theme or '{{' in color_theme):
			try:
				template_obj = stencil.Template(color_theme)
				context = stencil.Context(context_data)
				rendered = template_obj.render(context)
				if rendered:
					color_theme = rendered.strip()
			except Exception as e:
				logger.warning(f'渲染 color_theme 失败（{e}），使用原始值：{color_theme}')

		if message_type in ['card', 'card_v2']:
			# 构造通用的 header 和 elements
			header = {'template': color_theme, 'title': {'content': title, 'tag': 'plain_text'}}
			elements = [{'tag': 'markdown', 'content': content, 'text_align': 'left'}]

			# 根据版本构造卡片数据
			if message_type == 'card_v2':
				# v2.0 卡片：schema + header + body.elements
				card_data = {'schema': '2.0', 'header': header, 'body': {'elements': elements}}
			else:
				# v1.0 卡片：header + elements
				card_data = {'elements': elements, 'header': header}

			data = {'msg_type': 'interactive', 'card': card_data}
		else:
			# 其他情况使用纯文本模式
			data = {'msg_type': 'text', 'text': {'content': f'{title}\n{content}'}}

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(self.config.webhook, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(f'飞书推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}')
