#!/usr/bin/env python3
"""
SRA v2 — 基于实际 Skill 库的推荐质量评估工具（Cranfield 范式）

设计原则:
  - 测试查询全部基于主人实际的 122 个常规 skill 设计
  - Ground truth 直接从 skill 的实际 triggers 自动生成
  - 覆盖各类难度的自然语言查询

运行方式:
    python3 scripts/sra-eval-v2.py                    # 完整评估
    python3 scripts/sra-eval-v2.py --compare          # 与上次结果对比
    python3 scripts/sra-eval-v2.py --detail           # 每个查询的详细结果
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
RESULT_FILE = os.path.expanduser("~/.sra/eval_result_v2.json")
INDEX_FILE = os.path.expanduser("~/.sra/data/skill_full_index.json")
TOP_K = 5


# ════════════════════════════════════════════════════════════════
#  真实 Skill 库 — 基于实际 122 个常规 skill
#  每个查询的 expected_skills 直接基于该 skill 在实际触发词中的匹配度
# ════════════════════════════════════════════════════════════════

TEST_QUERIES = {}

# ── 定义测试查询 (分层设计 L1-L5) ──
# L1: 精确匹配 — 直接用 skill 核心名或 trigger 中的关键词
# L2: 同义映射 — 中文同义词触发或中英桥接  
# L3: 语义理解 — 自然语言任务描述
# L4: 多跳推理 — 需要理解多领域意图
# L5: 噪声抑制 — 不应推荐任何 skill


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
        return [r["skill"] for r in recs[:TOP_K]]
    except Exception as e:
        return []


def load_all_skills():
    """从索引加载全部 skill 数据"""
    try:
        with open(INDEX_FILE) as f:
            raw = f.read()
        start = raw.find('"skills": [')
        arr_start = raw.index('[', start)
        skills = []
        i = arr_start + 1
        while i < len(raw):
            while i < len(raw) and raw[i] in ' \n\r\t':
                i += 1
            if i >= len(raw) or raw[i] == ']':
                break
            if raw[i] == '{':
                depth = 1
                j = i + 1
                while j < len(raw) and depth > 0:
                    if raw[j] == '{': depth += 1
                    elif raw[j] == '}': depth -= 1
                    j += 1
                try:
                    s = json.loads(raw[i:j])
                    skills.append(s)
                except Exception as e:
                    logging.warning("sra-eval-v2: %s", e)
                i = j
            else:
                i += 1
        return skills
    except Exception as e:
        print(f"⚠️  加载索引失败: {e}")
        return []


def build_skill_map(skills):
    """构建 skill name -> info 映射，过滤掉 bmad/gds 系列"""
    smap = {}
    for s in skills:
        name = s["name"]
        if name.startswith("bmad-") or name.startswith("gds-") or name.startswith("skill-") or name == "{setup-skill-name}":
            continue
        smap[name] = {
            "triggers": s.get("triggers", []),
            "description": s.get("description", ""),
            "tags": s.get("tags", []),
        }
    return smap


def generate_test_queries(skill_map):
    """
    基于真实的 skill 库自动生成测试查询。
    
    L1 精确匹配: 直接用 skill 核心名作查询
    L2 同义映射: 用中文同义表达（如 "幻灯片" -> pptx-guide）
    L3 语义理解: 自然语言任务描述
    L4 多跳推理: 组合意图
    L5 噪声抑制: 完全无关的查询
    """
    queries = {}
    all_skill_names = list(skill_map.keys())
    
    # ── L1: 精确匹配 (20 query) ──
    l1_pairs = [
        # 基于 skill 核心名直接查询
        ("feishu", "feishu", "飞书"),
        ("web-access", "web-access", "联网搜索"),
        ("financial-analyst", "financial-analyst", "股票分析"),
        ("pptx-guide", "pptx-guide", "PPT"),
        ("pdf-layout", "pdf-layout", "PDF"),
        ("markdown-guide", "markdown-guide", "markdown"),
        ("mermaid-guide", "mermaid-guide", "mermaid"),
        ("latex-guide", "latex-guide", "latex"),
        ("xlsx-guide", "xlsx-guide", "excel"),
        ("docx-guide", "docx-guide", "docx"),
        ("epub-guide", "epub-guide", "epub"),
        ("html-guide", "html-guide", "html"),
        ("youtube-content", "youtube-content", "youtube"),
        ("news-briefing", "news-briefing", "新闻简报"),
        ("arxiv", "arxiv", "arxiv"),
        ("linux-ops-guide", "linux-ops-guide", "linux运维"),
        ("git-advanced-ops", "git-advanced-ops", "git"),
        ("image-generation", "image-generation", "生图"),
        ("learning", "learning", "学习"),
        ("sra-agent", "sra-agent", "技能推荐"),
    ]
    
    for i, (qid, exp_skill, query_text) in enumerate(l1_pairs):
        queries[f"L1_{i:02d}_{exp_skill}"] = {
            "q": query_text,
            "expected": [exp_skill],
        }
    
    # ── L2: 同义映射 (20 query) ──
    l2_pairs = [
        ("幻灯片", ["pptx-guide", "powerpoint"]),
        ("word文档", ["docx-guide"]),
        ("做表格", ["xlsx-guide"]),
        ("查资料", ["web-access"]),
        ("搜索网页", ["web-access"]),
        ("爬网页", ["web-access"]),
        ("发微信", ["feishu"]),  # 飞书是主要 IM
        ("查看股票行情", ["financial-analyst"]),
        ("分析大盘", ["financial-analyst"]),
        ("画流程图", ["mermaid-guide"]),
        ("画架构图", ["architecture-diagram"]),
        ("生成音乐", ["audiocraft-audio-generation", "heartmula"]),
        ("pdf生成", ["pdf-layout-weasyprint", "pdf-layout-reportlab", "pdf-layout"]),
        ("开发新功能", ["bmad-method"]),
        ("配置代理", ["proxy-finder", "proxy-monitor", "clash-config"]),
        ("看论文", ["arxiv"]),
        ("博客订阅", ["blogwatcher"]),
        ("动漫推荐", ["bangumi-recommender"]),
        ("ai新闻", ["ai-trends"]),
        ("系统监控", ["system-health-check", "proxy-monitor", "linux-ops-guide"]),
    ]
    
    for i, (query_text, expected) in enumerate(l2_pairs):
        qid = f"L2_{i:02d}_{expected[0]}"
        queries[qid] = {
            "q": query_text,
            "expected": expected,
        }
    
    # ── L3: 语义理解 — 自然语言任务描述 (15 query) ──
    l3_pairs = [
        ("帮我把笔记整理成演讲用的幻灯片", ["pptx-guide", "powerpoint"]),
        ("帮我写一份本周的工作总结报告", ["markdown-guide", "writing-styles-guide"]),
        ("帮我看看服务器为什么连不上了", ["linux-ops-guide", "system-health-check"]),
        ("写一个python脚本处理数据", ["python-env-guide", "codex"]),
        ("理解一下这个代码库的结构", ["codebase-inspection"]),
        ("每天自动给我推送新闻", ["news-briefing", "smart-broadcast"]),
        ("把这个数据做成图表展示", ["xlsx-guide", "pptx-guide"]),
        ("发一个文件到群里", ["feishu-send-file", "feishu"]),
        ("把代码审查一下看看有没有问题", ["github-code-review", "requesting-code-review"]),
        ("帮我定个时每天提醒我喝水", ["smart-broadcast", "cronjob"]),
        ("我想了解最新的AI技术趋势", ["ai-trends", "learning"]),
        ("这个bug反复出现，帮我彻底排查", ["systematic-debugging", "problem-solving-sherlock"]),
        ("我想做个调查问卷收集反馈", ["doc-design"]),
        ("把我的博客内容做成电子书", ["epub-guide", "markdown-guide"]),
        ("这个设计好不好看评价一下", ["visual-aesthetics"]),
    ]
    
    for i, (query_text, expected) in enumerate(l3_pairs):
        qid = f"L3_{i:02d}_{expected[0]}"
        queries[qid] = {
            "q": query_text,
            "expected": expected,
        }
    
    # ── L4: 多跳推理 — 跨领域组合 (10 query) ──
    l4_pairs = [
        ("每天爬取ai新闻生成pdf报告推送给我", ["news-briefing", "web-access", "pdf-layout-weasyprint", "smart-broadcast"]),
        ("帮我分析这只股票的历史数据做个PPT", ["financial-analyst", "pptx-guide"]),
        ("翻译这篇论文并整理成笔记", ["arxiv", "markdown-guide", "note-taking"]),
        ("把服务器监控数据做成可视化图表每天发飞书", ["linux-ops-guide", "smart-broadcast", "pptx-guide", "feishu"]),
        ("生成一张架构图并嵌入到PDF文档中", ["architecture-diagram", "pdf-layout-reportlab"]),
        ("用Mermaid画个流程图然后用WeasyPrint转成PDF", ["mermaid-guide", "pdf-layout-weasyprint"]),
        ("看这个YouTube视频总结要点，然后加入学习笔记", ["youtube-content", "note-taking", "learning"]),
        ("创建一个反映GitHub仓库最新Issue的飞书看板", ["github-issues", "feishu", "smart-broadcast"]),
        ("把excel数据做成图表，再生成PPT展示", ["xlsx-guide", "pptx-guide"]),
        ("监控代理节点状态，异常时发飞书通知", ["proxy-monitor", "feishu", "smart-broadcast"]),
    ]
    
    for i, (query_text, expected) in enumerate(l4_pairs):
        qid = f"L4_{i:02d}"
        queries[qid] = {
            "q": query_text,
            "expected": expected,
        }
    
    # ── L5: 噪声抑制 (5 query) ──
    l5_noise = [
        "你好",
        "今天天气怎么样",
        "谢谢",
        "再见",
        "人生的意义是什么",
    ]
    
    for i, query_text in enumerate(l5_noise):
        queries[f"L5_{i:02d}"] = {
            "q": query_text,
            "expected": [],  # 不应推荐任何 skill
        }
    
    return queries


def compute_qrels(test_queries, skill_map):
    """
    基于真实 skill 的 triggers 和 description，自动计算每个查询的 Qrels。
    
    对每个查询的 expected 列表中的 skill，从 skill_map 中找出真正的 trigger 匹配度。
    """
    qrels = {}
    
    for qid, info in test_queries.items():
        expected = info.get("expected", [])
        query_text = info["q"].lower()
        rels = {}
        
        if not expected:
            # L5: 不应推荐任何 skill
            qrels[qid] = {}
            continue
        
        # 给 expected 中的 skill 分配相关性分数
        for exp_name in expected:
            if exp_name in skill_map:
                s = skill_map[exp_name]
                rels[exp_name] = 2.0  # 高相关性
                
                # 如果 trigger 中有完全匹配查询词的，加额外分数
                for t in s["triggers"]:
                    t_low = t.lower()
                    if query_text in t_low or t_low in query_text:
                        rels[exp_name] = 3.0  # trigger 精确匹配
                    elif any(word in t_low for word in query_text.split()):
                        rels[exp_name] = max(rels[exp_name], 1.5)
            else:
                # skill 不在当前 skill 库中（如 BMad skill），标记为不存在
                pass
        
        # 对 skill_map 中其他可能相关的 skill 做泛匹配（防止漏报）
        query_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]{2,}', query_text))
        for name, s in skill_map.items():
            if name in rels:
                continue  # 已经标记过
            
            relevance = 0.0
            
            # 检查 trigger 中是否包含查询词
            for t in s["triggers"]:
                t_low = t.lower()
                # 精确 trigger 匹配
                if t_low == query_text:
                    relevance = max(relevance, 2.0)
                elif query_text in t_low:
                    relevance = max(relevance, 1.5)
                elif t_low in query_text:
                    relevance = max(relevance, 1.0)
                # 单词级别匹配
                for word in query_words:
                    if len(word) >= 3 and word in t_low:
                        relevance = max(relevance, 0.3)
            
            if relevance > 0:
                rels[name] = relevance
            else:
                # 描述中匹配
                desc = s["description"].lower()
                match_count = sum(1 for word in query_words if len(word) >= 3 and word in desc)
                if match_count >= 2:
                    rels[name] = 0.3  # 弱相关
        
        qrels[qid] = rels
    
    return qrels


def evaluate_run(test_queries, qrels, results):
    """对一次运行结果计算所有指标"""
    total_recall = 0.0
    total_mrr = 0.0
    total_ndcg = 0.0
    total_spurious = 0.0
    query_count = len(test_queries)
    
    level_results = defaultdict(lambda: {
        "recall": [], "mrr": [], "ndcg": [], "spurious": [], "count": 0
    })
    
    details = {}
    
    for qid in sorted(test_queries.keys()):
        info = test_queries[qid]
        level = qid.split("_")[0]
        level_results[level]["count"] += 1
        
        qrel = qrels.get(qid, {})
        run = results.get(qid, [])
        
        # 找出相关 skill（rel >= 1.0 的强相关）
        relevant_skills = {s for s, r in qrel.items() if r >= 1.0}
        # 弱相关也计为部分相关
        weak_relevant = {s for s, r in qrel.items() if 0 < r < 1.0}
        all_relevant = relevant_skills | weak_relevant
        
        relevant_count = len(all_relevant)
        
        # ── Recall@K ──
        if relevant_count > 0:
            retrieved_relevant = sum(1 for s in run[:TOP_K] if s in all_relevant)
            recall = retrieved_relevant / relevant_count
        else:
            recall = 1.0  # 无相关skill时（L5）视为完美
        
        # ── MRR ──
        mrr = 0.0
        for i, s in enumerate(run[:TOP_K]):
            if s in all_relevant:
                mrr = 1.0 / (i + 1)
                break
        
        # ── NDCG@K ──
        dcg = 0.0
        idcg = 0.0
        for i, s in enumerate(run[:TOP_K]):
            rel = qrel.get(s, 0.0)
            if rel >= 1.0:
                rel_score = 2.0
            elif rel > 0:
                rel_score = 1.0
            else:
                rel_score = 0.0
            dcg += rel_score / (i + 1)
        
        ideal_rels = sorted([v for v in qrel.values()], reverse=True)
        for i in range(min(TOP_K, len(ideal_rels))):
            rel_score = 2.0 if ideal_rels[i] >= 1.0 else (1.0 if ideal_rels[i] > 0 else 0.0)
            idcg += rel_score / (i + 1)
        
        ndcg = dcg / idcg if idcg > 0 else 0.0
        
        # ── Spurious@K (推荐了无关skill的比例) ──
        if len(run) > 0:
            spurious_count = sum(1 for s in run[:TOP_K] if s not in all_relevant)
            spurious = spurious_count / min(len(run), TOP_K)
        else:
            spurious = 1.0  # 没有推荐也算假正
        
        total_recall += recall
        total_mrr += mrr
        total_ndcg += ndcg
        total_spurious += spurious
        
        level_results[level]["recall"].append(recall)
        level_results[level]["mrr"].append(mrr)
        level_results[level]["ndcg"].append(ndcg)
        level_results[level]["spurious"].append(spurious)
        
        expected = info.get("expected", [])
        
        details[qid] = {
            "query": info["q"],
            "level": level,
            "top_recommended": run[:3],
            "expected": expected,
            "matched": [s for s in run[:TOP_K] if s in all_relevant],
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
    print()
    print("╔════════════════════════════════════════════╗")
    print("║ SRA v2 — 基于实际 Skill 库的评估报告       ║")
    print("╠════════════════════════════════════════════╣")
    print(f"║  综合得分:       {metrics['composite_score']*100:.1f}/100")
    print("║")
    print(f"║  Recall@5:       {metrics['recall_at_5']:.3f}  " + color_score(metrics['recall_at_5']))
    print(f"║  MRR:            {metrics['mrr']:.3f}  " + color_score(metrics['mrr']))
    print(f"║  NDCG@5:         {metrics['ndcg_at_5']:.3f}  " + color_score(metrics['ndcg_at_5']))
    print(f"║  Spurious@5:     {metrics['spurious_at_5']:.3f}  (越低越好)")
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


def print_detail(results, qrels, test_queries):
    """打印低分查询详情"""
    print("\n📋 需要改进的查询 (Recall < 0.5):")
    for qid in sorted(results.keys()):
        run = results[qid]
        info = test_queries[qid]
        qrel = qrels.get(qid, {})
        relevant = {s for s, r in qrel.items() if r >= 1.0}
        
        if relevant:
            matched = sum(1 for s in run[:TOP_K] if s in relevant)
            recall = matched / len(relevant)
            if recall < 0.5:
                print(f"  ❌ {qid}: \"{info['q']}\"")
                print(f"      期望→ {info['expected']}")
                print(f"      命中→ {[s for s in run[:3] if s in relevant]}")
                print(f"      推荐→ {run[:3]}")


def main():
    parser = argparse.ArgumentParser(description="SRA v2 — 基于实际 Skill 库的推荐质量评估工具")
    parser.add_argument("--compare", action="store_true", help="与上次结果对比")
    parser.add_argument("--detail", action="store_true", help="显示每个查询的详细结果")
    args = parser.parse_args()
    
    # 检查 SRA
    if not check_sra():
        sys.exit(1)
    
    # 加载技能元数据
    all_skills = load_all_skills()
    skill_map = build_skill_map(all_skills)
    print(f"📚 加载了 {len(skill_map)} 个常规 skill（过滤了 BMad/GDS 系列）")
    
    # 基于真实 skill 库生成测试查询
    test_queries = generate_test_queries(skill_map)
    print(f"🔧 生成了 {len(test_queries)} 个基于真实 skill 库的测试查询")
    
    # 统计各层数量
    level_counts = defaultdict(int)
    for qid in test_queries:
        level_counts[qid.split("_")[0]] += 1
    for level in ["L1", "L2", "L3", "L4", "L5"]:
        print(f"   {level}: {level_counts[level]} queries")
    
    # 生成 Qrels
    print("🔧 生成相关性判断 (Qrels)...")
    qrels = compute_qrels(test_queries, skill_map)
    
    # 执行查询
    print(f"🔍 运行 {len(test_queries)} 个测试查询...")
    results = {}
    for qid in sorted(test_queries.keys()):
        info = test_queries[qid]
        results[qid] = query_sra(info["q"])
        sys.stdout.write(f"  {qid}: {info['q'][:25]:25s} → {results[qid][:3]}\n")
        sys.stdout.flush()
    
    # 评估
    metrics, level_metrics, details = evaluate_run(test_queries, qrels, results)
    
    # 加载上次结果 (可选)
    baseline = None
    if args.compare and os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            baseline = json.load(f)
    
    # 报告
    print_report(metrics, level_metrics, baseline)
    
    if args.detail:
        print_detail(results, qrels, test_queries)
    
    # 保存结果
    result_data = {
        **metrics, 
        "level_metrics": level_metrics, 
        "query_count": len(test_queries),
        "timestamp": time.time(),
    }
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\n💾 结果已保存到 {RESULT_FILE}")


if __name__ == "__main__":
    main()
