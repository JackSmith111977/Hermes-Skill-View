"""
SRA - Skill Runtime Advisor
让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。

主入口：SkillAdvisor 类
"""

import os
import time
from typing import Dict, List

from .indexer import SkillIndexer
from .matcher import SkillMatcher
from .memory import SceneMemory
from .synonyms import SYNONYMS


class SkillAdvisor:
    """技能推荐引擎主类"""

    # 推荐阈值
    THRESHOLD_STRONG = 80  # 强推荐：自动加载
    THRESHOLD_WEAK = 40    # 弱推荐：附加提示

    def __init__(self, skills_dir: str = None, data_dir: str = None, no_quality: bool = False):
        """
        初始化 SRA 引擎

        Args:
            skills_dir: 技能目录路径。默认为 ~/.hermes/skills
            data_dir: 数据持久化目录。默认为 ~/.sra/data
            no_quality: 禁用 SQS 质量加权
        """
        self.skills_dir = skills_dir or os.path.expanduser("~/.hermes/skills")
        self.data_dir = data_dir or os.path.expanduser(
            os.environ.get("SRA_DATA_DIR", "~/.sra/data")
        )

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

        # 初始化子模块
        self.indexer = SkillIndexer(self.skills_dir, self.data_dir)
        self.matcher = SkillMatcher(SYNONYMS, no_quality=no_quality)
        self.memory = SceneMemory(self.data_dir)

        # 懒加载索引
        self._index_loaded = False

    def _ensure_index(self):
        """确保索引已加载"""
        if not self._index_loaded:
            self.indexer.load_or_build()
            self._index_loaded = True

    def refresh_index(self) -> int:
        """强制刷新技能索引"""
        count = self.indexer.build()
        self._index_loaded = True
        return count

    def build_contract(self, query: str, scored: List[Dict]) -> Dict:
        """为推荐结果构建技能契约

        Args:
            query: 用户原始输入
            scored: 已评分排序的技能列表（带 .score 字段）

        Returns:
            {
                "task_type": str,              # 推测的任务类型
                "required_skills": [str],       # 强推荐（score >= 80）
                "optional_skills": [str],       # 可选推荐（40 <= score < 80）
                "confidence": str,              # high / medium / low
                "summary": str,                 # 自然语言描述
            }
        """
        required = [s["skill"] for s in scored if s.get("score", 0) >= self.THRESHOLD_STRONG]
        optional = [s["skill"] for s in scored if self.THRESHOLD_WEAK <= s.get("score", 0) < self.THRESHOLD_STRONG]

        # 推测任务类型：取最高分技能的 category
        categories = {s.get("category", "") for s in scored if s.get("category")}
        task_type = next(iter(categories)) if len(categories) == 1 else (", ".join(categories) if categories else "general")

        # 置信度
        max_score = max((s.get("score", 0) for s in scored), default=0)
        if max_score >= 80:
            confidence = "high"
        elif max_score >= 60:
            confidence = "medium"
        else:
            confidence = "low"

        # 自然语言总结
        parts = []
        if required:
            parts.append(f"必须加载: {', '.join(required)}")
        if optional:
            parts.append(f"建议参考: {', '.join(optional)}")
        summary = f"任务类型「{task_type}」— " + ("; ".join(parts) if parts else "无特定技能推荐")

        return {
            "task_type": task_type,
            "required_skills": required,
            "optional_skills": optional,
            "confidence": confidence,
            "summary": summary,
        }

    def recommend(self, query: str, top_k: int = 3, no_quality: bool = False) -> Dict:
        """
        推荐匹配技能

        Args:
            query: 用户输入
            top_k: 返回 top-k 结果
            no_quality: 禁用 SQS 质量加权

        Returns:
            {recommendations, processing_ms, skills_scanned, query, contract}
        """
        if no_quality:
            self.matcher.no_quality = True

        self._ensure_index()
        start = time.time()

        skills = self.indexer.get_skills()
        stats = self.memory.load()

        # 提取输入关键词
        input_words = self.indexer.extract_keywords(query)
        input_expanded = self.indexer.expand_with_synonyms(input_words)

        if not input_expanded:
            return {"recommendations": [], "processing_ms": 0, "skills_scanned": 0, "query": query}

        # 对所有 skill 评分
        scored = []
        for skill in skills:
            total, details, reasons = self.matcher.score(
                input_expanded, skill, stats
            )

            if total >= self.THRESHOLD_WEAK:
                scored.append({
                    "skill": skill["name"],
                    "description": skill.get("description", "")[:120],
                    "category": skill.get("category", ""),
                    "score": round(total, 1),
                    "confidence": "high" if total >= self.THRESHOLD_STRONG else "medium",
                    "reasons": reasons[:3],
                    "details": details,
                })

        # 排序取 top-k
        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:top_k]

        # 更新推荐计数
        self.memory.increment_recommendations()

        # 🆕 构建契约
        contract = self.build_contract(query, scored)

        elapsed = round((time.time() - start) * 1000, 1)

        return {
            "recommendations": top,
            "processing_ms": elapsed,
            "skills_scanned": len(skills),
            "query": query,
            "contract": contract,       # 🆕
        }

    def recheck(self, conversation_summary: str, loaded_skills: List[str] = None,
                 top_k: int = 5) -> Dict:
        """
        长任务上下文漂移重检

        在长任务执行过程中定期调用，检测上下文是否漂移，
        以及是否有新的技能应该被加载。

        Args:
            conversation_summary: 当前对话摘要
            loaded_skills: 已经加载的技能名称列表
            top_k: 推荐 top-k 技能

        Returns:
            {
                "has_drift": bool,           # 是否检测到漂移
                "missing_skills": [...],      # 推荐但未加载的技能
                "drift_score": float,         # 漂移程度 (0-1)
                "recommendations": [...],      # 完整推荐结果
                "loaded_skills_count": int,
                "processing_ms": float,
            }
        """
        # 1. 运行推荐算法
        result = self.recommend(conversation_summary, top_k=top_k)
        recs = result.get("recommendations", [])
        elapsed = result.get("processing_ms", 0)

        # 2. 对比已加载技能
        loaded = loaded_skills or []
        loaded_lower = [s.lower() for s in loaded]
        [r["skill"].lower() for r in recs]

        missing = [r for r in recs if r["skill"].lower() not in loaded_lower]

        # 3. 计算漂移分数
        if recs:
            drift_score = round(len(missing) / len(recs), 2)
        else:
            drift_score = 0.0
        has_drift = len(missing) > 0 and drift_score >= 0.2

        # 4. 记录推荐
        if has_drift:
            self.memory.increment_recommendations()

        return {
            "has_drift": has_drift,
            "drift_score": drift_score,
            "missing_skills": missing,
            "recommendations": recs,
            "loaded_skills_count": len(loaded),
            "processing_ms": elapsed,
            "query": conversation_summary[:100],
        }

    def record_usage(self, skill_name: str, user_input: str, accepted: bool = True):
        """记录技能使用场景"""
        self.memory.record_usage(skill_name, user_input, accepted)

    def record_view(self, skill_name: str):
        """记录技能被查看"""
        self.memory.record_view(skill_name)

    def record_use(self, skill_name: str):
        """记录技能被使用"""
        self.memory.record_use(skill_name)

    def record_skip(self, skill_name: str, reason: str = ""):
        """记录技能被跳过"""
        self.memory.record_skip(skill_name, reason)

    def get_compliance_stats(self) -> Dict:
        """获取遵循率统计"""
        return self.memory.get_compliance_stats()

    def show_stats(self) -> Dict:
        """获取统计信息"""
        self._ensure_index()
        stats = self.memory.load()
        skills = self.indexer.get_skills()

        return {
            "total_skills": len(skills),
            "total_recommendations": stats.get("total_recommendations", 0),
            "scene_patterns": len(stats.get("scene_patterns", [])),
            "skills_with_stats": len(stats.get("skills", {})),
            "memory": stats,
        }

    def analyze_coverage(self) -> Dict:
        """
        分析 SRA 对技能目录的覆盖率
        返回：每个 skill 是否能被 SRA 的 trigger 机制识别
        """
        self._ensure_index()
        skills = self.indexer.get_skills()
        stats = self.memory.load()

        results = []
        covered = 0
        for skill in skills:
            # 用 skill 自己的 triggers 作为测试查询
            triggers = skill.get("triggers", [])
            name = skill.get("name", "")

            # 构造测试查询
            test_queries = []
            if triggers:
                test_queries.extend(triggers[:3])
            # 用 name 作为后备查询
            test_queries.append(name.replace("-", " "))

            # 测试所有查询
            max_score = 0
            for q in test_queries:
                if not q:
                    continue
                input_words = self.indexer.extract_keywords(q)
                input_expanded = self.indexer.expand_with_synonyms(input_words)
                if input_expanded:
                    total, _, _ = self.matcher.score(input_expanded, skill, stats)
                    max_score = max(max_score, total)

            is_covered = max_score >= self.THRESHOLD_WEAK
            if is_covered:
                covered += 1

            results.append({
                "name": skill["name"],
                "category": skill.get("category", ""),
                "has_triggers": len(triggers) > 0,
                "max_score": round(max_score, 1),
                "covered": is_covered,
            })

        return {
            "total": len(skills),
            "covered": covered,
            "coverage_rate": round(covered / len(skills) * 100, 1) if skills else 0,
            "not_covered": [r for r in results if not r["covered"]],
            "details": results,
        }
