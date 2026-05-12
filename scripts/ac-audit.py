#!/usr/bin/env python3
"""
AC Audit — Epic 文档验收标准审计脚本 v1.0.0

自动检查 Epic 文档中的验收标准 (Acceptance Criteria) 完成状态。
对比「文档声称」(checkbox [ ]) 与「代码实际」(文件/函数/测试存在性)。

用法:
    python3 scripts/ac-audit.py check <epic_file>    # 检查 AC 完成率
    python3 scripts/ac-audit.py sync <epic_file>     # 自动勾选可验证的 AC
    python3 scripts/ac-audit.py dashboard <epic_file> # 输出 Story 维度完成率表格

AI 友好设计: 输出标准化，AI 能自动解析完成状态。
"""

import argparse
import glob
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ── 验证器注册表 ──────────────────────────────────────────
# 每个验证器是一个函数: (ac_text: str, project_root: str) -> (可验证: bool, 已实现: bool, 证据: str)

# 预编译正则模式
PAT_FILE_EXISTS = re.compile(
    r'(?:创建|新增|添加|增加)\s*(?:了\s*)?[`‘"\']?([^`"\'《\n]+?\.(?:py|md|json|yaml|yml|toml|sh|conf|html|js))[`’"\']?',
    re.I
)
PAT_FUNCTION_EXISTS = re.compile(
    r'[`‘"\'](\w+)\(\)[`’"\']?\s*(?:方法|函数)',
    re.I
)
PAT_CLASS_EXISTS = re.compile(
    r'[`‘"\'](\w+)[`’"\']?\s*(?:类|Class)',
    re.I
)
PAT_CLI_COMMAND = re.compile(
    r'[`‘"\'](sra\s+\w+(?:\s+\w+)*)[`’"\']?\s*CLI',
    re.I
)
PAT_TEST_FILE = re.compile(
    r'[`‘"\']?(test_\w+\.py)[`’"\']?',
    re.I
)
PAT_ENDPOINT = re.compile(
    r'[`‘"\']((?:GET|POST|PUT|DELETE)\s+/\w+(?:/\w+)*)[`’"\']?',
    re.I
)
PAT_IMPORT = re.compile(
    r'[`‘"\'](from\s+\S+\s+import\s+\S+)[`’"\']',
    re.I
)
PAT_FILE_REF = re.compile(
    r'[`‘"\']([^`"\'/\s]+\/[^`"\'/\s]+\/\S+\.py)[`’"\']',
    re.I
)
PAT_DIR_EXISTS = re.compile(
    r'(?:创建|新增|添加)\s*(?:了\s*)?目录\s*[`‘"\']?([^`"\'《\n]+?)[`’"\']?',
    re.I
)


def verify_file_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的文件是否存在"""
    for pattern in [PAT_FILE_EXISTS, PAT_FILE_REF]:
        for match in pattern.finditer(ac_text):
            filepath = match.group(1)
            # 尝试多种路径解析
            for base in [project_root, os.path.join(project_root, 'skill_advisor'),
                         os.path.join(project_root, 'tests'), os.path.join(project_root, 'docs'),
                         os.path.join(project_root, 'scripts'), os.path.join(project_root, '.github')]:
                fullpath = os.path.join(base, filepath)
                if os.path.exists(fullpath):
                    return True, True, f"文件存在: {os.path.relpath(fullpath, project_root)}"
            # 尝试 glob 搜索
            matches = glob.glob(os.path.join(project_root, '**', filepath), recursive=True)
            if matches:
                relpath = os.path.relpath(matches[0], project_root)
                return True, True, f"文件存在: {relpath}"
            # 检查是否以路径片段形式存在
            if '/' in filepath:
                path_part = filepath.replace('\\', '/')
                matches = glob.glob(os.path.join(project_root, '**', path_part), recursive=True)
                if matches:
                    relpath = os.path.relpath(matches[0], project_root)
                    return True, True, f"文件存在: {relpath}"
    return False, None, ""


def verify_function_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的函数是否存在"""
    for match in PAT_FUNCTION_EXISTS.finditer(ac_text):
        func_name = match.group(1)
        # 在所有 Python 文件中搜索函数定义
        py_files = glob.glob(os.path.join(project_root, '**', '*.py'), recursive=True)
        for py_file in py_files:
            with open(py_file, 'r', errors='ignore') as f:
                content = f.read()
                # 检查函数定义
                if re.search(rf'def\s+{re.escape(func_name)}\s*\(', content):
                    relpath = os.path.relpath(py_file, project_root)
                    return True, True, f"函数存在: {relpath} → {func_name}()"
                # 检查方法定义
                if re.search(rf'\.{re.escape(func_name)}\s*=\s*', content):
                    relpath = os.path.relpath(py_file, project_root)
                    return True, True, f"方法存在: {relpath} → {func_name}"
    return False, None, ""


