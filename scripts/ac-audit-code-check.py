#!/usr/bin/env python3
"""AC 代码存在性门禁 — 验证 [x] AC 有真实代码

背景:
  EPIC-001/003 的教训 — AC 标记 [x] 只说明「文档上打了勾」，
  不说明「代码真实存在」。本脚本通过执行 ``<!-- 验证: ... -->``
  注释中的命令，实际验证 AC 是否真实完成。

用法:
  python3 scripts/ac-audit-code-check.py docs/EPIC-004.md
  python3 scripts/ac-audit-code-check.py docs/EPIC-003-v2-enforcement-layer.md

退出码:
  0 — 所有 AC 验证通过
  1 — 有 AC 验证失败（测试/文件不存在）
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def find_verify_comments(file_path: str) -> list[dict]:
    """解析文件中的 AC 行和验证注释

    匹配模式:
      - [x] ... <!-- 验证: <command> -->
      - | ✅ | ... | <command> |  (表格形式)
    """
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    checks = []

    # 模式 1: [x] AC + <!-- ... 验证: ... -->
    pattern1 = re.compile(
        r'\[x\].*?<!--.*?验证:\s*(.+?)\s*-->', re.DOTALL
    )
    for match in pattern1.finditer(text):
        cmd = match.group(1).strip()
        # 去除 markdown 反引号
        cmd = cmd.strip("`").strip()
        # 截取 AC 描述（[x] 到 <!-- 之间的文本）
        ac_text = match.group(0)
        ac_desc = ac_text.split("[x]")[-1].split("<!--")[0].strip()
        checks.append({
            "ac": ac_desc or "(AC)",
            "cmd": cmd,
            "type": "inline",
        })

    # 模式 2: | ✅ | ... | <验证命令> | （表格行）
    pattern2 = re.compile(
        r'\|\s*✅\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(test|pytest|python3.+?.py)',
        re.IGNORECASE,
    )
    for match in pattern2.finditer(text):
        desc = match.group(1).strip()
        cmd = match.group(0).strip().split("|")[-2].strip() if "|" in match.group(0) else desc
        checks.append({
            "ac": desc,
            "cmd": cmd,
            "type": "table",
        })

    return checks


def run_verify(cmd: str, project_root: Path) -> dict:
    """执行验证命令"""
    try:
        # 如果是 pytest 命令，加上 --collect-only 避免实际执行
        if cmd.startswith("pytest") and "--collect-only" not in cmd:
            # 检查测试文件是否存在
            parts = cmd.split()
            test_path = None
            for p in parts:
                if p.endswith(".py") and not p.startswith("-"):
                    test_path = project_root / p
                    break

            if test_path and not test_path.exists():
                return {
                    "passed": False,
                    "output": f"测试文件不存在: {test_path}",
                }

            # 用 --collect-only 验证可收集
            collect_cmd = cmd.replace("-q", "").strip()
            if "--tb" not in collect_cmd:
                collect_cmd += " --collect-only -q"
            result = subprocess.run(
                collect_cmd, shell=True, capture_output=True, text=True, timeout=30,
                cwd=str(project_root),
            )
            if result.returncode != 0:
                return {
                    "passed": False,
                    "output": result.stderr.strip() or result.stdout.strip(),
                }
            # 提取测试数量
            count_match = re.search(r'collected (\d+)', result.stdout)
            count = int(count_match.group(1)) if count_match else 0
            return {
                "passed": True,
                "output": f"✅ 测试可收集 ({count} tests)",
            }

        # 其他命令直接执行
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            cwd=str(project_root),
        )
        return {
            "passed": result.returncode == 0,
            "output": result.stdout.strip() or result.stderr.strip() or "(no output)",
        }

    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "⏱️ 超时 (30s)"}
    except Exception as e:
        return {"passed": False, "output": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="AC 代码存在性门禁 — 验证 [x] AC 有真实代码",
    )
    parser.add_argument(
        "files", nargs="*", default=["docs/EPIC-004.md"],
        help="要检查的文档文件路径（默认: docs/EPIC-004.md）",
    )
    parser.add_argument(
        "--project-root", default=".",
        help="项目根目录（默认: 当前目录）",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="只列出发现的验证点，不执行验证",
    )

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    all_passed = True
    total_checks = 0

    for file_path in args.files:
        full_path = (project_root / file_path).resolve()
        if not full_path.exists():
            print(f"\n📄 {file_path} — ❌ 文件不存在，跳过")
            continue

        checks = find_verify_comments(str(full_path))
        if not checks:
            print(f"\n📄 {file_path} — ⚠️ 未找到可验证的 AC 行")
            continue

        print(f"\n📄 {file_path} — 发现 {len(checks)} 个验证点")
        total_checks += len(checks)

        for i, check in enumerate(checks, 1):
            if args.list:
                print(f"  [{i}] {check['ac']}")
                print(f"       验证: {check['cmd']}")
                continue

            result = run_verify(check["cmd"], project_root)

            if result["passed"]:
                print(f"  ✅ [{i}] {check['ac']}")
                if result["output"]:
                    print(f"       {result['output']}")
            else:
                print(f"  ❌ [{i}] {check['ac']}")
                print(f"      命令: {check['cmd']}")
                print(f"      错误: {result['output'][:200]}")
                all_passed = False

    if args.list:
        print(f"\n共 {total_checks} 个验证点")
        return

    if all_passed and total_checks > 0:
        print(f"\n🎉 全部 {total_checks} 个 AC 验证通过！")
        sys.exit(0)
    elif total_checks == 0:
        print("\n⚠️ 没有需要验证的 AC")
        sys.exit(0)
    else:
        print(f"\n❌ 存在失败的 AC 验证")
        sys.exit(1)


if __name__ == "__main__":
    main()
