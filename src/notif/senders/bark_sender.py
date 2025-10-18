import httpx

from notif.models import BarkConfig


class BarkSender:
	def __init__(self, config: BarkConfig):
		"""
		初始化 Bark 发送器

		Args:
		    config: Bark 配置
		"""
		self.config = config

	async def send(self, title: str | None, content: str, context_data: dict | None = None):
		"""
		发送 Bark 消息

		Args:
		    title: 消息标题
		    content: 消息内容
		    context_data: 模板渲染的上下文数据

		Raises:
		    Exception: 当 HTTP 响应状态码不是 2xx 时抛出异常
		"""
		# 构建请求体
		data = {
			'device_key': self.config.device_key,
			'body': content,
		}

		# 添加标题
		if title:
			data['title'] = title

		# 从 platform_settings 中提取参数
		if self.config.platform_settings:
			# 通知显示设置
			display = self.config.platform_settings.get('display', {})
			if display:
				if 'subtitle' in display and display['subtitle']:
					data['subtitle'] = display['subtitle']
				if 'badge' in display and display['badge'] is not None:
					data['badge'] = display['badge']
				if 'icon' in display and display['icon']:
					data['icon'] = display['icon']
				if 'group' in display and display['group']:
					data['group'] = display['group']

			# 声音和提醒级别设置
			alert = self.config.platform_settings.get('alert', {})
			if alert:
				if 'sound' in alert and alert['sound']:
					data['sound'] = alert['sound']
				if 'call' in alert and alert['call']:
					data['call'] = alert['call']
				if 'level' in alert and alert['level']:
					data['level'] = alert['level']
				if 'volume' in alert and alert['volume']:
					data['volume'] = alert['volume']

			# 交互行为设置
			interaction = self.config.platform_settings.get('interaction', {})
			if interaction:
				if 'url' in interaction and interaction['url']:
					data['url'] = interaction['url']
				if 'action' in interaction and interaction['action']:
					data['action'] = interaction['action']
				if 'autoCopy' in interaction and interaction['autoCopy']:
					data['autoCopy'] = interaction['autoCopy']
				if 'copy' in interaction and interaction['copy']:
					data['copy'] = interaction['copy']

			# 其他设置
			options = self.config.platform_settings.get('options', {})
			if options:
				if 'isArchive' in options and options['isArchive']:
					data['isArchive'] = options['isArchive']

		# 发送 POST 请求到 Bark API
		push_url = f'{self.config.server_url.rstrip("/")}/push'

		async with httpx.AsyncClient(timeout=30.0) as client:
			response = await client.post(push_url, json=data)

			# 检查响应状态码
			if not response.is_success:
				raise Exception(f'Bark 推送失败，HTTP 状态码：{response.status_code}，响应内容：{response.text[:200]}')
