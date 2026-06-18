---
repo-layout:
  meta:
    "{case}/": 
      :meta: Each folder is a test group with multiple test cases, "core-success" for success cases, "core-error" for error cases
      data: Data files, created manually
      result: Generated test results, only need to be updated manually if big changes occur
      case.yaml: Test cases configuration
  when:
    - tag: [standard]
      show_files: false
---

## 测试脚本

测试脚本位于 `test/test_case.py`，用于验证脚本功能。

## 主测试规范

### 核心成功测试组

`test/core-success/`

如果添加了新功能，或者修改了已有功能，需要在 core-success 中添加或修改测试用例。

1. 如果需要处理新的文件或者对已有的文件进行修改，需要在 core-success/data 中进行修改，这里不应该包括任何可能潜在引发错误的文件。
2. 如果新增了命令行参数，需要在 core-success/case.yaml 中添加新的测试用例。
  1. 对于新增的命令行参数，某个参数如果和默认值相同，需要保证配置 `std-out: no-param.out.yaml`。
  2. 优先配置单个命令行参数，仅在已知出现多个参数相互影响的情况，再配置多个命令行参数。
3. 使用 `uv run test/test_case.py verify core-success --generate` 生成测试结果。
4. 别忘了确保生成的测试结果是符合预期的，`--generate` 只会校验返回值。


### 核心错误测试组

`test/core-error/` - 错误处理测试，测试不中断主流程的错误码

如果添加了新的错误码，需要在 core-error 中添加或修改测试用例。

1. 在 core-error/data 中创建新的测试数据文件夹，使用新增的错误码作为文件夹名称，并在其中放置测试数据。
2. 使用 `uv run test/test_case.py verify core-error --generate` 生成测试结果。
3. 校验一下 `conflict.err.yaml` 内的错误码是否符合预期。
4. 如果修改了输出，也需要检查一下 `conflict.out.yaml` 是否符合预期。


## 测试命令示例

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

## 测试组格式

每个测试组目录包含：
- `case.yaml` - 测试用例配置
- `data/` - 测试数据
- `result/` - 测试结果

**case.yaml 格式：**
```yaml
- name: core-success
  # 脚本参数（空字符串表示无特殊参数）
  cli-params: ""
  # 期望的返回码
  return-code: 0
  # 默认使用name生成每个case的输出文件名：{name}.out.yaml
  # 如果配置了此字段，只校验不生成，用来校验改命令匹配前面的某个case。
  std-out: some.yaml
```
