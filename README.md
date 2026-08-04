# Codex × ChatGPT Collaboration Skill

一个让 Codex 在每个任务开始前自动与 ChatGPT 网页最高可用模型协作、同时保持本地证据闭环的可安装 Skill。

它把原项目 [manwithshit/codex-chatgpt-collaboration-prompt](https://github.com/manwithshit/codex-chatgpt-collaboration-prompt) 的一次性 Prompt 改造成渐进披露的 Codex Skill：

- 通过隐式调用元数据把自身声明为每个任务的前置编排器；
- 自动复用或打开一个 ChatGPT 标签页，并选择页面中可见、可选的 Pro，或 UI 明确标记的最强推理档；
- 先做真实连接门禁，不能读取完整回复就 fail closed；
- ChatGPT 负责外部调研、方案比较和复杂推理；
- Codex 负责本地检查、实现、权限控制和独立验收；
- 建议、修改、验证、提交和发布是彼此独立的状态，不得混称。

## 安装

使用 Codex 的 Skill 安装能力，从本仓库安装路径：

```text
skills/codex-chatgpt-collaboration
```

也可以把该目录复制到本机 Codex skills 目录。安装后可这样调用：

```text
Use $codex-chatgpt-collaboration to ask ChatGPT Pro to compare these two designs, then verify the recommendation against this repository.
```

## 严格前置调用

`allow_implicit_invocation: true` 会最大化自动触发，但 Skill 本身不能强制宿主调度器。若希望每个任务都明确执行，可在全局 `AGENTS.md` 加入：

```markdown
Before substantive action on every user task, invoke the installed
`codex-chatgpt-collaboration` skill, including for routine tasks. Let the skill
automatically open or reuse ChatGPT, select the visible Pro option or another
UI-labeled strongest reasoning tier, submit the task, and retrieve the complete
response before Codex executes and verifies locally.
```

这条宿主规则与 Skill 的隐式调用元数据共同工作。登录、CAPTCHA、Passkey 和多因素认证仍必须由用户本人完成。

## 结构

```text
skills/codex-chatgpt-collaboration/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── report-template.md
│   ├── security-boundary.md
│   ├── task-envelope.md
│   └── workflow.md
└── scripts/audit_context.py
```

`audit_context.py` 是只读的轻量 fail-closed 检查器，用于发现常见密钥模式、禁止文件类型和越界路径。它不能替代仓库可信的 secret scanner，也不能证明文件适合外发。

## 设计边界

- 需要当前 Codex 环境具备浏览器控制能力，并由用户亲自完成登录和身份验证。
- Skill 已设置 `policy.allow_implicit_invocation: true` 并在触发描述中覆盖所有任务；是否能做到宿主级 100% 强制调用，最终仍取决于 Codex 的 Skill 调度器或全局策略。
- 除登录、验证码、Passkey、CAPTCHA 和二次验证外，页面打开、模型选择、提问和回复读取均由 Codex 自动完成。
- Skill 只报告页面可观察的选择证据，不声称某个模型在全局上能力最高。
- 默认只发送最小文字上下文；上传文件需要单独、明确授权。
- ChatGPT 输出不是证据；只有源码、权威资料和真实验证结果能支持 `VERIFIED`。
- 本项目不是 OpenAI 官方项目，不承诺固定 Token、速度或模型性能收益。

## 来源与许可

本项目基于上游 commit `21c1b57` 的 MIT 许可内容进行结构化改编。详见 [NOTICE](./NOTICE) 与 [LICENSE](./LICENSE)。
