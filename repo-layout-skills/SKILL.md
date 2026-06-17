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

## Metadata配置示例

### 文件夹Metadata配置

在目录中创建 AGENTS.md 文件并添加 frontmatter，可以为该文件夹添加元数据信息：

```markdown
---
repo-layout:
  meta:
    description: Repo Root
    purpose: Project root directory
  entry_point: main.py
  name_patterns:
    files:
      include: ['*.py', '*.json', '*.yaml']
      exclude: ['*_test.py', '*.tmp']
    folders:
      include: ['src', 'test', 'docs']
      exclude: ['__pycache__', '*.bak']
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

### 文件Metadata配置

为文件创建对应的metadata文件，文件名格式为`{原文件名}.{扩展名}.md`：

```markdown
---
description: This file contains important configuration
---
```

例如，为`config.json`创建metadata文件`config.json.md`。

## when 条件过滤

可以使用 `when` 字段来根据 tags 过滤文件显示：

```yaml
---
repo-layout:
  meta:
    description: Repo Root
  when:
    - tag: [standard]
      show_files: false
---
```

当提供的 tags 包含 `standard` 时，该文件夹的文件明细将被隐藏，只显示 `repo-layout.meta` 的内容。

## 设计参考

### 两级Metadata系统

file-tree目前分为两个级别的metadata：

1. **文件夹级别metadata**：配置在AGENTS.md的frontmatter中
2. **文件级别metadata**：配置在{file}.{ext}.md文件中

### 一对一Metadata机制

#### 文件夹Metadata（AGENTS.md）

在目录中创建AGENTS.md文件并添加frontmatter：

```markdown
---
repo-layout:
  meta:
    description: Repo Root
    purpose: Project root directory
  entry_point: main.py
  name_patterns:
    files:
      include: ['*.py', '*.json', '*.yaml']
      exclude: ['*_test.py', '*.tmp']
    folders:
      include: ['src', 'test', 'docs']
      exclude: ['__pycache__', '*.bak']
  files:
    file1.txt: Description from AGENTS.md files field
  when:
    - tag: [standard]
      show_files: false
---
```

**字段说明：**
- `repo-layout`：文件夹的配置根节点
  - `meta`：文件夹的元数据，会作为`:meta`键添加到目录节点
    - `description`：文件夹描述
    - `purpose`：文件夹目的
    - `show_files`：是否显示该文件夹的文件明细（默认为 true）
  - `entry_point`：该模块的入口文件
  - `name_patterns`：允许使用的文件名格式
    - `files`：文件名模式配置
      - `include`：允许的文件名glob模式列表（白名单）
      - `exclude`：排除的文件名glob模式列表（黑名单）
    - `folders`：文件夹名模式配置
      - `include`：允许的文件夹名glob模式列表（白名单）
      - `exclude`：排除的文件夹名glob模式列表（黑名单）
  - `files`：为同级文件提供描述（一对一机制的补充）
  - `when`：条件过滤，根据tags控制文件显示
    - `tag`：匹配的tags列表
    - `show_files`：是否显示该文件夹的文件明细（会覆盖 meta.show_files）

#### 文件Metadata（{file}.{ext}.md）

为每个文件创建对应的metadata文件：

```markdown
---
description: Description from .md file
---
```

文件名格式：`{原文件名}.{扩展名}.md`，例如`file2.txt.md`

### 一对多Metadata机制（repo-layout frontmatter）

在任何.md文件中添加`repo-layout` frontmatter，可以覆盖同级多个文件和文件夹的metadata：

```markdown
---
repo-layout:
  files: ['exact_file.txt']           # 精确匹配文件名
  include: ['pattern_*.txt']          # glob模式白名单
  exclude: ['*_excluded.txt']         # glob模式黑名单
  show_files: false                   # 是否显示被覆盖文件的详细信息
  meta:
    :custom_key: custom_value         # 自定义元数据输出
---
```

**匹配模式：**
1. **精确匹配**：使用`files`字段指定文件名列表
2. **include-only**：只使用`include`字段进行glob模式匹配
3. **include+exclude**：使用`include`白名单和`exclude`黑名单组合

**字段说明：**
- `files`：精确匹配的文件名列表
- `include`：glob模式白名单
- `exclude`：glob模式黑名单（必须与include配合使用）
- `show_files`：控制是否显示被覆盖文件的详细信息
- `meta`：自定义元数据，会直接输出到文件树中

**冲突处理：**
- 如果多个repo-layout md文件覆盖同一个文件，会报错并忽略覆盖
- 如果多个repo-layout md文件的meta字段有冲突键，会报错并保留第一个值
