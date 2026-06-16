# Repo Layout Skill

这个skill用来管理repo内部所有文件的layout，让AI和人类能够快速了解项目的结构。

## 功能

- 生成项目的文件树结构（YAML格式）
- 分析项目布局和组织结构
- 提供项目结构的可视化表示
- 支持 AGENTS.md frontmatter 解析：如果目录包含 AGENTS.md 文件，会解析其 frontmatter 中的 folder_meta 字段
- 元数据展示：folder_meta 内容会作为 :meta 键添加到对应的目录节点中，并排在最前面

## 使用方式

当需要了解或分析项目的文件结构时使用此skill。

### file_tree.py 工具

生成项目的文件树结构：

```bash
# 扫描当前目录
uv run scripts/file_tree.py

# 扫描指定目录
uv run scripts/file_tree.py /path/to/directory

# 禁用 .gitignore 过滤
uv run scripts/file_tree.py /path/to/directory --no-gitignore
```

## 给文件夹添加元数据

在目录中创建 AGENTS.md 文件并添加 frontmatter，可以为该文件夹添加元数据信息：

```markdown
---
folder_meta:
    description: Repo Root
    purpose: Project root directory
---

这里写目录的说明...
```

生成的文件树会包含：

```yaml
:meta:
  description: Repo Root
  purpose: Project root directory
AGENTS.md: null
其他文件...
```
