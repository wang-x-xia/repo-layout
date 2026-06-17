---
repo-layout:
  meta:
    "{case}/": 
      :meta: Each folder is a set of test cases, "core-success" for success cases, "core-error" for error cases
      data: Data files, created manually
      result: Generated test results, only need to be updated manually if big changes occur
      case.yaml: Test case configuration
  when:
    - tag: [standard]
      show_files: false
---

## 测试脚本

测试脚本位于 `test/test_case.py`，用于验证脚本功能。

## 测试原则

- **优先复用现有测试用例**：在现有的测试用例中添加新的测试场景，而不是创建新的测试目录
- **按功能分类**：测试用例按功能分类（如正常场景、错误处理），每个目录覆盖相关功能
- **最小化测试数据**：测试数据应该精简，只包含验证功能所需的最小文件集
- **覆盖核心功能**：重点测试核心功能和边界情况

## 运行测试

**生成测试结果：**
```bash
uv run test/test_case.py verify core-success --generate
uv run test/test_case.py verify core-error --generate
```

**验证单个测试：**
```bash
uv run test/test_case.py verify core-success
uv run test/test_case.py verify core-error
```

**验证所有测试：**
```bash
uv run test/test_case.py verify-all
```

## 测试结构

- `test/core-success/` - 正常场景测试，尽可能覆盖 happy path
- `test/core-error/` - 错误处理测试，测试不中断主流程的错误码

## 测试用例格式

每个测试用例目录包含：
- `case.yaml` - 测试用例配置
- `data/` - 测试数据
- `result/` - 测试结果

**case.yaml 格式：**
```yaml
- name: core-success
  cli-params: ""              # 脚本参数（空字符串表示无特殊参数）
  return-code: 0              # 期望的返回码
  std-out: core-success.yaml   # 标准输出文件
  std-err: null               # 标准错误文件（null 表示期望为空）
```

## 输出格式

所有命令输出均为 YAML 格式，便于解析和处理。