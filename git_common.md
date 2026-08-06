# Git 常用命令

## 分支操作

### 切换回 main 分支

```bash
git checkout main
# 或等价的
git switch main
```

**原理**: `checkout` / `switch` 会将 `HEAD` 指针指向 `main` 分支，并将工作目录的文件替换为 `main` 分支最新提交的快照。未提交的修改会被带到目标分支（有冲突时会阻止切换）。

### 查看所有分支

```bash
git branch          # 本地分支，当前分支前有 *
git branch -r       # 远程分支
git branch -a       # 所有分支（本地 + 远程）
```

### 创建分支

```bash
git branch <branch-name>              # 基于当前位置创建，但不切换
git checkout -b <branch-name>         # 创建并切换
git switch -c <branch-name>           # 创建并切换（新版推荐写法）
```

### 删除分支

```bash
git branch -d <branch-name>           # 安全删除（已合并的分支）
git branch -D <branch-name>           # 强制删除（无论是否合并）
git push origin --delete <branch-name> # 删除远程分支
```

### 推送分支到远程

```bash
git push -u origin <branch-name>      # 首次推送并设置上游跟踪
git push                              # 之后可直接 push（已跟踪）
```

---

## 暂存与提交

### 查看状态与差异

```bash
git status                # 文件变更概览
git diff                  # 工作区 vs 暂存区的差异
git diff --staged         # 暂存区 vs 最近一次提交的差异
git log --oneline -10     # 最近 10 条提交简表
```

### 暂存与提交

```bash
git add <file>            # 暂存指定文件
git add -p <file>         # 交互式选择暂存哪些块
git commit -m "message"   # 提交
```

### 撤销

| 场景 | 命令 |
|------|------|
| 撤销工作区修改（未 add） | `git checkout -- <file>` 或 `git restore <file>` |
| 取消暂存（已 add 未 commit） | `git reset HEAD <file>` 或 `git restore --staged <file>` |
| 撤销最近一次提交（保留修改） | `git reset --soft HEAD~1` |
| 撤销最近一次提交（丢弃修改） | `git reset --hard HEAD~1` |

---

## 同步与合并

### 拉取远程更新

```bash
git pull                 # fetch + merge（默认）
git pull --rebase        # fetch + rebase（保持历史线性）
git fetch origin         # 只下载，不合入当前分支
```

### 合并分支

```bash
git merge <branch>       # 将目标分支合并到当前分支
git rebase <branch>      # 将当前分支的提交移到目标分支顶端
```

`merge` vs `rebase` 的区别：

- **merge**: 创建一个新的合并提交，保留两条分支的完整历史。适合公共分支（如 main）。
- **rebase**: 将当前分支的提交"搬"到目标分支顶端，历史是一条直线，更干净。适合本地功能分支。

```
merge:                     rebase:
A---B---M (merge commit)   main: A---B
 \     /                    feat:        C'---D'
  C---D
```

### 解决冲突

冲突发生时，Git 会在文件中标记冲突区域：

```
<<<<<<< HEAD
当前分支的内容
=======
要合并的内容
>>>>>>> <branch>
```

手动编辑后执行：

```bash
git add <resolved-file>
git commit          # merge 冲突
# 或
git rebase --continue  # rebase 冲突
```

放弃合并/变基：

```bash
git merge --abort
git rebase --abort
```

---

## 储藏（Stash）

```bash
git stash               # 暂存当前工作区修改
git stash list          # 列出所有 stash
git stash pop           # 恢复最近一次 stash 并删除记录
git stash apply         # 恢复但不删除
git stash drop          # 删除最近一次 stash
```

**场景**: 正在分支 A 开发，突然需要切到分支 B 处理紧急问题，但又不想提交半成品。先 `stash`，切分支，回来再 `pop`。

---

## 实际案例

### 回到本次任务

当前在 `feature/session-storage-mount-path`，想切回 `main`：

```bash
git checkout main
```

如果之后想回到这个功能分支：

```bash
git checkout feature/session-storage-mount-path
```
