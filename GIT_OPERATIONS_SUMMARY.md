# Git 操作总结

## 📊 当前状态

### 分支情况
- **main**: 已合并 main-new 的内容，领先 origin/main 4 个提交
- **main-new**: 包含 fxf 的更改，已撤销错误的合并
- **fxf**: 本地已重置到合并之前（19d263f），但远程还有错误的合并

### 已完成的操作
1. ✅ 将 main-new 合并到 main
2. ✅ 解决合并冲突（factory.py 和 minimax_client.py）
3. ✅ 本地 fxf 分支已重置到合并之前

### 待完成的操作
1. ⏳ 推送 main 到远程
2. ⏳ 处理远程 fxf 分支（撤销错误的合并）

---

## 🚀 执行步骤

### 步骤1: 推送 main 到远程

```bash
git push origin main
```

### 步骤2: 处理远程 fxf 分支

**选项A: 强制推送（会覆盖远程分支）**
```bash
git checkout fxf
git push origin fxf --force
```

**选项B: 创建 revert 提交（保留历史）**
```bash
git checkout fxf
git revert e7df390
git push origin fxf
```

---

## ⚠️ 注意事项

1. **强制推送风险**: 如果其他人也在使用 fxf 分支，强制推送会影响他们
2. **备份**: 在强制推送前，建议先备份远程分支
3. **确认**: 确保这是你想要的操作

---

## 📝 操作记录

### 合并 main-new 到 main
- 提交: `d2c4b62 Merge main-new (fxf) into main`
- 冲突文件: `factory.py`, `minimax_client.py`
- 解决方案: 使用 main-new 的版本（包含 minimax 支持）

### 重置 fxf 分支
- 重置到: `19d263f deploy`
- 撤销的提交: `e7df390 Merge branch 'main' into fxf`

