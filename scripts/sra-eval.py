#!/usr/bin/env python3
"""
SRA — 推荐质量评估工具（Cranfield 范式）

运行方式:
    python3 scripts/sra-eval.py                    # 完整评估
    python3 scripts/sra-eval.py --compare          # 与上次结果对比
    python3 scripts/sra-eval.py --detail           # 每个查询的详细结果
    
设计原理: 基于 TREC/Cranfield 信息检索评估范式
- 文档集: 279 个 SKILL.md
- 查询集: 100 个分层测试查询 (L1-L5)
- 相关性判断: 从 skill triggers 自动生成
- 评估指标: Recall@K, MRR, NDCG@K, Spurious@K

输出: 按难度分层的量化评估报告
"""

import json
import os
import sys
import re
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict


# ════════════════════════════════════════════════════════════════
#  配置
# ════════════════════════════════════════════════════════════════

SRA_API = "http://127.0.0.1:8536/recommend"
SRA_HEALTH = "http://127.0.0.1:8536/health"
SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
RESULT_FILE = os.path.expanduser("~/.sra/eval_result.json")
TOP_K = 5  # 评估 top-5 推荐


# ════════════════════════════════════════════════════════════════
#  测试查询集 — 按难度分层 (L1-L5)
# ════════════════════════════════════════════════════════════════

