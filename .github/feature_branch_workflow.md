# Feature 分支开发流程

本文档用于约定从 `dev2` 开始新功能开发、同步上游代码和提交 PR 的标准流程。

## 1. 分支关系

- `upstream/dev2` 是目标仓库的主开发分支，也是 PR 最终合入的基线。
- 本地 `dev2` 应跟踪 `upstream/dev2`，只用于同步上游代码，不直接开发。
- 功能分支从本地 `dev2` 切出，开发完成后推送到自己的 fork，也就是 `origin/<feature-branch>`。

如需设置本地 `dev2` 的跟踪分支：

```bash
git fetch upstream
git switch dev2
git branch --set-upstream-to=upstream/dev2 dev2
git pull --ff-only
```

## 2. 新开 feature 分支

开始新任务前，先同步 `upstream/dev2`：

```bash
git fetch upstream
git switch dev2
git pull --ff-only
```

再从最新的本地 `dev2` 切出功能分支：

```bash
git switch -c feature/<short-name>
```

分支命名建议：

```text
feature/<task-name>
fix/<issue-or-module>
docs/<topic>
test/<module>
```

## 3. 开发与提交

- 一次 commit 只做一类事情，提交信息遵循 `.github/commit_conventions.md`。
- 修改逻辑代码时，需要补充或更新相关测试。
- 不要在功能分支中混入与本任务无关的格式化、重构或文档调整。

## 4. 提交 PR 前同步主线

提交 PR 前，必须先基于最新 `upstream/dev2` 完成 rebase：

```bash
git fetch upstream
git switch <feature-branch>
git rebase upstream/dev2
```

如果 rebase 过程中出现冲突，AI 必须暂停当前 rebase 流程，并将冲突文件、冲突原因和当前状态反馈给人工处理。冲突必须由人工解决并确认后，AI 才能继续执行后续命令。

人工完成冲突解决并明确确认后，再继续：

```bash
git add <resolved-files>
git rebase --continue
```

rebase 完成后，运行必要测试，再推送到自己的 fork：

```bash
git push -u origin <feature-branch>
```

如果该分支之前已经推送过，rebase 后需要使用：

```bash
git push --force-with-lease origin <feature-branch>
```

## 5. PR 提交要求

创建 PR 时：

- base 分支选择 `ydhh-test/tire-ai-pattern:dev2`。
- compare 分支选择自己的 fork 中对应的 feature 分支。
- PR 描述必须按 `.github/pull_request_template.md` 填写完整。
- PR 中需要写明提交目标、提交类型、测试结果、改动范围和未修改内容。
- 涉及逻辑代码时，必须提供 pytest 和相关 coverage 结果；不适用时写明原因。
- 若 PR 由 AI 生成或协助提交，需要在补充说明中明确说明。
