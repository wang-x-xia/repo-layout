---
name: repo_layout_skills
description: This skill is used to manage the layout of all files within a repo, allowing AI and humans to quickly understand the project structure.
---
# Repo Layout Skill

这个skill用来管理repo内部所有文件的layout，让AI和人类能够快速了解项目的结构。

## 功能

- 生成项目的文件树结构（YAML格式）
- 分析项目布局和组织结构
- 提供项目结构的可视化表示
- 支持两级metadata系统：文件夹级别和文件级别
- 支持一对一metadata机制：每个文件/文件夹对应一个metadata文件
- 支持一对多metadata机制：通过repo-layout frontmatter覆盖同级多个文件/文件夹

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

# 使用 tags 显示不同类别的信息，默认是[standard]，支持多个
uv run scripts/file_tree.py --tags tag1 tag2
```

## Metadata配置

### 两级Metadata系统

file-tree目前分为两个级别的metadata：

1. **文件夹级别metadata**：配置在AGENTS.md的frontmatter中
2. **文件级别metadata**：配置在{file}.{ext}.md文件中

### 文件夹Metadata配置

在目录中创建 AGENTS.md 文件并添加 frontmatter，可以为该文件夹添加元数据信息：

```yaml
# 使用repo-layout作为key
# 如未特殊说明，字段默认都是可选的
repo-layout:
  # 用来描述文件夹的元数据，会添加到文件树的:meta节点中
  meta:
    description: Repo Root
    purpose: Project root directory
  # 用来描述文件夹的入口文件
  entry_point: main.py
  # 用来描述文件夹中文件和文件夹的命名模式
  name_patterns:
    files:
      include: ['*.py', '*.json', '*.yaml']
      exclude: ['*_test.py', '*.tmp']
    folders:
      include: ['src', 'test', 'docs']
      exclude: ['__pycache__', '*.bak']
  # 用来为文件添加描述信息，是一个简单的修改文件description的机制
  files:
    main.py: Main entry point
```

生成的文件树会包含：

```yaml
:meta:
  description: Repo Root
  purpose: Project root directory
AGENTS.md: null
其他文件...
```

### 文件Metadata配置

为文件创建对应的metadata文件，文件名格式为`{原文件名}.{扩展名}.md`，并添加frontmatter：

```yaml
# 不需要repo-layout字段
# 用来描述文件的元数据，会添加到文件树的va
description: This file contains important configuration
```

例如，为`config.json`创建metadata文件`config.json.md`。

生成的文件树会包含：

```yaml
config.json: This file contains important configuration
```

### Hint Markdown

为了简化metadata配置，避免为每个文件都创建一个metadata文件，提供了hint markdown机制。

在任何.md文件中添加`repo-layout` frontmatter，可以覆盖同级多个文件和文件夹的metadata：

```yaml
# 使用repo-layout作为key
# 如未特殊说明，字段默认都是可选的
repo-layout:
  # 精确匹配文件名，和include/exclude互斥
  files: ['exact_file.txt']
  # 白名单，支持glob模式，不配置files时必须配置
  include: ['pattern_*.txt']
  # 黑名单，支持glob模式
  exclude: ['*_excluded.txt']
  # 是否显示被覆盖文件的详细信息
  show_files: 
  # 自定义元数据，用来展示在文件树的文件夹中，但是没有 :meta 前缀
  # 和其他meta不同，这个meta是字典类型，不是任意类型，值可以是任意类型。
  meta:
    :custom_key: custom_value
    # 推荐在meta内部添加如下字段用于识别Hint Markdown文件本身
    # 因为hint markdown自己不会出现在文件树中。
    # 当然为了灵活度，也可以不添加
    hint.md: 就是这个文件自己啦
```

### when条件定制Metadata

可以使用 `when` 字段来根据 tags 定制Metadata：

```yaml
repo-layout:
  meta: A long description
  when:
    - tag: [standard]
      meta: A short description
```

当提供的 tags 包含 `standard` 时，该文件夹的元数据会使用 `A short description`。

tags通过命令行参数传递给repo-layout，例如：


```bash
# 默认 tags = [standard]
uv run scripts/file_tree.py
# 清空 tags = []
uv run scripts/file_tree.py --tags
# 自定义和多个tags，例如["standard", "custom"]
uv run scripts/file_tree.py --tags standard custom
```