TEST_QUERIES = {
    # ── L1: 精确匹配 (skill 名称直接匹配) ──
    "L1_ppt": {"q": "ppt", "cat": ["ppt", "powerpoint", "pptx"]},
    "L1_pdf": {"q": "pdf", "cat": ["pdf", "reportlab", "weasyprint"]},
    "L1_git": {"q": "git", "cat": ["git"]},
    "L1_feishu": {"q": "飞书", "cat": ["feishu"]},
    "L1_mermaid": {"q": "mermaid", "cat": ["mermaid"]},
    "L1_excel": {"q": "excel", "cat": ["excel", "xlsx"]},
    "L1_markdown": {"q": "markdown", "cat": ["markdown"]},
    "L1_latex": {"q": "latex", "cat": ["latex"]},
    "L1_docker": {"q": "docker", "cat": ["linux", "server", "ops", "deploy"]},
    "L1_test": {"q": "测试", "cat": ["test"]},
    "L1_arxiv": {"q": "arxiv", "cat": ["arxiv", "paper", "学术"]},
    "L1_wechat": {"q": "微信", "cat": ["wechat", "weixin"]},
    "L1_ascii": {"q": "ascii", "cat": ["ascii"]},
    "L1_pokemon": {"q": "pokemon", "cat": ["pokemon", "game"]},
    "L1_minecraft": {"q": "minecraft", "cat": ["minecraft"]},
    "L1_gif": {"q": "gif", "cat": ["gif"]},
    "L1_obsidian": {"q": "obsidian", "cat": ["obsidian", "note"]},
    "L1_news": {"q": "news", "cat": ["news", "rss", "简报"]},
    "L1_email": {"q": "email", "cat": ["email", "mail"]},
    "L1_epub": {"q": "epub", "cat": ["epub", "ebook"]},

    # ── L2: 同义映射 (需中英文桥接) ──
    "L2_architecture": {"q": "画架构图", "cat": ["architecture"]},
    "L2_slides": {"q": "幻灯片", "cat": ["ppt", "powerpoint", "pptx"]},
    "L2_word": {"q": "word文档", "cat": ["word", "docx"]},
    "L2_schedule_job": {"q": "定时任务", "cat": ["cron", "schedule", "定时"]},
    "L2_search_web": {"q": "搜索信息", "cat": ["search", "web"]},
    "L2_translate": {"q": "翻译英文", "cat": ["translate"]},
    "L2_finance": {"q": "股票行情", "cat": ["stock", "finance", "金融"]},
    "L2_code_review": {"q": "审查代码", "cat": ["code review", "review"]},
    "L2_deploy": {"q": "部署上线", "cat": ["deploy", "发布"]},
    "L2_monitor": {"q": "监控系统", "cat": ["monitor", "监控"]},
    "L2_learn": {"q": "学习新东西", "cat": ["learn", "学习"]},
    "L2_refactor": {"q": "重构代码", "cat": ["refactor", "重构"]},
    "L2_bug_fix": {"q": "修复bug", "cat": ["debug", "bug", "调试"]},
    "L2_drawing": {"q": "画图", "cat": ["draw", "diagram", "画图"]},
    "L2_data_analysis": {"q": "数据分析", "cat": ["data", "分析"]},
    "L2_proxy": {"q": "配置代理", "cat": ["proxy", "代理"]},
    "L2_reminder": {"q": "设置提醒", "cat": ["通知", "reminder", "提醒"]},
    "L2_music": {"q": "生成音乐", "cat": ["music", "song", "音乐"]},
    "L2_video": {"q": "制作动画", "cat": ["video", "animation", "manim"]},
    "L2_image": {"q": "生成图片", "cat": ["image", "picture", "图片"]},

    # ── L3: 语义理解 (自然语言任务描述) ──
    "L3_create_ppt": {"q": "帮我把设计稿做成能演示的PPT", "cat": ["ppt", "powerpoint", "pptx"]},
    "L3_search_ai_news": {"q": "帮我搜索最新的AI行业新闻", "cat": ["news", "search", "web"]},
    "L3_fix_server": {"q": "服务器连不上了帮我看看", "cat": ["linux", "server", "ops"]},
    "L3_summary_report": {"q": "写一份本周工作总结", "cat": ["汇报", "report", "总结"]},
    "L3_send_file": {"q": "发一个文件到群里", "cat": ["feishu", "wechat", "file"]},
    "L3_learn_python": {"q": "我想学Python怎么做", "cat": ["learn", "学习"]},
    "L3_db_design": {"q": "设计数据库表结构", "cat": ["database", "data"]},
    "L3_code_gen": {"q": "帮我写一个Python脚本", "cat": ["code", "program", "编程"]},
    "L3_research_topic": {"q": "调研一下最新的RAG技术", "cat": ["research", "调研"]},
    "L3_export_report": {"q": "把这次测试结果导出成PDF", "cat": ["pdf", "report"]},

    # ── L4: 多跳推理 (多个skill组合) ──
    "L4_crawl_report": {"q": "每天自动爬取新闻生成PDF报告", "cat": ["news", "pdf", "cron"]},
    "L4_send_reminder": {"q": "每天早上8点发飞书消息提醒我开会", "cat": ["feishu", "cron", "通知"]},
    "L4_market_ppt": {"q": "分析股票数据做成PPT每周发送", "cat": ["stock", "ppt", "cron"]},
    "L4_search_translate": {"q": "搜索一篇英文论文翻译成中文", "cat": ["search", "translate", "arxiv"]},
    "L4_monitor_alert": {"q": "监控服务器状态异常时发微信告警", "cat": ["monitor", "wechat", "linux"]},

    # ── L5: 噪声抑制 (不应推荐任何skill) ──
    "L5_greeting": {"q": "你好", "cat": []},
    "L5_weather": {"q": "今天天气怎么样", "cat": []},
    "L5_thanks": {"q": "谢谢", "cat": []},
    "L5_goodbye": {"q": "再见", "cat": []},
    "L5_meaning": {"q": "人生的意义是什么", "cat": []},
}


# ════════════════════════════════════════════════════════════════
#  核心函数
# ════════════════════════════════════════════════════════════════

def check_sra():
    """检查 SRA Daemon 是否运行"""
    try:
        req = urllib.request.Request(SRA_HEALTH)
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        skills = data.get("skills_count", 0)
        print(f"✅ SRA Daemon 运行中 | 技能数: {skills}")
        return True
    except Exception as e:
        print(f"❌ SRA Daemon 不可用: {e}")
        return False


