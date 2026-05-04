"""
SRA CLI 入口
"""

import sys
import os

# 确保包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from skill_advisor import SkillAdvisor
    
    if len(sys.argv) < 2:
        print("SRA — Skill Runtime Advisor v1.0")
        print()
        print("用法: sra <command> [options]")
        print()
        print("  --query <输入>         推荐匹配")
        print("  --refresh             刷新技能索引")
        print("  --stats               查看统计")
        print("  --coverage            分析技能识别覆盖率")
        print("  --record <skill>      记录使用")
        print("    --input <输入>       用户输入")
        print("    --accepted <bool>    是否接受推荐")
        print("  --enhanced-prompt      生成增强版 system prompt")
        print("  --daemon              守护模式")
        return
    
    cmd = sys.argv[1]
    advisor = SkillAdvisor()
    
    if cmd == "--refresh":
        count = advisor.refresh_index()
        print(f"✅ 技能索引已刷新：{count} 个 skill")
    
    elif cmd == "--query":
        if len(sys.argv) < 3:
            print("🚨 请提供查询内容: --query <输入>")
            return
        query = " ".join(sys.argv[2:])
        result = advisor.recommend(query)
        
        print(f"🔍 查询: '{query}'")
        print(f"⚡ 处理时间: {result['processing_ms']}ms")
        print(f"📊 扫描 {result['skills_scanned']} 个 skill")
        print()
        
        if result["recommendations"]:
            print("🎯 推荐技能:")
            for r in result["recommendations"]:
                icon = "✅" if r["confidence"] == "high" else "💡"
                print(f"  {icon} {r['skill']} (得分: {r['score']})")
                print(f"     📄 {r['description']}")
                print(f"     📂 类别: {r['category']}")
                print(f"     💬 理由: {'; '.join(r['reasons'][:3])}")
                if r["confidence"] == "high":
                    print(f"     ⚡ 建议: 自动加载")
                print()
        else:
            print("📭 未找到匹配技能")
    
    elif cmd == "--stats":
        stats = advisor.show_stats()
        print("=" * 50)
        print("📊 SRA 统计")
        print("=" * 50)
        print(f"  技能总数: {stats['total_skills']}")
        print(f"  总推荐次数: {stats['total_recommendations']}")
        print(f"  场景模式: {stats['scene_patterns']} 条")
        print(f"  有使用记录的技能: {stats['skills_with_stats']} 个")
        
        # 常用技能
        memory = stats.get("memory", {})
        skill_usage = memory.get("skills", {})
        if skill_usage:
            print()
            print("📈 最常用技能:")
            sorted_skills = sorted(skill_usage.items(), key=lambda x: x[1]["total_uses"], reverse=True)
            for name, data in sorted_skills[:10]:
                rate = data.get("acceptance_rate", 0)
                last = (data.get("last_used") or "")[:16]
                bar = "█" * min(data["total_uses"], 20) + "░" * max(0, 20 - min(data["total_uses"], 20))
                print(f"  {bar} {name} ({data['total_uses']}次, 接受率{rate:.0%})")
    
    elif cmd == "--coverage":
        result = advisor.analyze_coverage()
        print("=" * 60)
        print(f"📊 SRA 技能识别覆盖率分析")
        print("=" * 60)
        print(f"  总技能数: {result['total']}")
        print(f"  能识别的: {result['covered']}")
        print(f"  覆盖率: {result['coverage_rate']}%")
        print()
        
        not_covered = result.get("not_covered", [])
        if not_covered:
            print(f"❌ 未能识别的技能 ({len(not_covered)} 个):")
            for s in not_covered[:20]:
                print(f"  - {s['name']} ({s['category']}) 最高分: {s['max_score']}")
            if len(not_covered) > 20:
                print(f"  ... 还有 {len(not_covered) - 20} 个")
        else:
            print("🎉 所有技能都能被识别！")
    
    elif cmd == "--record":
        if len(sys.argv) < 4:
            print("🚨 用法: --record <skill_name> --input <user_input> [--accepted true/false]")
            return
        skill_name = sys.argv[2]
        user_input = ""
        accepted = True
        
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--input" and i + 1 < len(sys.argv):
                user_input = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--accepted" and i + 1 < len(sys.argv):
                accepted = sys.argv[i + 1].lower() == "true"
                i += 2
            else:
                i += 1
        
        if not user_input:
            print("🚨 需要 --input 参数")
            return
        
        advisor.record_usage(skill_name, user_input, accepted)
        print(f"✅ 已记录: {skill_name} ← '{user_input[:50]}'")
    
    elif cmd == "--enhanced-prompt":
        advisor._ensure_index()
        skills = advisor.indexer.get_skills()
        from collections import defaultdict
        
        lines = ["<available_skills>"]
        by_cat = defaultdict(list)
        for s in skills:
            by_cat[s["category"]].append(s)
        
        for category in sorted(by_cat.keys()):
            lines.append(f"  {category}:")
            for s in sorted(by_cat[category], key=lambda x: x["name"]):
                name = s["name"]
                desc = s.get("description", "")[:100]
                triggers = s.get("triggers", [])
                tag_str = f" [triggers: {'/'.join(triggers[:5])}]" if triggers else ""
                lines.append(f"    - {name}: {desc}{tag_str}" if desc else f"    - {name}{tag_str}")
        
        lines.append("</available_skills>")
        print("\n".join(lines))
    
    elif cmd == "--daemon":
        import time
        print("🚀 SRA 守护模式启动（每 60 秒检查一次）")
        while True:
            advisor._ensure_index()
            skills = advisor.indexer.get_skills()
            print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] 索引活跃: {len(skills)} skills")
            time.sleep(60)


if __name__ == "__main__":
    main()
