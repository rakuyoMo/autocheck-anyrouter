#!/usr/bin/env python3

import json
import os
import sys


def generate_coverage_detail(
	coverage_json_path: str = 'coverage.json',
	output_path: str = 'coverage-detail.md',
	top_n: int = 10,
) -> None:
	"""生成覆盖率详细信息的 Markdown 报告

	Args:
		coverage_json_path: 覆盖率 JSON 文件路径
		output_path: 输出的 Markdown 文件路径
		top_n: 显示覆盖率最低的文件数量
	"""
	try:
		with open(coverage_json_path, 'r') as f:
			data = json.load(f)

		files = data['files']

		# 生成 Markdown 表格
		md = '| 文件 | 覆盖率 | 语句 | 未覆盖 |\n'
		md += '|------|--------|------|--------|\n'

		# 只显示覆盖率最低的前 N 个文件
		sorted_files = sorted(files.items(), key=lambda x: x[1]['summary']['percent_covered'])[:top_n]

		for filepath, info in sorted_files:
			summary = info['summary']
			percent = summary['percent_covered']
			num_statements = summary['num_statements']
			missing_lines = summary['missing_lines']

			# 根据覆盖率设置图标
			if percent >= 80:
				icon = '🟢'
			elif percent >= 60:
				icon = '🟡'
			else:
				icon = '🔴'

			md += f'| {filepath} | {icon} {percent:.1f}% | {num_statements} | {missing_lines} |\n'

		with open(output_path, 'w') as f:
			f.write(md)

		print(f'✅ 覆盖率详细信息生成成功: {output_path}')

	except Exception as e:
		error_msg = f'生成覆盖率详情失败: {str(e)}\n'
		with open(output_path, 'w') as f:
			f.write(error_msg)
		print(f'❌ {error_msg}')
		sys.exit(1)


if __name__ == '__main__':
	# 从环境变量读取配置，提供默认值
	top_n = int(os.environ.get('COVERAGE_DETAIL_FILE_COUNT', '10'))
	generate_coverage_detail(top_n=top_n)
