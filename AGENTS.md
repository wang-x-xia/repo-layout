---
folder_meta:
    description: Repo Root
---

## 项目目标

这个项目的目标是提供一个简单的工具，用来帮助AI工具和人理解和管理repo内部所有文件的layout。

## 实现细节

- 使用Python脚本实现
- 脚本使用 PEP 723 格式定义内联依赖（在脚本开头使用 `# /// script` 块）
- 不使用项目级包管理，依赖在脚本内部定义
- 使用 `uv run` 运行脚本
- 脚本配置 UTF-8 输出编码以支持中文等多语言字符（Windows兼容）