def verify_cli_command(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的 CLI 命令是否存在"""
    for match in PAT_CLI_COMMAND.finditer(ac_text):
        cmd = match.group(1)
        cmd_parts = cmd.split()
        if len(cmd_parts) >= 2:
            subcmd = cmd_parts[1]
            # 在 CLI 文件中搜索命令注册
            cli_files = glob.glob(os.path.join(project_root, 'skill_advisor', 'cli.py'))
            cli_files.extend(glob.glob(os.path.join(project_root, 'skill_advisor', '**', 'cli*.py'), recursive=True))
            for cli_file in cli_files:
                if os.path.exists(cli_file):
                    with open(cli_file, 'r', errors='ignore') as f:
                        content = f.read()
                        if subcmd in content and ('cmd_' + subcmd) in content:
                            relpath = os.path.relpath(cli_file, project_root)
                            return True, True, f"CLI 命令存在: {relpath} → {cmd}"
            # 也检查 commands.py
            cmd_files = glob.glob(os.path.join(project_root, 'skill_advisor', 'runtime', 'commands.py'))
            for cmd_file in cmd_files:
                if os.path.exists(cmd_file):
                    with open(cmd_file, 'r', errors='ignore') as f:
                        content = f.read()
                        if f"cmd_{subcmd}" in content:
                            relpath = os.path.relpath(cmd_file, project_root)
                            return True, True, f"CLI 命令存在: {relpath} → {cmd}"
    return False, None, ""


def verify_test_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的测试文件是否存在"""
    for match in PAT_TEST_FILE.finditer(ac_text):
        test_file = match.group(1)
        test_path = os.path.join(project_root, 'tests', test_file)
        if os.path.exists(test_path):
            return True, True, f"测试存在: tests/{test_file}"
        # glob 搜索
        matches = glob.glob(os.path.join(project_root, 'tests', '**', test_file), recursive=True)
        if matches:
            return True, True, f"测试存在: {os.path.relpath(matches[0], project_root)}"
    return False, None, ""


def verify_endpoint_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的 API 端点是否存在"""
    for match in PAT_ENDPOINT.finditer(ac_text):
        endpoint = match.group(1)
        method_part = endpoint.split()[0]  # GET/POST
        path_part = endpoint.split()[1] if ' ' in endpoint else endpoint

        # 在 daemon.py 或其他路由文件中搜索
        route_files = glob.glob(os.path.join(project_root, 'skill_advisor', '**', '*.py'), recursive=True)
        for rf in route_files:
            with open(rf, 'r', errors='ignore') as f:
                content = f.read()
                # 检查 self.path == "/xxx" 或 "/xxx": handler
                if path_part in content and method_part in content.upper():
                    relpath = os.path.relpath(rf, project_root)
                    return True, True, f"端点存在: {relpath} → {endpoint}"
    return False, None, ""


def verify_dir_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的目录是否存在"""
    for match in PAT_DIR_EXISTS.finditer(ac_text):
        dirpath = match.group(1)
        for base in [project_root, os.path.join(project_root, 'skill_advisor'),
                     os.path.join(project_root, 'tests'), os.path.join(project_root, 'docs')]:
            fullpath = os.path.join(base, dirpath)
            if os.path.isdir(fullpath):
                return True, True, f"目录存在: {os.path.relpath(fullpath, project_root)}"
    return False, None, ""


def verify_import_exists(ac_text: str, project_root: str) -> Tuple[bool, Optional[bool], str]:
    """验证 AC 中引用的 import 是否在代码中使用"""
    for match in PAT_IMPORT.finditer(ac_text):
        import_stmt = match.group(1)
        py_files = glob.glob(os.path.join(project_root, 'skill_advisor', '**', '*.py'), recursive=True)
        for py_file in py_files:
            with open(py_file, 'r', errors='ignore') as f:
                content = f.read()
                if import_stmt in content:
                    relpath = os.path.relpath(py_file, project_root)
                    return True, True, f"Import 存在: {relpath} → {import_stmt}"
    return False, None, ""


# 验证器注册表：按优先级排序
VERIFIERS = [
    ("文件存在", verify_file_exists),
    ("目录存在", verify_dir_exists),
    ("函数存在", verify_function_exists),
    ("CLI 命令", verify_cli_command),
    ("测试存在", verify_test_exists),
    ("端点存在", verify_endpoint_exists),
    ("Import 存在", verify_import_exists),
]


# ── Epic 文档解析 ───────────────────────────────────────

def parse_epic_ac(filepath: str) -> List[Dict]:
    """解析 Epic markdown 文档，提取所有 Story 和 AC"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    with open(filepath, 'r') as f:
        content = f.read()

    # 按 Story 分割
    story_sections = re.split(r'(?=### Story \d+)', content)

    results = []
    for section in story_sections:
        if not section.strip():
            continue

        # 提取 Story ID 和标题
        story_match = re.search(r'### Story\s+(\d+)[\s:]*(.*?)(?:\n|$)', section)
        story_id_match = re.search(r'(SRA-\d+-\d+)', section)

        story_num = story_match.group(1) if story_match else "?"
        story_title = story_match.group(2).strip() if story_match else ""
        story_id = story_id_match.group(1) if story_id_match else ""

        # 提取该 Story 下的所有 AC
        # 匹配 - [ ] 或 - [x] 开头的行
        ac_items = []
        for line in section.split('\n'):
            line_stripped = line.strip()
            ac_match = re.match(r'^-\s*\[([ x])\]\s*(.*)', line_stripped)
            if ac_match:
                checked = ac_match.group(1) == 'x'
                text = ac_match.group(2).strip()
                ac_items.append({
                    'checked': checked,
                    'text': text,
                    'line': line,
                })

        if ac_items:
            results.append({
                'story_num': story_num,
                'story_title': story_title,
                'story_id': story_id,
                'ac_items': ac_items,
            })

    return results


def verify_ac(ac_text: str, project_root: str) -> Tuple[bool, str]:
    """对单个 AC 文本执行所有验证器"""
    for verifier_name, verifier_func in VERIFIERS:
        applicable, implemented, evidence = verifier_func(ac_text, project_root)
        if applicable:
            return implemented, evidence
    return False, ""  # 无法自动验证


# ── Check 模式 ──────────────────────────────────────────

def cmd_check(epic_file: str, project_root: str):
    """检查模式：分析 AC 完成率"""
    stories = parse_epic_ac(epic_file)
    if not stories:
        print("❌ 未找到任何 Story 或 AC")
        return

    total_ac = 0
    total_checked = 0
    total_auto_verifiable = 0
    total_implemented_but_unchecked = 0

    print(f"\n{'='*60}")
    print(f"  📋 AC 审计报告: {os.path.basename(epic_file)}")
    print(f"{'='*60}")

    for story in stories:
        story_ac = len(story['ac_items'])
        story_checked = sum(1 for a in story['ac_items'] if a['checked'])
        story_unchecked = story_ac - story_checked

        total_ac += story_ac
        total_checked += story_checked

        print(f"\n  📌 Story {story['story_num']}: {story['story_title']}")
        if story['story_id']:
            print(f"     ID: {story['story_id']}")
        print(f"     AC: {story_checked}/{story_ac} ({story_checked*100//story_ac if story_ac else 0}%)")

        # 分析每个未勾选的 AC
        unchecked_acs = [a for a in story['ac_items'] if not a['checked']]
        for ac in unchecked_acs:
            implemented, evidence = verify_ac(ac['text'], project_root)
            if implemented:
                total_auto_verifiable += 1
                total_implemented_but_unchecked += 1
                print(f"     🔄  [ ] → 代码已实现! {evidence}")
                print(f"         AC: {ac['text'][:80]}")
            elif evidence:
                pass  # 有证据但不是 "已实现"（目前不会发生）
            else:
                print(f"     ⏳  [ ] 需人工验证")
                print(f"         AC: {ac['text'][:80]}")

    # 汇总
    print(f"\n{'='*60}")
    print(f"  📊 汇总")
    print(f"{'='*60}")
    print(f"  总 AC 数:          {total_ac}")
    print(f"  已勾选 [x]:        {total_checked} ({total_checked*100//total_ac if total_ac else 0}%)")
    print(f"  未勾选 [ ]:        {total_ac - total_checked}")
    print(f"  可自动验证:        {total_auto_verifiable}")
    print(f"  代码已实现但未勾选: {total_implemented_but_unchecked}")
    print(f"  需人工验证:        {total_ac - total_checked - total_implemented_but_unchecked}")

    # 完成率修正
    adjusted_completion = total_checked + total_implemented_but_unchecked
    print(f"\n  📈 文档声称完成率:   {total_checked*100//total_ac if total_ac else 0}%")
    print(f"  📈 实际完成率:      {adjusted_completion*100//total_ac if total_ac else 0}%")
    print(f"  📉 漂移:            -{total_implemented_but_unchecked} 个 AC 滞后于代码")
    print()

    return total_implemented_but_unchecked


# ── Sync 模式 ──────────────────────────────────────────

def cmd_sync(epic_file: str, project_root: str, dry_run: bool = True):
    """同步模式：自动勾选可验证的 AC"""
    stories = parse_epic_ac(epic_file)
    if not stories:
        print("❌ 未找到任何 Story 或 AC")
        return

    # 读取完整文件
    with open(epic_file, 'r') as f:
        content = f.read()

    total_synced = 0

    print(f"\n{'='*60}")
    print(f"  🔄 AC 同步: {os.path.basename(epic_file)}")
    print(f"{'='*60}")
    if dry_run:
        print("  (DRY RUN 模式 — 不会实际修改文件)")

    for story in stories:
        for ac in story['ac_items']:
            if ac['checked']:
                continue  # 已勾选，跳过

            # 对未勾选的 AC 执行验证
            implemented, evidence = verify_ac(ac['text'], project_root)
            if implemented:
                total_synced += 1
                old_line = ac['line'].rstrip()
                new_line = old_line.replace('- [ ]', '- [x]', 1)

                print(f"  ✅ [{'+' if not dry_run else '~'}] {story['story_id'] or story['story_num']}")
                print(f"      证据: {evidence}")

                if not dry_run:
                    # 在原始内容中替换
                    content = content.replace(old_line, new_line, 1)

    # 写回文件
    if not dry_run and total_synced > 0:
        with open(epic_file, 'w') as f:
            f.write(content)
        print(f"\n  ✅ 已同步 {total_synced} 个 AC 为 [x]")
    elif not dry_run and total_synced == 0:
        print("  ℹ️  没有需要同步的 AC")
    else:
        print(f"\n  📋 DRY RUN: 发现 {total_synced} 个可同步的 AC")
        print(f"  使用 --apply 标志实际写入文件")

    return total_synced


# ── Dashboard 模式 ─────────────────────────────────────

def cmd_dashboard(epic_file: str, project_root: str):
    """Dashboard 模式：输出 Story 维度完成率表格"""
    stories = parse_epic_ac(epic_file)
    if not stories:
        print("❌ 未找到任何 Story 或 AC")
        return

    print(f"\n{'='*70}")
    print(f"  📊 AC Dashboard — {os.path.basename(epic_file)}")
    print(f"{'='*70}")
    print(f"  {'Story':<8} {'ID':<16} {'Checked':<10} {'Actual':<10} {'ACs':<6} {'Status'}")
    print(f"  {'-'*8} {'-'*16} {'-'*10} {'-'*10} {'-'*6} {'-'*10}")

    total_ac = 0
    total_checked = 0
    total_actual = 0

    for story in stories:
        story_ac = len(story['ac_items'])
        story_checked = sum(1 for a in story['ac_items'] if a['checked'])

        # 计算实际完成数（已勾选 + 可自动验证的）
        story_actual = story_checked
        for ac in story['ac_items']:
            if not ac['checked']:
                implemented, _ = verify_ac(ac['text'], project_root)
                if implemented:
                    story_actual += 1

        checked_pct = story_checked * 100 // story_ac if story_ac else 0
        actual_pct = story_actual * 100 // story_ac if story_ac else 0

        # 状态符号
        if actual_pct == 100:
            status = "✅"
        elif actual_pct >= 80:
            status = "🟡"
        else:
            status = "🔴"

        sid = story['story_id'] if story['story_id'] else '-'
        print(f"  #{story['story_num']:<6} {sid:<16} {story_checked}/{story_ac} ({checked_pct:>2d}%) {story_actual}/{story_ac} ({actual_pct:>2d}%)  {status}")

        total_ac += story_ac
        total_checked += story_checked
        total_actual += story_actual

    # 总计行
    print(f"  {'-'*8} {'-'*16} {'-'*10} {'-'*10} {'-'*6} {'-'*10}")
    total_checked_pct = total_checked * 100 // total_ac if total_ac else 0
    total_actual_pct = total_actual * 100 // total_ac if total_ac else 0
    final_status = "✅ 全部完成" if total_actual_pct == 100 else f"⚠️  完成 {total_actual_pct}%"
    print(f"  {'总计':<8} {'':<16} {total_checked}/{total_ac} ({total_checked_pct:>2d}%) {total_actual}/{total_ac} ({total_actual_pct:>2d}%)  {final_status}")
    print(f"{'='*70}")
    print(f"  📈 文档声称完成率: {total_checked_pct}% | 实际完成率: {total_actual_pct}%")
    if total_actual > total_checked:
        print(f"  ⚠️  检测到 {total_actual - total_checked} 个 AC 文档滞后于代码")
    print()


# ── CLI 入口 ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AC Audit — Epic 文档验收标准审计脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/ac-audit.py check docs/EPIC-003-v2-enforcement-layer.md
  python3 scripts/ac-audit.py sync docs/EPIC-003-v2-enforcement-layer.md --dry-run
  python3 scripts/ac-audit.py sync docs/EPIC-003-v2-enforcement-layer.md --apply
  python3 scripts/ac-audit.py dashboard docs/EPIC-003-v2-enforcement-layer.md
        """
    )

    parser.add_argument('mode', choices=['check', 'sync', 'dashboard'],
                        help='操作模式')
    parser.add_argument('epic_file',
                        help='Epic markdown 文件路径')
    parser.add_argument('--project-root', default='.',
                        help='项目根目录（默认: 当前目录）')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='sync 模式的 dry-run（默认开启）')
    parser.add_argument('--apply', action='store_true',
                        help='sync 模式中实际写入文件')

    args = parser.parse_args()

    # 解析项目根目录
    project_root = os.path.abspath(args.project_root)

    # 解析 epic 文件路径
    epic_file = args.epic_file
    if not os.path.isabs(epic_file):
        epic_file = os.path.join(project_root, epic_file)

    if args.mode == 'check':
        cmd_check(epic_file, project_root)
    elif args.mode == 'sync':
        dry_run = not args.apply  # 默认 dry_run，--apply 时实际写入
        cmd_sync(epic_file, project_root, dry_run=dry_run)
    elif args.mode == 'dashboard':
        cmd_dashboard(epic_file, project_root)


if __name__ == '__main__':
    main()
