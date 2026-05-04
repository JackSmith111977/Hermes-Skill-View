# 贡献指南

感谢你考虑为 SRA 做贡献！

## 开发环境

```bash
git clone https://github.com/yourname/sra-agent
cd sra-agent
pip install -e ".[dev]"
```

## 代码规范

- 遵循 PEP 8
- 所有公开函数需要有类型注解和 docstring
- 新增同义词时确保中英文都有映射
- 不要破坏现有测试

## 测试

所有贡献必须附带测试：

```bash
# 运行全部测试
pytest tests/ -v

# 只跑覆盖率测试
pytest tests/test_coverage.py -v

# 运行基准测试
pytest tests/test_benchmark.py -v
```

**覆盖率要求**：
- 有 trigger 的 skill 识别率 ≥ 85%
- 所有 skill 综合识别率 ≥ 50%
- 常见用户查询通过率 ≥ 60%

## 提交 PR

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 发布流程

```bash
# 更新版本号
# 更新 CHANGELOG
git tag v1.0.0
git push origin v1.0.0
# GitHub Actions 会自动发布到 PyPI
```
