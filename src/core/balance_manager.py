import hashlib
import json
from pathlib import Path

from tools.logger import logger


class BalanceManager:
	"""余额管理器"""

	def __init__(self, balance_hash_file: Path):
		"""初始化余额管理器

		Args:
			balance_hash_file: 余额 hash 文件路径
		"""
		self.balance_hash_file = balance_hash_file

	def load_balance_hash(self) -> dict[str, str] | None:
		"""加载余额 hash 字典

		Returns:
			字典格式：{api_user_hash: balance_hash}，加载失败返回 None
		"""
		try:
			if self.balance_hash_file.exists():
				with open(self.balance_hash_file, 'r', encoding='utf-8') as f:
					content = f.read().strip()
					if not content:
						return None
					return json.loads(content)

		except (OSError, IOError) as e:
			logger.warning(f'加载余额哈希失败：{e}')

		except json.JSONDecodeError as e:
			logger.warning(f'余额哈希文件格式无效：{e}')

		except Exception as e:
			logger.warning(f'加载余额哈希时发生意外错误：{e}')

		return None

	def save_balance_hash(self, balance_hash_dict: dict[str, str]):
		"""保存余额 hash 字典

		Args:
			balance_hash_dict: 字典格式 {api_user_hash: balance_hash}
		"""
		try:
			# 确保父目录存在
			self.balance_hash_file.parent.mkdir(parents=True, exist_ok=True)
			with open(self.balance_hash_file, 'w', encoding='utf-8') as f:
				json.dump(balance_hash_dict, f, ensure_ascii=False, indent=2)

		except (OSError, IOError) as e:
			logger.warning(f'保存余额哈希失败：{e}')

		except Exception as e:
			logger.warning(f'保存余额哈希时发生意外错误：{e}')

	@staticmethod
	def generate_account_key(api_user: str) -> str:
		"""生成账号标识的 hash

		Args:
			api_user: API 用户标识

		Returns:
			完整的 SHA256 hash
		"""
		return hashlib.sha256(api_user.encode('utf-8')).hexdigest()

	@staticmethod
	def generate_balance_hash(quota: float, used: float) -> str:
		"""生成单个账号余额的 hash

		Args:
			quota: 总额度
			used: 已使用额度

		Returns:
			完整的 SHA256 hash
		"""
		balance_data = f'{quota}_{used}'
		return hashlib.sha256(balance_data.encode('utf-8')).hexdigest()
