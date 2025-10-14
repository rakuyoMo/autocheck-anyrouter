import re
import smtplib
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

		msg = MIMEText(content, msg_type, 'utf-8')
		msg['From'] = f'AnyRouter Assistant <{self.config.user}>'
		msg['To'] = self.config.to
		msg['Subject'] = title

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
			消息类型字符串（'plain' 或 'html'）
		"""
		# 1. 配置优先（如果配置了非空值）
		if self.config.platform_settings and 'message_type' in self.config.platform_settings:
			msg_type = self.config.platform_settings['message_type']
			# 如果配置值不为空，则使用配置
			if msg_type:
				return self._normalize_msg_type(msg_type)

		# 2. 自动检测（配置为空或未配置时）
		return self._detect_msg_type(content)

	def _normalize_msg_type(self, msg_type: str) -> str:
		"""
		规范化消息类型，向后兼容

		Args:
			msg_type: 原始消息类型

		Returns:
			规范化后的消息类型（'plain' 或 'html'）
		"""
		# 向后兼容：'text' 转为 'plain'
		if msg_type == 'text':
			print("警告：消息类型 'text' 已弃用，请使用 'plain' 代替")
			return 'plain'
		return msg_type

	def _detect_msg_type(self, content: str) -> str:
		"""
		自动检测消息类型

		Args:
			content: 消息内容

		Returns:
			消息类型字符串（'plain' 或 'html'）
		"""
		# 常见 HTML 标签列表
		html_tags = [
			r'<html',
			r'<head',
			r'<body',
			r'<div',
			r'<span',
			r'<p>',
			r'<br',
			r'<a\s',
			r'<img',
			r'<table',
			r'<tr',
			r'<td',
			r'<ul',
			r'<ol',
			r'<li',
			r'<h[1-6]',
			r'<strong',
			r'<em',
			r'<b>',
			r'<i>',
			r'<u>',
		]

		# 如果内容包含任何 HTML 标签，返回 html
		for tag in html_tags:
			if re.search(tag, content, re.IGNORECASE):
				return 'html'

		# 否则返回 plain
		return 'plain'
