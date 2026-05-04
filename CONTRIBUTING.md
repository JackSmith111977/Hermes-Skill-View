# SRA — Skill Runtime Advisor

感谢你对 SRA 的关注！以下是如何参与贡献的指南。

## 🐛 报告 Bug

1. 使用 [Bug Report 模板](https://github.com/JackSmith111977/Hermes-Skill-View/issues/new?template=bug_report.md)
2. 提供完整的环境信息（OS、Python 版本、SRA 版本）
3. 附上复现步骤和期望行为

## 💡 提出新功能

1. 先搜索 [已有的 Issue/Discussion](https://github.com/JackSmith111977/Hermes-Skill-View/issues) 确认是否已有人提过
2. 使用 [Feature Request 模板](https://github.com/JackSmith111977/Hermes-Skill-View/issues/new?template=feature_request.md)
3. 清晰描述解决的问题和你的方案

## 🔧 提交代码

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交改动：`git commit -m 'feat: add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

### 代码规范

- 确保测试通过：`pytest tests/ -v`
- 新功能请添加测试覆盖
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范

### 匹配引擎改动

如果修改了 `matcher.py`，请确保：
1. 更新基准测试数据
2. 新增同义词时中英文都映射
3. 所有覆盖率测试通过

## 📖 完善文档

- README 可以增加使用示例
- 文档改进可以单独提交 PR
- 中英文文档都欢迎

## ❓ 问题咨询

请使用 [GitHub Discussions](https://github.com/JackSmith111977/Hermes-Skill-View/discussions) 进行问题咨询。

## 行为准则

请保持友好、尊重、包容的交流氛围。

---

**感谢你为 SRA 做的贡献！❤️**
