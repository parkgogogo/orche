# 测试场景

## 测试场景一：

多次 orche codex，每一个 sessions 都能正常工作，且这样创建的 sessions 和 sessions-new 创建的等价，区别在于这样创建的是有交互式会话的（tmux），以及没有 notify ~

## 测试场景二

使用 orche 起一个 codex session「A」，让这个 session 中的 codex 通过阅读我们的 SKILL.md 来正确创建 codex session「B」，让「A」跟「B」说一句 “您好 codex，如果收到消息，请回复 hello“，我们作为观察者，观察到 A B 之间的正常通信 ～

- 检查使用能成功创建 sessions

- 检查 SKILL.md 是否能正确指引 codex 来规范化使用 orche

- 检查 `notify` 功能是否正常

