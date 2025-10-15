# 更新日志

本项目的所有重要变更都将记录在此文件中。

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

#### Change
* 统一企业微信配置字段：将 `markdown_style` 改为 `message_type`，与其他通知平台保持一致。

---

## [1.2.0] (2025-10-15)

#### Add
* 添加 CHANGELOG.md 项目变更日志文件。[#10]
* 增加邮箱的配置示例。[#9]
* 飞书通知支持动态卡片颜色，可根据签到结果自动调整卡片主题色（绿色/橙色/红色）。[#11]
* 飞书通知新增支持 v2.0 卡片格式（`message_type: "card_v2"`）。[#11]

#### Change
* 统一飞书和钉钉的配置字段：将飞书的 `use_card` 改为 `message_type`，与钉钉保持一致。[#11]
* 重命名邮箱的配置字段：`default_msg_type` > `message_type`。[#9]
* 优化邮件消息类型检测逻辑，支持空配置时自动识别。[#9]
* 更新 ruff 版本至 0.14.0。[#11]
* 默认折叠项目架构说明。[#9]

---

## [1.1.0] (2025-10-14)

#### Add
* 钉钉消息支持 markdown 格式。[#6]
* 添加图片示例。[#6]
* 完善测试用例。[#6]

#### Fix
* 修复邮件正文在 QQ 邮箱和 Gmail 中显示异常的问题。[#5]
* 修复静态检查 Action 没有在 File changes 汇报错误的问题。[#5]

#### Change
* 集成测试改为使用多账号的测试数据。[#6]
* 完善文档。[#6]

---

## [1.0.2] (2025-10-14)

#### Add
* 集成 Codecov 测试覆盖率工具。[#4]
* 增加 PR 代码检查的 CI 流程。[#1]
* 测试覆盖率不允许低于 59%。[#2]
* 调整评论区汇报内容。[#1]

#### Fix
* 修复测试覆盖率报告发送失败的问题。[#2]
* 修复 checkout 错误。[#2]
* 修复 Ruff 问题。[#1]
* 修复余额历史缓存错误的问题。

#### Change
* 重构检查流程的 Github Action。[#2]
* 重构测试模块。[#1]
* 调整 mise 任务封装。
* 使用 `astral-sh/ruff-action@v3` 代替 `chartboost/ruff-action@v1`。[#1]
* 完善文档。[#3]
* 根据最新的测试模块，完善说明文档。[#1]

---

## [1.0.1] (2025-10-10)

#### Fix
* 修复 Action 没有配置 `SHOW_SENSITIVE_INFO` 的问题。

---

## [1.0.0] (2025-10-10)

#### Add
* 基于 AnyRouter 的多账号自动签到功能。
* 多平台通知支持（邮箱、钉钉、飞书、企业微信、PushPlus、Server 酱），支持 Stencil 模板自定义通知内容。
* 智能隐私保护，公开仓库自动脱敏敏感信息。
* 支持 Fork 定时运行和 Composite Action 两种使用方式。
* 完善的 CI/CD 工作流、测试体系和项目文档。

[1.2.0]: https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.2.0
[1.1.0]: https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.1.0
[1.0.2]: https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.0.2
[1.0.1]: https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.0.1
[1.0.0]: https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.0.0

[#1]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/1
[#2]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/2
[#3]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/3
[#4]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/4
[#5]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/5
[#6]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/6
[#9]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/9
[#10]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/10
[#11]: https://github.com/rakuyoMo/autocheck-anyrouter/pull/11
