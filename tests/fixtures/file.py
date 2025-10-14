import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_balance_hash_file():
	"""提供临时的余额 hash 文件"""
	with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
		temp_path = Path(f.name)
	yield temp_path
	temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_summary_file():
	"""提供临时的 summary 文件"""
	with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
		temp_path = Path(f.name)
	yield temp_path
	temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_file_manager():
	"""管理多个临时文件的 fixture"""
	files = []

	def create_temp(content: str = '', suffix: str = '.txt') -> Path:
		"""创建临时文件并返回路径"""
		with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix) as f:
			if content:
				f.write(content)
			temp_path = Path(f.name)
		files.append(temp_path)
		return temp_path

	yield create_temp

	for file_path in files:
		file_path.unlink(missing_ok=True)
