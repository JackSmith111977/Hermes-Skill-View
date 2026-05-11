"""
场景记忆持久化模块 — 记录使用历史，优化匹配

v2: 扩展了技能轨迹追踪（view/use/skip）+ 遵循率统计
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional


class SceneMemory:
    """场景记忆管理器"""

    def __init__(self, data_dir: str):
        self.stats_file = os.path.join(data_dir, "skill_usage_stats.json")
        self._cache = None
        self._lock = threading.RLock()

    def load(self) -> Dict:
        """加载场景记忆"""
        with self._lock:
            if self._cache is not None:
                return self._cache

            if not os.path.exists(self.stats_file):
                self._cache = self._default_stats()
                return self._cache

            try:
                with open(self.stats_file) as f:
                    data = json.load(f)
                # 确保新字段存在（向前兼容）
                if "compliance" not in data:
                    data["compliance"] = self._default_compliance()
                self._cache = data
            except (FileNotFoundError, json.JSONDecodeError):
                import logging
                logging.getLogger("sra.memory").debug("场景记忆文件不存在或格式错误，使用默认值")
                self._cache = self._default_stats()

            return self._cache

    def _default_stats(self) -> Dict:
        return {
            "skills": {},
            "scene_patterns": [],
            "total_recommendations": 0,
            "compliance": self._default_compliance(),
        }

    def _default_compliance(self) -> Dict:
        return {
            "total_views": 0,
            "total_uses": 0,
            "total_skips": 0,
            "overall_compliance_rate": 1.0,
            "recent_events": [],
        }

    def save(self):
        """保存场景记忆"""
        with self._lock:
            if self._cache is None:
                return
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)

    # ── 推荐记录（原有） ──────────────────────────────────────────

    def increment_recommendations(self):
        """增加推荐计数"""
        with self._lock:
            stats = self.load()
            stats["total_recommendations"] = stats.get("total_recommendations", 0) + 1
            self.save()

    def record_usage(self, skill_name: str, user_input: str, accepted: bool = True):
        """记录技能使用场景（推荐 → 被采纳/被拒绝）"""
        stats = self.load()
        self._ensure_skill_entry(stats, skill_name)

        s = stats["skills"][skill_name]
        s["total_uses"] += 1

        # 更新接受率
        accepted_count = s.get("accepted_count", 0) + (1 if accepted else 0)
        s["accepted_count"] = accepted_count
        s["acceptance_rate"] = round(accepted_count / s["total_uses"], 2)

        # 记录触发短语
        self._record_trigger_phrase(s, user_input)

        # 更新场景模式
        self._update_scene_patterns(stats, skill_name, user_input)

        self.save()

    # ── 技能轨迹追踪（新增） ──────────────────────────────────────

    def record_view(self, skill_name: str):
        """记录技能被查看（skill_view 调用）"""
        stats = self.load()
        self._ensure_skill_entry(stats, skill_name)

        s = stats["skills"][skill_name]
        s["view_count"] = s.get("view_count", 0) + 1
        s["last_viewed"] = datetime.now().isoformat()

        comp = stats["compliance"]
        comp["total_views"] += 1
        self._push_event(comp, skill_name, "viewed")

        self.save()

    def record_use(self, skill_name: str):
        """记录技能被实际使用（工具调用时触发）"""
        stats = self.load()
        self._ensure_skill_entry(stats, skill_name)

        s = stats["skills"][skill_name]
        s["use_count"] = s.get("use_count", 0) + 1
        s["last_used"] = datetime.now().isoformat()

        comp = stats["compliance"]
        comp["total_uses"] += 1
        self._recalc_compliance(comp)
        self._push_event(comp, skill_name, "used")

        self.save()

    def record_skip(self, skill_name: str, reason: str = ""):
        """记录技能被跳过（推荐了但未使用）"""
        stats = self.load()
        self._ensure_skill_entry(stats, skill_name)

        s = stats["skills"][skill_name]
        s["skip_count"] = s.get("skip_count", 0) + 1

        comp = stats["compliance"]
        comp["total_skips"] += 1
        self._recalc_compliance(comp)
        self._push_event(comp, skill_name, "skipped", metadata={"reason": reason} if reason else {})

        self.save()

    def get_compliance_stats(self) -> Dict:
        """获取遵循率统计"""
        stats = self.load()
        comp = stats.get("compliance", self._default_compliance())
        skills_data = stats.get("skills", {})

        # 按技能维度统计
        per_skill = {}
        for name, s in skills_data.items():
            use_count = s.get("use_count", 0)
            skip_count = s.get("skip_count", 0)
            total = use_count + skip_count
            per_skill[name] = {
                "view_count": s.get("view_count", 0),
                "use_count": use_count,
                "skip_count": skip_count,
                "compliance_rate": round(use_count / total, 2) if total > 0 else None,
                "acceptance_rate": s.get("acceptance_rate"),
            }

        return {
            "summary": {
                "total_views": comp.get("total_views", 0),
                "total_uses": comp.get("total_uses", 0),
                "total_skips": comp.get("total_skips", 0),
                "overall_compliance_rate": comp.get("overall_compliance_rate", 1.0),
            },
            "per_skill": per_skill,
            "recent_events": comp.get("recent_events", [])[-20:],  # 最近 20 条
        }

    # ── 内部工具方法 ──────────────────────────────────────────────

    def _ensure_skill_entry(self, stats: Dict, skill_name: str):
        """确保 skills[skill_name] 存在且有所有字段"""
        if skill_name not in stats["skills"]:
            stats["skills"][skill_name] = {
                "total_uses": 0,
                "last_used": None,
                "trigger_phrases": [],
                "accepted_count": 0,
                "acceptance_rate": 1.0,
                "view_count": 0,
                "use_count": 0,
                "skip_count": 0,
                "last_viewed": None,
            }

    def _record_trigger_phrase(self, s: Dict, user_input: str):
        """记录触发短语"""
        input_lower = user_input.lower().strip()
        if input_lower and input_lower not in [p.lower() for p in s.get("trigger_phrases", [])]:
            if "trigger_phrases" not in s:
                s["trigger_phrases"] = []
            s["trigger_phrases"].append(input_lower[:100])
            if len(s["trigger_phrases"]) > 20:
                s["trigger_phrases"] = s["trigger_phrases"][-20:]

    def _update_scene_patterns(self, stats: Dict, skill_name: str, user_input: str):
        """更新场景模式"""
        import re
        keywords = set()
        chinese = re.findall(r'[\u4e00-\u9fff]+', user_input)
        for ch in chinese:
            if len(ch) >= 2:
                keywords.add(ch)

        for kw in list(keywords)[:5]:
            found = False
            for pattern in stats["scene_patterns"]:
                if kw in pattern["pattern"] or pattern["pattern"] in kw:
                    if skill_name not in pattern["recommended_skills"]:
                        pattern["recommended_skills"].append(skill_name)
                    pattern["hit_count"] += 1
                    found = True
                    break

            if not found:
                stats["scene_patterns"].append({
                    "pattern": kw,
                    "recommended_skills": [skill_name],
                    "hit_count": 1,
                })

    def _recalc_compliance(self, comp: Dict):
        """重新计算整体遵循率"""
        total = comp.get("total_uses", 0) + comp.get("total_skips", 0)
        if total > 0:
            comp["overall_compliance_rate"] = round(comp.get("total_uses", 0) / total, 2)
        else:
            comp["overall_compliance_rate"] = 1.0

    def _push_event(self, comp: Dict, skill_name: str, event_type: str, metadata: Optional[Dict] = None):
        """添加一个最近事件"""
        if "recent_events" not in comp:
            comp["recent_events"] = []
        event = {
            "skill": skill_name,
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            event.update(metadata)
        comp["recent_events"].append(event)
        # 只保留最近 200 条
        if len(comp["recent_events"]) > 200:
            comp["recent_events"] = comp["recent_events"][-200:]

    def get_skill_stats(self, skill_name: str) -> Dict:
        """获取某个技能的使用统计"""
        stats = self.load()
        return stats.get("skills", {}).get(skill_name, {})
