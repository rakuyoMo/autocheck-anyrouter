const fs = require('fs');

/**
 * 读取错误文件内容
 *
 * @param {string} filename - 错误文件名
 * @returns {string} 文件内容，如果文件不存在则返回空字符串
 */
function readErrorFile(filename) {
	try {
		return fs.readFileSync(filename, 'utf8').trim();
	} catch (e) {
		return '';
	}
}

/**
 * 发布 PR 评论的主函数
 *
 * @param {object} github - GitHub API 客户端
 * @param {object} context - GitHub Actions 上下文
 */
async function postPRComment(github, context) {
	// 从环境变量读取检查结果，默认为 pending（fail-safe 设计）
	const formatStatus = process.env.FORMAT_STATUS || 'pending';
	const lintStatus = process.env.LINT_STATUS || 'pending';
	const typeStatus = process.env.TYPE_STATUS || 'pending';
	const coverageStatus = process.env.COVERAGE_STATUS || 'pending';
	const coveragePercent = process.env.COVERAGE_PERCENT || 'N/A';
	const coverageThreshold = parseInt(process.env.COVERAGE_THRESHOLD) || 59;

	// 读取错误详情文件
	const testErrors = readErrorFile('test-errors.txt');

	// 读取覆盖率详细信息（如果存在）
	let coverageDetail = '';
	try {
		coverageDetail = fs.readFileSync('coverage-detail.md', 'utf8');
	} catch (e) {
		// 文件不存在，忽略
	}

	// 构建评论内容
	let comment = '## 🔍 代码质量检查报告\n\n';

	// 静态代码检查部分
	comment += '### 静态代码检查\n';

	const staticCheckFailed = formatStatus === 'failure' || lintStatus === 'failure' || typeStatus === 'failure';

	if (staticCheckFailed) {
		comment += '❌ **失败** - 请修复以下问题：\n\n';
		comment += '> 💡 **提示**：要查看详细的错误注释，请在 Files Changed 标签页右上角点击 ✨ "Try the new experience"，然后在侧边栏中查看错误和警告列表。\n\n';
	} else {
		comment += '✅ **通过**\n\n';
	}

	// 格式化检查
	if (formatStatus === 'success') {
		comment += '- ✅ 代码格式化\n';
	} else if (formatStatus === 'failure') {
		comment += '- ❌ 代码格式化\n';
	} else {
		comment += '- ⏭️ 代码格式化（跳过）\n';
	}

	// 代码规范检查
	if (lintStatus === 'success') {
		comment += '- ✅ 代码规范检查\n';
	} else if (lintStatus === 'failure') {
		comment += '- ❌ 代码规范检查\n';
	} else {
		comment += '- ⏭️ 代码规范检查（跳过）\n';
	}

	// 类型检查
	if (typeStatus === 'success') {
		comment += '- ✅ 类型检查\n';
	} else if (typeStatus === 'failure') {
		comment += '- ❌ 类型检查\n';
	} else {
		comment += '- ⏭️ 类型检查（跳过）\n';
	}

	comment += '\n';

	// 测试覆盖率部分
	comment += '### 测试覆盖率\n';

	if (coverageStatus === 'pending') {
		if (staticCheckFailed) {
			comment += '⏭️ **跳过** - 请先修复静态检查问题\n\n';
			comment += '> 修复静态检查问题后，测试将自动运行\n';
		} else {
			comment += '⏭️ **跳过**\n';
		}
	} else if (coverageStatus === 'success') {
		comment += `✅ **通过** (覆盖率: ${coveragePercent}% ≥ ${coverageThreshold}%)\n\n`;
		if (coverageDetail) {
			comment += '<details>\n<summary>查看覆盖率最低的文件</summary>\n\n';
			comment += coverageDetail;
			comment += '\n</details>\n';
		}
	} else if (coverageStatus === 'failure') {
		// 检查是否有覆盖率数据来区分测试失败和覆盖率不达标
		if (coveragePercent && coveragePercent !== 'N/A') {
			comment += `❌ **失败** (覆盖率: ${coveragePercent}% < ${coverageThreshold}%)\n\n`;
			if (coverageDetail) {
				comment += '<details>\n<summary>查看覆盖率最低的文件</summary>\n\n';
				comment += coverageDetail;
				comment += '\n</details>\n';
			}
		} else {
			comment += '❌ **测试失败** - 部分测试用例未通过\n\n';
			if (testErrors) {
				comment += '<details>\n<summary>查看测试错误详情</summary>\n\n```\n';
				comment += testErrors;
				comment += '\n```\n\n</details>\n';
			}
		}
	}

	comment += '\n---\n';

	// 总结
	const allPassed = !staticCheckFailed && coverageStatus === 'success';

	if (allPassed) {
		comment += '### 🎉 所有检查通过！\n';
	} else if (staticCheckFailed) {
		comment += '### ⚠️ 请先修复静态检查问题\n';
	} else if (coverageStatus === 'failure') {
		// 区分测试失败和覆盖率不达标
		if (coveragePercent && coveragePercent !== 'N/A') {
			comment += '### ⚠️ 请提高测试覆盖率\n';
		} else {
			comment += '### ⚠️ 请修复测试失败的问题\n';
		}
	}
	// 如果 coverageStatus === 'pending' 且静态检查通过，则不显示警告总结

	comment += '\n*🤖 此评论由 GitHub Actions 自动生成*';

	// 创建评论
	await github.rest.issues.createComment({
		owner: context.repo.owner,
		repo: context.repo.repo,
		issue_number: context.issue.number,
		body: comment,
	});
	console.log('✅ 已创建评论');
}

module.exports = { postPRComment };
