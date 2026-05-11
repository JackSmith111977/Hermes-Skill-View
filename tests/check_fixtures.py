#!/usr/bin/env python3
"""验证测试 Fixture 完整性的辅助脚本

在 CI 中运行，确保 tests/fixtures/skills/ 包含至少 300 个有效的 SKILL.md 文件。
也供本地 pre-flight check 使用。

用法:
    python3 tests/check_fixtures.py
"""
import os
import sys

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")


def main():
    if not os.path.isdir(FIXTURES_DIR):
        print(f"❌ Fixture 目录不存在: {FIXTURES_DIR}")
        sys.exit(1)

    count = 0
    for root, dirs, files in os.walk(FIXTURES_DIR):
        for f in files:
            if f == "SKILL.md":
                count += 1

    threshold = 300
    if count < threshold:
        print(f"❌ Fixture 不完整: 找到 {count} 个 SKILL.md，需要至少 {threshold}")
        sys.exit(1)

    print(f"✅ Fixture 完整性验证通过: {count} 个有效 SKILL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
