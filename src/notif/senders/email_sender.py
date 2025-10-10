import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from notif.models import EmailConfig


class EmailSender:
	def __init__(self, config: EmailConfig):
		"""
		初始化邮件发送器

		Args:
			config: 邮件配置
		"""
		self.config = config

	async def send(self, title: str, content: str):
		"""
		发送邮件

		Args:
			title: 邮件标题
			content: 邮件内容
		"""
		# 智能确定消息类型：配置优先，没配置则自动检测
		msg_type = self._determine_msg_type(content)

		msg = MIMEMultipart()
		msg['From'] = f'AnyRouter Assistant <{self.config.user}>'
		msg['To'] = self.config.to
		msg['Subject'] = title

		body = MIMEText(content, msg_type, 'utf-8')
		msg.attach(body)

		# 如果有自定义 SMTP 服务器，使用它；否则从邮箱地址推断
		if self.config.smtp_server:
			smtp_server = self.config.smtp_server
		else:
			smtp_server = f'smtp.{self.config.user.split("@")[1]}'

		with smtplib.SMTP_SSL(smtp_server, 465) as server:
			server.login(self.config.user, self.config.password)
			server.send_message(msg)

	def _determine_msg_type(self, content: str) -> str:
		"""
		确定消息类型：配置优先，没配置则自动检测

		Args:
			content: 消息内容

		Returns:
			消息类型字符串（'text' 或 'html'）
		"""
		# 1. 配置优先
		if self.config.default_msg_type:
			return self.config.default_msg_type

		# 2. 自动检测
		return self._detect_msg_type(content)

	def _detect_msg_type(self, content: str) -> str:
		"""
		自动检测消息类型

		Args:
			content: 消息内容

		Returns:
			消息类型字符串（'text' 或 'html'）
		"""
		# 常见 HTML 标签列表
		html_tags = [
			r'<html', r'<head', r'<body', r'<div', r'<span', r'<p>',
			r'<br', r'<a\s', r'<img', r'<table', r'<tr', r'<td',
			r'<ul', r'<ol', r'<li', r'<h[1-6]', r'<strong', r'<em',
			r'<b>', r'<i>', r'<u>'
		]

		# 如果内容包含任何 HTML 标签，返回 html
		for tag in html_tags:
			if re.search(tag, content, re.IGNORECASE):
				return 'html'

		# 否则返回 text
		return 'text'
