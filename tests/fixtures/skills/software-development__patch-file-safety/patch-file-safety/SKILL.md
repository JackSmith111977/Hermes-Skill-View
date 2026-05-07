---
name: patch-file-safety
description: 安全使用 patch 工具的最佳实践指南——何时用 patch、何时用 write_file、什么时候该重写整个文件。避免大块替换污染文件的风险。
version: 1.0.0
triggers:
- 需要修改代码文件
- patch 工具遇到问题
- 文件被 patch 污染了
- 如何安全编辑文件
- 大块替换代码
allowed-tools:
- read_file
- write_file
- patch
- terminal
- execute_code
metadata:
  hermes:
    tags:
    - patch
    - file-edit
    - safety
    - code-modification
    category: software-development
    skill_type: library-reference
    design_pattern: tool-wrapper
category: software-development
---
# patch-file-safety

安全使用 patch 工具的最佳实践指南——何时用 patch、何时用 write_file、什么时候该重写整个文件。避免大块替换污染文件的风险。
