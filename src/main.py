import asyncio
import sys

from core import CheckinService
from tools.logger import logger


def run_main():
    """运行主函数的包装函数"""
    try:
        service = CheckinService()
        asyncio.run(service.run())

    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"程序执行过程中发生错误：{e}")
        sys.exit(1)


if __name__ == '__main__':
    run_main()
