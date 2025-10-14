from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from core import CheckinService
from notif import notify


class MockDependencies:
	"""统一的 CheckinService 依赖 Mock 对象"""

	def __init__(self):
		self.check_in_account = AsyncMock(return_value=(True, {'success': True, 'quota': 25.0, 'used_quota': 5.0}))
		self.load_balance_hash = MagicMock(return_value='same_hash')
		self.generate_balance_hash = MagicMock(return_value='same_hash')
		self.save_balance_hash = MagicMock()
		self.generate_github_summary = MagicMock()
		self.push_message = AsyncMock()

	def apply_to_service(self, service: CheckinService):
		"""
		将所有 mock 应用到 service 实例

		Args:
			service: CheckinService 实例

		Returns:
			ExitStack: 包含所有 patch 的上下文管理器
		"""
		stack = ExitStack()
		stack.enter_context(patch.object(service, '_check_in_account', self.check_in_account))
		stack.enter_context(patch.object(service, '_load_balance_hash', self.load_balance_hash))
		stack.enter_context(patch.object(service, '_generate_balance_hash', self.generate_balance_hash))
		stack.enter_context(patch.object(service, '_save_balance_hash', self.save_balance_hash))
		stack.enter_context(patch.object(service, '_generate_github_summary', self.generate_github_summary))
		stack.enter_context(patch.object(notify, 'push_message', self.push_message))
		return stack
