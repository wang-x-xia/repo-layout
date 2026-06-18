---
repo-layout:
  meta: This prject is an Agent Skill that helps understand and manage the layout of files within a folder.
---

## 项目目标

这个项目的目标是提供一个Agent Skill，用来帮助AI工具和人理解和管理文件夹内的layout。

## 项目结构

```yaml
# :repo-layout: uv run repo-layout-skills\scripts\file_tree.py  
:meta:
  description: Repo Root
AGENTS.md: AI Agents的README
repo-layout-skills/:
  SKILL.md: Agent Skill描述文件
  reference/known_files.zh-CN.yaml:
  scripts/:
    file_tree.py:
    repo_layout_lib/:
      __init__.py: Python包初始化文件
      error.py:
      git.py:
      impl.py:
      known_files.py:
      models.py:
      when.py:
      yaml_utils.py:
test(+AI)/:
  '{case}/':
    :meta: Each folder is a test group with multiple test cases, "core-success" for
      success cases, "core-error" for error cases
    case.yaml: Test cases configuration
    data: Data files, created manually
    result: Generated test results, only need to be updated manually if big changes
      occur
```

## 编码规范

- 使用Python脚本实现
- 脚本使用 PEP 723 格式定义内联依赖（在脚本开头使用 `# /// script` 块）
- 不使用项目级包管理，依赖在脚本内部定义
- 使用 `uv run` 运行脚本
- 脚本配置 UTF-8 输出编码以支持中文等多语言字符（Windows兼容）

## 测试

运行全部测试：`uv run test/test_case.py verify-all`
详情参考 `test/AGENTS.md`
