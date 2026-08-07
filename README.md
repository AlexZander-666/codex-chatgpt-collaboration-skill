# Codex × ChatGPT Collaboration Skill

一个让 Codex 在每个任务开始前自动与 ChatGPT 网页最高可用模型协作、同时保持本地证据闭环的可安装 Skill。

它把原项目 [manwithshit/codex-chatgpt-collaboration-prompt](https://github.com/manwithshit/codex-chatgpt-collaboration-prompt) 的一次性 Prompt 改造成渐进披露的 Codex Skill：

- 通过隐式调用元数据把自身声明为每个任务的前置编排器；
- 自动复用或打开一个 ChatGPT 标签页，并选择页面中可见、可选的 Pro，或 UI 明确标记的最强推理档；
- 先做真实连接门禁，不能读取完整回复就 fail closed；
- 用规范传输文本重建 ProseMirror 的语义明文，兼容编辑器自动生成的段落、标题和扁平列表节点，不再把 `innerText`/`textContent` 的 DOM 表示差异误判为正文变化；
- 每个 Codex 用户任务创建新的任务纪元；只在同一任务内恢复写前可证明的草稿，新任务会在 Skill 专用标签页中一次性清理稳定残留而不会继承；
- 为新任务信封加入自校验草稿指纹，同时兼容一次性识别和清理旧版结构化 Codex 信封；
- 区分发送前污染与发送后幻影草稿，后者不会追溯性推翻已经确认的消息或阻断回复读取；
- 验证编辑器已真正接受输入，不把“文字可见”误判为“可以发送”；
- 对超时和中断使用 `SEND_UNKNOWN` 恢复流程，先确认消息是否已发送，禁止盲目重试造成重复提问；
- 使用“响应存在、生成结束、内容稳定、回复操作可用”等结构化证据判断完成，不依赖单一状态文案；
- 任意残留文本只允许在可证明由 Skill 创建并专用的标签页中清理；共享或归属不明标签页继续保护普通草稿，并只在用户消息角色中计算精确任务标记；
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
│   ├── composer-contract.md
│   ├── security-boundary.md
│   ├── task-envelope.md
│   └── workflow.md
└── scripts/
    ├── audit_context.py
    └── composer_contract.py
```

`audit_context.py` 是只读的轻量 fail-closed 检查器，用于发现常见密钥模式、禁止文件类型和越界路径。它不能替代仓库可信的 secret scanner，也不能证明文件适合外发。

## 设计边界

- 需要当前 Codex 环境具备浏览器控制能力，并由用户亲自完成登录和身份验证。
- Skill 已设置 `policy.allow_implicit_invocation: true` 并在触发描述中覆盖所有任务；是否能做到宿主级 100% 强制调用，最终仍取决于 Codex 的 Skill 调度器或全局策略。
- 除登录、验证码、Passkey、CAPTCHA 和二次验证外，页面打开、模型选择、提问和回复读取均由 Codex 自动完成。
- Skill 只报告页面可观察的选择证据，不声称某个模型在全局上能力最高。
- 新对话中的模型控件和发送状态可能异步出现；Skill 会在当前对话内做有界等待和复查，不继承上一对话的模型证据。
- “新聊天”只隔离对话上下文，不视为草稿存储重置；同一任务内只有当前任务纪元的完整溯源草稿才能恢复为 `SAME_TASK_SKILL_DRAFT`。
- 新 Codex 用户任务绝不继承旧草稿；在记录为 `SKILL_RESERVED_TAB` 的专用标签页中，稳定残留文本可在零附件、零用户消息和即时归属复核后执行唯一一次 `MANAGED_TASK_DRAFT_RESET`；共享或归属不明标签页只有完整匹配固定连接消息、带有效指纹的新信封或严格旧版信封时才允许 `STALE_CODEX_DRAFT_RESET`，普通文本和任何附件仍保持阻断保护。
- 多行正文先将换行规范为 LF，再按编辑器块语义重建并逐代码点、长度和 UTF-8 SHA-256 比较；原始 `innerText` 与 `textContent` 长度仅作诊断。
- 每个连接消息和任务信封都必须在对话中精确出现一次；发送动作超时不等于发送失败。
- 每个异步等待都必须选择并记录有限的截止时间或复查次数；用两次连续一致的内容读取证明回复稳定。
- 默认只发送最小文字上下文；上传文件需要单独、明确授权。
- ChatGPT 输出不是证据；只有源码、权威资料和真实验证结果能支持 `VERIFIED`。
- 本项目不是 OpenAI 官方项目，不承诺固定 Token、速度或模型性能收益。

## 验证

```powershell
python -B -m unittest discover -s tests -v
```

回归测试会检查引用文件、前置元数据、隐式调用策略、单次发送恢复状态、结构化完成判据和最终报告证据字段。发布前还应使用当前 Codex 环境中 `skill-creator/scripts/quick_validate.py` 验证 Skill 目录。2026-08-07 的真实 ChatGPT Pro 场景验证结果记录在 [PRACTICAL_VALIDATION.md](PRACTICAL_VALIDATION.md)。

## 来源与许可

本项目基于上游 commit `21c1b57` 的 MIT 许可内容进行结构化改编。详见 [NOTICE](./NOTICE) 与 [LICENSE](./LICENSE)。