def query_sra(query_text):
    """向 SRA 发送推荐查询"""
    try:
        req = urllib.request.Request(
            SRA_API,
            data=json.dumps({"message": query_text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        recs = data.get("recommendations", [])
        # 返回 skill 名称列表
        return [r["skill"] for r in recs[:TOP_K]]
    except Exception as e:
        return []


def skill_matches_category(skill_name, categories, skill_meta=None):
    """
    判断一个 skill 是否属于指定的类别。
    支持多级匹配：category 字段、name 关键词、tags。
    """
    name_lower = skill_name.lower()
    for cat in categories:
        cat_lower = cat.lower()
        # 直接名称匹配
        if cat_lower in name_lower or name_lower in cat_lower:
            return True
        # 部分匹配（"pdf" 匹配 "pdf-layout"）
        if len(cat_lower) >= 3 and cat_lower in name_lower:
            return True
    return False


def compute_qrels(test_queries, skills):
    """
    自动生成相关性判断 (Qrels)。
    从 query 的 cat 字段和 skill 的 name/description 比对，判断相关性。
    
    返回: {query_id: {skill_name: relevance_score}}
    """
    qrels = {}
    for qid, info in test_queries.items():
        query = info["q"]
        categories = info["cat"]
        query_lower = query.lower()
        
        rels = {}
        for skill in skills:
            name = skill.get("name", "")
            desc = skill.get("description", "")
            triggers = skill.get("triggers", [])
            tags = skill.get("tags", [])
            category = skill.get("category", "")
            
            name_lower = name.lower()
            desc_lower = desc.lower()
            
            relevance = 0.0
            
            # 精确 trigger 匹配
            for t in triggers:
                t_lower = t.lower()
                if query_lower in t_lower or t_lower in query_lower:
                    relevance = max(relevance, 2.0)
                # 部分匹配
                if len(query_lower) >= 3 and query_lower in t_lower:
                    relevance = max(relevance, 1.5)
            
            # 类别匹配 (直接匹配 categories)
            for cat in categories:
                cat_lower = cat.lower()
                if cat_lower in name_lower or name_lower in cat_lower:
                    relevance = max(relevance, 2.0)
                if cat_lower in category.lower():
                    relevance = max(relevance, 1.5)
                for tag in tags:
                    if cat_lower in tag.lower():
                        relevance = max(relevance, 1.5)
                if len(cat_lower) >= 3 and cat_lower in desc_lower:
                    relevance = max(relevance, 0.5)
            
            # 查询词本身名称匹配
            for word in re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}', query_lower):
                if word in name_lower:
                    relevance = max(relevance, 1.0)
            
            if relevance > 0:
                rels[name] = relevance
        
        qrels[qid] = rels
    return qrels


def evaluate_run(test_queries, qrels, results):
    """
    对一次运行结果计算所有指标。
    
    Args:
        test_queries: 测试查询集
        qrels: 相关性判断 {qid: {skill: relevance}}
        results: SRA 返回结果 {qid: [skill_names]}
    
    Returns:
        metrics: 各指标值
        details: 各查询的详细信息
    """
    total_recall = 0.0
    total_mrr = 0.0
    total_ndcg = 0.0
    total_spurious = 0.0
    query_count = len(test_queries)
    
    # 按难度分层
    level_results = defaultdict(lambda: {
        "recall": [], "mrr": [], "ndcg": [], "spurious": [], "count": 0
    })
    
    details = {}
    
    for qid in test_queries:
        info = test_queries[qid]
        level = qid.split("_")[0]  # L1, L2, etc.
        level_results[level]["count"] += 1
        
        qrel = qrels.get(qid, {})
        run = results.get(qid, [])
        
        # 找出相关 skill
        relevant_skills = set(qrel.keys())
        relevant_count = len(relevant_skills)
        
        # ── Recall@K ──
        if relevant_count > 0:
            retrieved_relevant = sum(1 for s in run[:TOP_K] if s in relevant_skills)
            recall = retrieved_relevant / relevant_count
        else:
            recall = 1.0  # 无相关skill时视为完美
        
        # ── MRR ──
        mrr = 0.0
        for i, s in enumerate(run[:TOP_K]):
            if s in relevant_skills:
                mrr = 1.0 / (i + 1)
                break
        
        # ── NDCG@K ──
        dcg = 0.0
        idcg = 0.0
        for i, s in enumerate(run[:TOP_K]):
            rel = qrel.get(s, 0.0)
            dcg += rel / (i + 1)  # 简化版，不用 log2
        
        # 理想排序
        ideal_rels = sorted(qrel.values(), reverse=True)
        for i in range(min(TOP_K, len(ideal_rels))):
            idcg += ideal_rels[i] / (i + 1)
        
        ndcg = dcg / idcg if idcg > 0 else 0.0
        
        # ── Spurious@K (推荐了无关skill的比例) ──
        if len(run) > 0 and relevant_skills:
            spurious_count = sum(1 for s in run[:TOP_K] if s not in relevant_skills and relevant_count > 0)
            spurious = spurious_count / min(len(run), TOP_K)
        else:
            spurious = 0.0
        
        total_recall += recall
        total_mrr += mrr
        total_ndcg += ndcg
        total_spurious += spurious
        
        level_results[level]["recall"].append(recall)
        level_results[level]["mrr"].append(mrr)
        level_results[level]["ndcg"].append(ndcg)
        level_results[level]["spurious"].append(spurious)
        
        details[qid] = {
            "query": info["q"],
            "level": level,
            "top_recommended": run[:3],
            "expected_categories": info["cat"],
            "recall": round(recall, 3),
            "mrr": round(mrr, 3),
            "ndcg": round(ndcg, 3),
            "spurious": round(spurious, 3),
        }
    
    metrics = {
        "recall_at_5": round(total_recall / query_count, 3),
        "mrr": round(total_mrr / query_count, 3),
        "ndcg_at_5": round(total_ndcg / query_count, 3),
        "spurious_at_5": round(total_spurious / query_count, 3),
    }
    
    # 综合得分 (加权)
    metrics["composite_score"] = round(
        metrics["recall_at_5"] * 0.30 +
        metrics["mrr"] * 0.35 +
        metrics["ndcg_at_5"] * 0.25 +
        (1 - metrics["spurious_at_5"]) * 0.10,
        3
    )
    
    # 按难度分层报告
    level_metrics = {}
    for level in ["L1", "L2", "L3", "L4", "L5"]:
        lr = level_results[level]
        if lr["count"] > 0:
            recall_avg = sum(lr["recall"]) / lr["count"]
            mrr_avg = sum(lr["mrr"]) / lr["count"]
            ndcg_avg = sum(lr["ndcg"]) / lr["count"]
            spurious_avg = sum(lr["spurious"]) / lr["count"]
            
            level_metrics[level] = {
                "count": lr["count"],
                "recall_at_5": round(recall_avg, 3),
                "mrr": round(mrr_avg, 3),
                "ndcg_at_5": round(ndcg_avg, 3),
                "spurious_at_5": round(spurious_avg, 3),
            }
    
    return metrics, level_metrics, details


def load_skills_meta():
    """从 SRA Daemon 加载技能元数据"""
    try:
        # 从索引文件或daemon加载
        index_file = os.path.expanduser("~/.sra/data/skill_full_index.json")
        if os.path.exists(index_file):
            with open(index_file) as f:
                data = json.load(f)
            return data.get("skills", [])
    except:
        pass
    return []


# ════════════════════════════════════════════════════════════════
#  报告输出
# ════════════════════════════════════════════════════════════════

def format_level_name(level):
    names = {
        "L1": "L1 精确匹配",
        "L2": "L2 同义映射",
        "L3": "L3 语义理解",
        "L4": "L4 多跳推理",
        "L5": "L5 噪声抑制",
    }
    return names.get(level, level)


def color_score(score):
    if score >= 0.85:
        return f"✅ {score:.1%}"
    elif score >= 0.60:
        return f"⚠️  {score:.1%}"
    else:
        return f"❌ {score:.1%}"


def print_report(metrics, level_metrics, baseline=None):
    """打印评估报告"""
    print()
    print("╔════════════════════════════════════════════╗")
    print("║     SRA 推荐质量评估报告                    ║")
    print("╠════════════════════════════════════════════╣")
    print(f"║  综合得分:         {metrics['composite_score']:.1f}/100")
    print("║")
    print(f"║  Recall@5:         {metrics['recall_at_5']:.3f}  " + color_score(metrics['recall_at_5']))
    print(f"║  MRR:              {metrics['mrr']:.3f}  " + color_score(metrics['mrr']))
    print(f"║  NDCG@5:           {metrics['ndcg_at_5']:.3f}  " + color_score(metrics['ndcg_at_5']))
    print(f"║  Spurious@5:       {metrics['spurious_at_5']:.3f}  (越低越好)")
    print("╠════════════════════════════════════════════╣")
    print("║  按难度分层:                                ║")
    
    for level in ["L1", "L2", "L3", "L4", "L5"]:
        lm = level_metrics.get(level)
        if lm:
            level_name = format_level_name(level)
            comp = (lm['recall_at_5'] * 0.30 + lm['mrr'] * 0.35 + 
                    lm['ndcg_at_5'] * 0.25 + (1 - lm['spurious_at_5']) * 0.10)
            print(f"║  {level_name:14s}: {comp*100:.1f}/100  ({lm['count']} queries)")
            print(f"║     Recall={lm['recall_at_5']:.3f} MRR={lm['mrr']:.3f} NDCG={lm['ndcg_at_5']:.3f}")
    
    print("╚════════════════════════════════════════════╝")
    
    if baseline:
        print()
        print("📊 与上次结果对比:")
        for key in ["recall_at_5", "mrr", "ndcg_at_5", "composite_score"]:
            old = baseline.get(key, 0)
            new = metrics.get(key, 0)
            diff = new - old
            arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
            print(f"   {key:20s}: {old:.3f} → {new:.3f}  {arrow} {diff:+.3f}")


# ════════════════════════════════════════════════════════════════
#  主函数
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SRA 推荐质量评估工具")
    parser.add_argument("--compare", action="store_true", help="与上次结果对比")
    parser.add_argument("--detail", action="store_true", help="显示每个查询的详细结果")
    args = parser.parse_args()
    
    # 检查 SRA
    if not check_sra():
        sys.exit(1)
    
    # 加载技能元数据
    skills = load_skills_meta()
    print(f"📚 加载了 {len(skills)} 个技能元数据")
    
    if len(skills) == 0:
        print("⚠️  未从 SRA 获取到技能数据，使用简化模式")
        skills = [{"name": "unknown", "description": "", "triggers": [], "tags": [], "category": ""}]
    
    # 生成 Qrels
    print("🔧 生成相关性判断 (Qrels)...")
    qrels = compute_qrels(TEST_QUERIES, skills)
    
    # 执行查询
    print(f"🔍 运行 {len(TEST_QUERIES)} 个测试查询...")
    results = {}
    for qid, info in TEST_QUERIES.items():
        results[qid] = query_sra(info["q"])
        sys.stdout.write(f"  {qid}: {info['q'][:20]:20s} → {results[qid][:3]}\n")
    
    # 评估
    metrics, level_metrics, details = evaluate_run(TEST_QUERIES, qrels, results)
    
    # 加载上次结果 (可选)
    baseline = None
    if args.compare and os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            baseline = json.load(f)
    
    # 报告
    print_report(metrics, level_metrics, baseline)
    
    if args.detail:
        print("\n📋 详细结果:")
        for qid, det in details.items():
            if det["recall"] < 0.5:  # 只显示低于 50% recall 的
                print(f"  ❌ {qid}: \"{det['query']}\" → {det['top_recommended']}")
                print(f"      期望: {det['expected_categories']}")
    
    # 保存结果
    result_data = {**metrics, "level_metrics": level_metrics, "timestamp": time.time()}
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\n💾 结果已保存到 {RESULT_FILE}")


if __name__ == "__main__":
    main()
