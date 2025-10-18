# autocheck-anyrouter

> 基于 Python 的 AnyRouter 多账号自动签到工具，支持多种通知方式和智能隐私保护 </br>
> 🩷 本项目基于 [anyrouter-check-in](https://github.com/millylee/anyrouter-check-in) 实现核心签到功能，特别感谢 [Milly](https://github.com/millylee) 的付出与开源精神！

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/rakuyoMo/autocheck-anyrouter)](https://github.com/rakuyoMo/autocheck-anyrouter/releases)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/rakuyoMo/autocheck-anyrouter/ci.yml?branch=main)](https://github.com/rakuyoMo/autocheck-anyrouter/actions)
[![codecov](https://codecov.io/gh/rakuyoMo/autocheck-anyrouter/branch/main/graph/badge.svg)](https://codecov.io/gh/rakuyoMo/autocheck-anyrouter)
[![License](https://img.shields.io/badge/license-BSD--2--Clause-green.svg)](LICENSE)

## 功能特性

### 核心功能
- [x] 单个/多账号自动签到
- [x] 多平台通知，并且支持通过 Stencil 模板自定义通知内容
- [x] 隐私保护和账号信息脱敏
- [x] 同时支持 Fork 定时运行、Composite Action 调用两种方式

### 隐私保护

工具支持智能隐私保护：

> 隐私保护不影响通知内容，仅作用于 GitHub Actions Step Summary 以及 GitHub Action 的日志。

- **公开仓库**：自动脱敏账号名称和余额信息
- **私有仓库**：显示完整信息
- **手动控制**：通过 `ACTIONS_RUNNER_DEBUG` 或 `SHOW_SENSITIVE_INFO` 环境变量控制强制展示

## 使用方式

### 方式一：Fork 后定时签到

1. **Fork 本仓库**
  - 点击右上角 "Fork" 按钮

2. **获取账号信息**
  - 访问 [AnyRouter](https://anyrouter.top/register?aff=sL91) 并登录
  - 打开开发者工具 (F12)
  - 获取 `session` cookie 和 `New-Api-User` 请求头值

3. **配置环境变量**
  - 进入 fork 后仓库的 `Settings` > `Environments` > `Environment secrets`
  - 创建名为 `production` 的环境
  - 参考 [账号配置](#账号配置) 添加环境变量

4. **启用 Actions**
  - 进入 `Actions` 选项卡
  - 启用 Actions，工作流将每 6 小时自动运行一次

> ⚠️ 关于签到时间的特别说明：
> - Github Action 可能会[出现延迟](https://docs.github.com/zh/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)，所以本定时只能满足 “当天一定会签到”，无法精准控制签到时间。
> - AnyRouter 主站的签到逻辑似乎是 “本次签到后 24 小时，可再次签到”，似乎并非 “0 点后可再次签到”。

签到成功后将在 Summary 面板展示签到结果：

<details>
<summary>脱敏示例（公开仓库默认展示）</summary>

![签到成功脱敏示例](/assets/check-in-success-desensitization.png)

</details>

<details>
<summary>非脱敏示例（私有仓库或开启调试模式）</summary>

![签到成功示例](/assets/check-in-success.png)

</details>

### 方式二：在自有仓库中使用 Composite Action

先参照 [方式一](#方式一fork-后定时签到) 中的内容配置环境变量。然后在您的仓库中创建 `.github/workflows/checkin.yml` 文件：

```yaml
name: AnyRouter 自动签到
on:
  schedule:
    - cron: '0 */6 * * *'  # 每隔 6 小时执行一次，或其他您需要的时间
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - name: 执行签到
        uses: rakuyoMo/autocheck-anyrouter@v1
        with:
          # 从环境变量加载账号信息
          accounts: ${{ secrets.ANYROUTER_ACCOUNTS }}
          # 可选：是否显示敏感信息，默认为 `false`
          show-sensitive-info: false
          # 可选：配置通知方式
          dingtalk-notif-config: ${{ secrets.DINGTALK_NOTIF_CONFIG }}
          email-notif-config: ${{ secrets.EMAIL_NOTIF_CONFIG }}
          # ... 其他通知配置
```

## 配置说明

### 账号配置

- `name`（可选）：账号显示名称
- `cookies`：登录后的 session cookie
- `api_user`：API 用户标识

配置格式：
```json5
[
  {
    "name": "账号1",
    "cookies": {
      "session": "..."
    },
    "api_user": "12345"
  },
  {
    "cookies": {
      "session": "..."
    },
    "api_user": "67890"
  }
]
```

### 通知配置

本系统支持多平台通知：
- [x] 邮箱：`EMAIL_NOTIF_CONFIG`
- [x] [钉钉机器人](https://open.dingtalk.com/document/robots/custom-robot-access)：`DINGTALK_NOTIF_CONFIG`
- [x] [飞书机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)：`FEISHU_NOTIF_CONFIG`
- [x] [企业微信](https://developer.work.weixin.qq.com/document/path/99110)：`WECOM_NOTIF_CONFIG`
- [x] [PushPlus](https://www.pushplus.plus/)：`PUSHPLUS_NOTIF_CONFIG`
- [x] [Server 酱](https://sct.ftqq.com/)：`SERVERPUSH_NOTIF_CONFIG`
- [x] [Bark](https://bark.day.app/)：`BARK_NOTIF_CONFIG`

除了 Bark 和邮箱外，其余平台的配置字段均有两种用法：
- 设置为纯字符串：代表 WebHook、Key 或者 Token，此时将使用 [默认配置](/src/notif/configs) 发送通知。
- 设置为 JSON：高级配置，此时可设置模板样式（`template`），或者一些平台配置（`platform_settings`）。具体可查看：
  - [默认配置](/src/notif/configs)
  - [.env.test.example](.env.test.example) 中的简单示例
  - [自定义通知模板](#自定义通知模板)，展示自定义模板的使用方法，并展示了一些配置后的示例效果

您可以在 `Environment secrets` 中添加相应的配置。如下图所示：
<img src="/assets/github-env-notif-config-example.png" alt="环境变量配置示例" width="500" style="max-width: 100%;" />

通知默认只在以下情况时触发，且暂不支持通过环境变量控制触发时机：
- 首次运行时
- 余额发生变化时
- 某个账号签到失败时

### 自定义通知模板

支持使用 [Stencil](https://stencil.pyllyukko.com/) 模板语法自定义通知内容。模板配置支持分别自定义通知的标题和内容。

**模板格式**：

从 [v1.3.0](https://github.com/rakuyoMo/autocheck-anyrouter/releases/tag/v1.3.0) 版本开始，`template` 字段支持对象格式：
```jsonc
{
  "template": {
    "title": "通知标题模板",   // 标题模板。部分平台要求必须设置标题，不强制要求的平台如果不设置，或者设置为空字符串时不展示标题
    "content": "通知内容模板"  // 内容模板
  }
}
```

为保持向后兼容，旧的字符串格式仍然支持：
```jsonc
{
  "template": "通知内容模板"  // 字符串格式会使用默认标题 "AnyRouter 签到提醒"
}
```

**可用变量**：

基础变量：

> **注意**：<br>
> 从 v1.3.0 开始，`accounts` 包含所有账号的完整结果。您可以使用下面的分组列表来筛选特定类型的账号。

- `timestamp`: 执行时间
- `stats`: 统计数据（success_count, failed_count, total_count）
- `accounts`: 所有账号的结果列表（name, status, quota, used, balance_changed, error）

账号状态分组：
- `success_accounts`: 成功账号列表
- `failed_accounts`: 失败账号列表
- `has_success`: 有成功的账号
- `has_failed`: 有失败的账号
- `all_success`: 所有账号都成功
- `all_failed`: 所有账号都失败
- `partial_success`: 部分账号成功

余额变化追踪（v1.3.0+）：

> **注意**：<br>
> 余额变化相关变量仅包含能够成功获取到余额信息的账号（通常为签到成功的账号）。失败账号的 `balance_changed` 字段通常为 `None`（无法判断）。

- `balance_changed_accounts`: 余额发生变化的账号列表
- `balance_unchanged_accounts`: 余额未发生变化的账号列表
- `has_balance_changed`: 是否有账号余额发生变化
- `has_balance_unchanged`: 是否有账号余额未发生变化
- `all_balance_changed`: 所有账号余额都发生变化
- `all_balance_unchanged`: 所有账号余额都未发生变化

以上变量在 `title` 和 `content` 模板中**均可使用**。

**重要说明**：

**关于 title 的限制**：
- ✅ **支持空 title（不展示标题）**：企业微信、飞书、PushPlus
- ⚠️ **部分支持**：钉钉（纯文本模式支持空 title；markdown 模式需要 title，不设置会抛出错误）
- ❌ **必须提供 title**：邮箱、Server 酱（不设置会抛出错误）

**模板引擎限制**：
由于 Stencil 模板引擎的限制，请注意以下事项：
- ❌ 不支持比较操作符（`==`、`!=`、`<`、`>` 等）
- ❌ 不支持在循环中使用条件判断，例如 `{% if account.status == "success" %}`

推荐使用预过滤的便利变量（如 `has_success`、`has_failed`、`all_success` 等）来替代循环内的条件判断。

**模板示例**：
> 请注意，虽然本系统使用 json5 解析 json 字符串，但是为了避免消息平台方的问题，建议您在设置 `template` 字段时，**不要使用多行字符串**，而是将每个换行符替换为 `\\n`。

以企业微信支持的 markdown 语法为例：
```jinja2
{% if all_success %}**✅ 所有账号全部签到成功！**{% else %}{% if partial_success %}**⚠️ 部分账号签到成功**{% else %}**❌ 所有账号签到失败**{% endif %}{% endif %}

### 详细信息
- **执行时间**：{{ timestamp }}
- **成功比例**：{{ stats.success_count }}/{{ stats.total_count }}
- **失败比例**：{{ stats.failed_count }}/{{ stats.total_count }}

{% if has_success %}
### 成功账号
{% if all_balance_unchanged %}
所有账号余额无变化
{% else %}
| 账号 | 已用（$） | 剩余（$） |
| :----- | :---- | :---- |
{% for account in success_accounts %}
|{{ account.name }}|{{ account.used }}|{{ account.quota }}|
{% endfor %}
{% endif %}

{% if has_failed %}
### 失败账号
| 账号 | 错误原因 |
| :----- | :----- |
{% for account in failed_accounts %}
|{{ account.name }}|{{ account.error }}|
{% endfor %}
{% endif %}
```

下面展示一些不同平台的自定义样式配置：

> 小技巧：<br>
> 1. 在部分平台可以使用 `\\n<br>\\n` 实现连换两行，即两行中间增加一个空行。<br>
> 2. 对于 `\\n\\n` 无效的平台，可以尝试使用 `\\n<br>`

<details>
<summary>企业微信（markdown 2.0）</summary>

```jsonc
{
  "webhook":"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key",
  "platform_settings":{
    "message_type": "markdown_v2"
  },
  "template": {
    "title": "{% if all_success %}**✅ 所有账号全部签到成功！**{% else %}{% if partial_success %}**⚠️ 部分账号签到成功**{% else %}**❌ 所有账号签到失败**{% endif %}{% endif %}",
    "content": "\\n### 详细信息\\n- **执行时间**：{{ timestamp }}\\n- **成功比例**：{{ stats.success_count }}/{{ stats.total_count }}\\n- **失败比例**：{{ stats.failed_count }}/{{ stats.total_count }}{% if has_success %}\\n### 成功账号\\n{% if all_balance_unchanged %}所有账号余额无变化{% else %}| 账号 | 已用（$） | 剩余（$） |\\n| :----- | :---- | :---- |\\n{% for account in success_accounts %}|{{ account.name }}|{{ account.used }}|{{ account.quota }}|{% endfor %}\\n{% endif %}{% endif %}{% if has_failed %}\\n### 失败账号\\n| 账号 | 错误原因 |\\n| :----- | :----- |\\n{% for account in failed_accounts %}|{{ account.name }}|{{ account.error }}|\\n{% endfor %}{% endif %}"
  }
}
```

<img src="/assets/notif_example/wecom.png" alt="WECOM_NOTIF_CONFIG" width="400" style="max-width: 100%;" />

</details>

<details>
<summary>钉钉</summary>

```jsonc
{
  "webhook": "https://oapi.dingtalk.com/robot/send?access_token=your_token",
  "platform_settings": {
    "message_type": "markdown"
  },
  "template": "{% if all_success %}**✅ 所有账号全部签到成功！**{% else %}{% if partial_success %}**⚠️ 部分账号签到成功**{% else %}**❌ 所有账号签到失败**{% endif %}{% endif %}\\n<br>\\n### 详细信息\\n\\n- **执行时间**：{{ timestamp }}\\n\\n- **成功比例**：{{ stats.success_count }}/{{ stats.total_count }}\\n\\n- **失败比例**：{{ stats.failed_count }}/{{ stats.total_count }}\\n<br>\\n{% if has_success %}\\n\\n### 成功账号\\n\\n{% for account in success_accounts %}\\n\\n- {{ account.name }}\\n<br>已用：${{ account.used }} | 剩余：${{ account.quota }}{% endfor %}{% endif %}\\n<br>\\n{% if has_failed %}\\n\\n### 失败账号\\n\\n{% for account in failed_accounts %}\\n\\n- {{ account.name }}\\n<br>	错误：{{ account.error }}{% endfor %}{% endif %}"
}
```

<img src="/assets/notif_example/dingtalk.png" alt="DINGTALK_NOTIF_CONFIG" width="400" style="max-width: 100%;" />

</details>

<details>
<summary>飞书（卡片 json 2.0）</summary>

```jsonc
{
  "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/your_key",
  "platform_settings": {
    "message_type": "card_v2", 
    "color_theme": "" // 不设置以实现 “根据签到状态自动设置颜色”
  },
  "template": "{% if all_success %}**✅ 所有账号全部签到成功！**{% else %}{% if partial_success %}**⚠️ 部分账号签到成功**{% else %}**❌ 所有账号签到失败**{% endif %}{% endif %}\\n<br>\\n##### 详细信息\\n- **执行时间**：{{ timestamp }}\\n- **成功比例**：{{ stats.success_count }}/{{ stats.total_count }}\\n- **失败比例**：{{ stats.failed_count }}/{{ stats.total_count }}{% if has_success %}\\n\\n<br>\\n##### 成功账号\\n| 账号 | 已用（$） | 剩余（$） |\\n| :----- | :---- | :---- |\\n{% for account in success_accounts %}|{{ account.name }}|{{ account.used }}|{{ account.quota }}|\\n{% endfor %}{% endif %}{% if has_failed %}\\n<br>\\n##### 失败账号\\n| 账号 | 错误原因 |\\n| :----- | :----- |\\n{% for account in failed_accounts %}|{{ account.name }}|{{ account.error }}|\\n{% endfor %}{% endif %}"
}
```

<img src="/assets/notif_example/feishu.png" alt="FEISHU_NOTIF_CONFIG" width="400" style="max-width: 100%;" />

</details>

<details>
<summary>Gmail 邮箱</summary>

```jsonc
{
  "user": "your_email",
  "pass": "your_pass_word",
  "to": "your_email",
  "platform_settings": {
    "message_type": "" // 不设置以实现 “html 自动识别”
  },
  "template": "{% if all_success %}<h2>✅ 所有账号全部签到成功！</h2>{% else %}{% if partial_success %}<h2>⚠️ 部分账号签到成功</h2>{% else %}<h2>❌ 所有账号签到失败</h2>{% endif %}{% endif %}<h3>详细信息</h3><ul><li><strong>执行时间</strong>：{{ timestamp }}</li><li><strong>成功比例</strong>：{{ stats.success_count }}/{{ stats.total_count }}</li><li><strong>失败比例</strong>：{{ stats.failed_count }}/{{ stats.total_count }}</li></ul>{% if has_success %}<h3>成功账号</h3><table border=\"1\" cellpadding=\"5\" cellspacing=\"0\"><tr><th>账号</th><th>已用（$）</th><th>剩余（$）</th></tr>{% for account in success_accounts %}<tr><td>{{ account.name }}</td><td>{{ account.used }}</td><td>{{ account.quota }}</td></tr>{% endfor %}</table>{% endif %}{% if has_failed %}<h3>失败账号</h3><table border=\"1\" cellpadding=\"5\" cellspacing=\"0\"><tr><th>账号</th><th>错误原因</th></tr>{% for account in failed_accounts %}<tr><td>{{ account.name }}</td><td>{{ account.error }}</td></tr>{% endfor %}</table>{% endif %}"
}
```

<img src="/assets/notif_example/email.png" alt="EMAIL_NOTIF_CONFIG" width="400" style="max-width: 100%;" />

</details>

## 注意事项

- 部分账号签到失败的时候，Action 整体依然会展示成功，具体的错误将在日志与通知中体现
- 遇到 401 错误时请重新获取 cookies，理论 1 个月失效，详见 [anyrouter-check-in #6](https://github.com/millylee/anyrouter-check-in/issues/6)

## 贡献指南

欢迎提交 Issue 和 Pull Request！

<details>
<summary>点击查看项目架构说明</summary>

### 项目架构

```
src/
├── core/                   # 核心业务逻辑
│   ├── checkin_service.py  # 签到服务主逻辑
│   └── models/             # 数据模型
├── notif/                  # 通知系统
│   ├── notify.py           # 通知统一入口
│   ├── models/             # 通知配置模型
│   ├── senders/            # 各种通知发送器
│   └── configs/            # 默认模板配置
├── tools/                  # 工具模块
│   └── logger/             # 日志系统
└── main.py                 # 程序入口
```

### 开发环境设置

#### 环境准备

```bash
# 1. 安装 mise（如果尚未安装）
curl https://mise.run | sh

# 2. 克隆并进入项目目录
git clone <your_fork_url>
cd <project_name>

# 3. 安装 Python 和配置开发环境
mise install          # 安装 Python 3.11
mise run setup        # 安装依赖 + Playwright 浏览器
```

#### 测试说明

项目采用 pytest 作为测试框架。测试分为以下几类：

- **单元测试** (`tests/unit/`)：测试独立模块的功能
- **集成测试** (`tests/integration/`)：测试模块间的协作和端到端流程
- **测试夹具** (`tests/fixtures/`)：提供可复用的测试数据和 Mock 对象
- **测试工具** (`tests/tools/`)：数据构造器等辅助工具

**常用测试命令**：

```bash
# 运行所有测试
mise run test

# 运行测试并生成覆盖率报告
mise run test-cov                    # 终端输出
mise run test-cov --cov-report=html  # 生成 HTML 报告

# 运行特定类型的测试
mise exec -- python3 -m pytest tests/unit        # 仅运行单元测试
mise exec -- python3 -m pytest tests/integration # 仅运行集成测试

# 运行单个测试文件
mise exec -- python3 -m pytest tests/unit/test_notification.py -v
```

**真实集成测试**：

部分集成测试会实际调用通知平台接口（需要在 `.env.test` 文件中配置真实的通知平台信息）。默认情况下这些测试会被跳过，使用以下命令启用：

```bash
# 启用真实集成测试
ENABLE_REAL_TEST=true
mise run test
```

#### 代码规范

```bash
mise run fmt              # 代码格式化
mise run fmt --check      # 检查代码格式（不修改文件）
mise run lint             # 代码检查
mise run lint --fix       # 代码检查并自动修复
```

#### 添加新的通知平台

1. 在 `src/notif/senders/` 下创建新的发送器类
2. 在 `src/notif/models/` 下创建对应的配置模型
3. 在 `src/notif/notify.py` 中注册新的通知方式
4. 在 `tests/unit/test_send_functions.py` 中添加对应的测试用例

</details>

## 许可证

本项目采用 BSD 2-Clause 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- [anyrouter-check-in](https://github.com/millylee/anyrouter-check-in) - 原始项目和灵感来源
- [Playwright](https://playwright.dev/) - 强大的浏览器自动化工具
- [Stencil](https://stencil.pyllyukko.com/) - 简洁的模板引擎
- 所有贡献者和用户的支持

---

**⭐ 如果这个项目对您有帮助，请帮忙点个 Star！**
