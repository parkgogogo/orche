[English](README.md) · [Install Guide](https://github.com/parkgogogo/tmux-orche/raw/main/install.md)

# tmux-orche

一个面向 delegation、review 和 takeover 的持久化 tmux agent session 工具。

`tmux-orche` 解决的是这样一个空档：

- 一次性跑 agent 太短，状态留不住
- 纯手工盯 tmux pane 又太重，流程容易散

它让你可以：

- 用稳定名字打开一个 agent session，并持续复用
- 把任务发出去后立刻返回
- 稍后再检查，不丢失现场终端状态
- 显式把通知路由到另一个 session 或 Discord
- 在任何时刻直接接管 live TTY

如果你已经在 tmux 里用 Codex 或 Claude Code，`orche` 的价值不是“再包一层命令”，而是把这套工作流变成可复用、可检查、可接管的 session 模型。

## 为什么值得用

大多数 agent 工作流的问题都很像：

- 一个命令跑完后 session 就没了
- 终端现场丢失，后续只能重开
- follow-up prompt 只能重新开始
- 多 agent 协作最后退化成零散的 tmux 脚本
- 通知来源不清晰，边界不明确

`orche` 的做法是把 session 变成一等资源。

你不再操作“某个 pane”，而是操作一个命名清晰的 session，它自带：

- 工作目录
- agent 类型
- 持久化 tmux pane
- 可选的显式 notify 路由
- 后续检查和接管能力

## 它和普通 tmux 工作流的区别

### 以 session 为中心，不是以 pane 为中心

你操作的是 `repo-worker`、`repo-reviewer`、`auth-fixer`，不是 `%17`。

### 以 handoff 为中心，不是以 babysit 为中心

默认流程就是：

1. `open`
2. `prompt`
3. 离开
4. 之后再 `status` / `read`

### notify 是显式的，没有默认路由

只有你明确配置时才会发通知：

- `tmux:<session>`
- `discord:<channel-id>`

不会再因为某个全局默认配置就自动发。

### 同时适合后台 delegation 和中途接管

平时用 `read` / `status` 跟进。
需要时用 `attach` 直接进入 live terminal。

## 核心工作流

```bash
# 先打开一个 worker session
orche open \
  --cwd /path/to/repo \
  --agent codex \
  --name repo-worker \
  --notify tmux:repo-reviewer

# 再把任务发进去
orche prompt repo-worker "analyze the failing tests and propose a fix"

# 稍后回来检查
orche status repo-worker
orche read repo-worker --lines 120

# 需要时直接接管
orche attach repo-worker

# 最后关闭
orche close repo-worker
```

这就是它的标准模型：持久化 session、显式 handoff、稍后检查。

## 适合什么场景

`tmux-orche` 特别适合这些情况：

- 一个 reviewer session 协调多个 worker
- 一个实现任务或调研任务要跑很久
- 同一个 agent 需要接收多轮 follow-up
- 终端型 agent 可能会中途卡在交互输入
- 需要在 session 间通过 tmux 回消息
- 自动化不够时，你还想随时接管现场终端

如果你只是想执行一次短命令、执行完就结束，那它就不一定有优势。

## 快速开始

打开一个带显式 notify 的托管 session：

```bash
orche open \
  --cwd /path/to/repo \
  --agent codex \
  --name repo-worker \
  --notify tmux:repo-reviewer
```

发送任务：

```bash
orche prompt repo-worker "implement the parser refactor"
```

稍后检查：

```bash
orche status repo-worker
orche read repo-worker --lines 120
orche list
```

处理交互输入：

```bash
orche input repo-worker "yes"
orche key repo-worker Enter
```

直接接管：

```bash
orche attach repo-worker
```

## Managed 和 Native 的区别

### Managed session

普通 delegation 用 managed 模式：

```bash
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

这是默认推荐方式。

### Native session

如果你需要把原生 agent CLI 参数透传进去，用 native 模式：

```bash
orche open --cwd /repo --agent claude -- --print --help
```

规则：

- 原生 agent 参数必须放在 `--` 后面
- native session 不使用 `--notify`
- 不要把 raw agent args 和 managed notify 混用

## 命令模型

- `orche open`
  创建或复用一个命名 session。
- `orche prompt`
  往现有 session 发送 prompt。
- `orche status`
  看 pane 和 agent 是否活着，以及是否还有 pending turn。
- `orche read`
  读取最近的终端输出。
- `orche attach`
  把当前终端接到 live tmux session。
- `orche input`
  输入文本但不按 Enter。
- `orche key`
  发送特殊按键，比如 `Enter`、`Escape`、`C-c`。
- `orche list`
  列出本地已知 session。
- `orche cancel`
  中断当前 turn，但保留 session。
- `orche close`
  结束 session 并清理状态。
- `orche whoami`
  输出当前 session id。
- `orche config`
  读取或修改共享运行时配置。

## 多 Agent Review 模式

```bash
# reviewer
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678

# worker 回消息给 reviewer
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer

# 发送实现任务
orche prompt repo-worker "implement the parser refactor"

# 之后查看 reviewer
orche read repo-reviewer --lines 120
```

这套模式的价值在于：不用自己拼零散 tmux 脚本，也能得到稳定的 reviewer/worker 协作回路。

## Notify

Notify 是显式的。

`orche open --notify` 接受：

- `tmux:<target-session>`
- `discord:<channel-id>`

例如：

```bash
orche open --cwd /repo --agent codex --name repo-reviewer --notify discord:123456789012345678
orche open --cwd /repo --agent codex --name repo-worker --notify tmux:repo-reviewer
```

说明：

- `tmux:<session>` 用于 agent-to-agent 路由
- `discord:<channel-id>` 只在你明确需要 Discord 投递时使用
- 如果要换 notify 目标，直接开一个新 session

## 安装

完整安装说明：<https://github.com/parkgogogo/tmux-orche/raw/main/install.md>

从 PyPI 安装：

```bash
pip install tmux-orche
```

使用 `uv` 安装：

```bash
uv tool install tmux-orche
```

从源码安装：

```bash
git clone https://github.com/parkgogogo/orche
cd orche
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install .
```

## 配置

```bash
orche config list
orche config set discord.bot-token "$BOT_TOKEN"
orche config set discord.mention-user-id 123456789012345678
orche config set notify.enabled true
```

配置文件：

```text
~/.config/orche/config.json
```

状态目录：

```text
~/.local/share/orche/
```

## 前置条件

- `tmux`
- `codex` CLI 和/或 `claude` CLI
- Python `3.9+`

## License

[MIT](LICENSE)
