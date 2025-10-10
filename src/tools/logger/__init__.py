from .log_level import LogLevel
from .logger import Logger

logger = Logger()

__all__ = [
	'Logger',
	'LogLevel',
	'logger',
]
