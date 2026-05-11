"""SceneMemory 单元测试 — 技能轨迹追踪 + 遵循率统计"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.memory import SceneMemory


class TestSceneMemory:
    """场景记忆管理器测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mem = SceneMemory(self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── 基础加载/保存 ──

    def test_load_empty_dir_returns_defaults(self):
        """空目录应返回默认统计结构"""
        stats = self.mem.load()
        assert "skills" in stats
        assert "scene_patterns" in stats
        assert "compliance" in stats
        assert stats["total_recommendations"] == 0
        assert stats["compliance"]["overall_compliance_rate"] == 1.0

    def test_save_and_reload_preserves_data(self):
        """保存后重载应保留数据"""
        self.mem.record_view("my-skill")
        assert self.mem._cache is not None
        # 清缓存强制重载
        self.mem._cache = None
        stats = self.mem.load()
        assert stats["skills"]["my-skill"]["view_count"] == 1

    def test_load_invalid_json_returns_defaults(self):
        """损坏的 JSON 应返回默认值"""
        with open(self.mem.stats_file, "w") as f:
            f.write("not json")
        stats = self.mem.load()
        assert stats["total_recommendations"] == 0

    def test_load_missing_compliance_field_adds_default(self):
        """旧数据缺少 compliance 字段应自动补充"""
        with open(self.mem.stats_file, "w") as f:
            json.dump({"skills": {}, "scene_patterns": [], "total_recommendations": 0}, f)
        self.mem._cache = None
        stats = self.mem.load()
        assert "compliance" in stats
        assert stats["compliance"]["total_views"] == 0

    # ── record_view / record_use / record_skip ──

    def test_record_view_increments_count(self):
        self.mem.record_view("skill-a")
        s = self.mem.get_skill_stats("skill-a")
        assert s["view_count"] == 1

    def test_record_view_twice(self):
        self.mem.record_view("skill-a")
        self.mem.record_view("skill-a")
        s = self.mem.get_skill_stats("skill-a")
        assert s["view_count"] == 2

    def test_record_use_increments_count(self):
        self.mem.record_use("skill-a")
        s = self.mem.get_skill_stats("skill-a")
        assert s["use_count"] == 1
        assert s["last_used"] is not None

    def test_record_skip_increments_count(self):
        self.mem.record_skip("skill-b", reason="not relevant")
        s = self.mem.get_skill_stats("skill-b")
        assert s["skip_count"] == 1

    def test_record_skip_with_reason(self):
        """skip 记录应包含 reason"""
        self.mem.record_skip("skill-b", reason="not relevant")
        comp = self.mem.load()["compliance"]
        events = [e for e in comp["recent_events"] if e["type"] == "skipped"]
        assert any(e.get("reason") == "not relevant" for e in events)

    # ── 遵循率计算 ──

    def test_compliance_rate_100_percent(self):
        """全使用无跳过 → 遵循率 100%"""
        self.mem.record_use("s1")
        stats = self.mem.get_compliance_stats()
        assert stats["summary"]["overall_compliance_rate"] == 1.0

    def test_compliance_rate_mixed(self):
        """混合使用和跳过 → 正确计算遵循率"""
        self.mem.record_use("s1")
        self.mem.record_use("s2")
        self.mem.record_skip("s3")
        stats = self.mem.get_compliance_stats()
        # 2 use, 1 skip → rate = 2/3 ≈ 0.67
        assert stats["summary"]["total_uses"] == 2
        assert stats["summary"]["total_skips"] == 1
        assert stats["summary"]["overall_compliance_rate"] == round(2/3, 2)

    def test_compliance_rate_no_data(self):
        """无数据 → 遵循率 1.0"""
        stats = self.mem.get_compliance_stats()
        assert stats["summary"]["overall_compliance_rate"] == 1.0

    # ── per_skill 统计 ──

    def test_per_skill_stats(self):
        self.mem.record_view("s1")
        self.mem.record_use("s1")
        self.mem.record_skip("s2")
        stats = self.mem.get_compliance_stats()
        assert stats["per_skill"]["s1"]["view_count"] == 1
        assert stats["per_skill"]["s1"]["use_count"] == 1
        assert stats["per_skill"]["s2"]["skip_count"] == 1
        assert stats["per_skill"]["s1"]["compliance_rate"] == 1.0

    def test_per_skill_only_skipped_has_rate_zero(self):
        """仅跳过 → 遵循率 0.0"""
        self.mem.record_skip("s1")
        stats = self.mem.get_compliance_stats()
        assert stats["per_skill"]["s1"]["compliance_rate"] == 0.0

    def test_per_skill_only_viewed_has_rate_none(self):
        """仅查看未使用也未跳过 → rate 为 None"""
        self.mem.record_view("s1")
        stats = self.mem.get_compliance_stats()
        assert stats["per_skill"]["s1"]["compliance_rate"] is None

    # ── 旧 API 向后兼容 ──

    def test_record_usage_backward_compat(self):
        """旧 record_usage 仍可正常工作"""
        self.mem.record_usage("old-skill", "hello world", accepted=True)
        s = self.mem.get_skill_stats("old-skill")
        assert s["total_uses"] == 1
        assert s["accepted_count"] == 1
        assert s["view_count"] == 0  # 新字段默认为 0

    def test_record_usage_rejected(self):
        """记录被拒绝的推荐"""
        self.mem.record_usage("old-skill", "test", accepted=False)
        s = self.mem.get_skill_stats("old-skill")
        assert s["accepted_count"] == 0
        assert s["acceptance_rate"] == 0.0

    def test_mixed_new_and_old_api(self):
        """新旧 API 混合使用不冲突"""
        self.mem.record_view("hybrid")
        self.mem.record_usage("hybrid", "test query", accepted=True)
        s = self.mem.get_skill_stats("hybrid")
        assert s["view_count"] == 1
        assert s["total_uses"] == 1  # from record_usage
        assert s["use_count"] == 0   # from record_use (different counter)

    # ── get_skill_stats ──

    def test_get_skill_stats_existing(self):
        self.mem.record_view("existing")
        s = self.mem.get_skill_stats("existing")
        assert s["view_count"] == 1

    def test_get_skill_stats_non_existing(self):
        """不存在的技能应返回空字典"""
        s = self.mem.get_skill_stats("nope")
        assert s == {}

    # ── 最近事件 ──

    def test_recent_events_contains_recorded_actions(self):
        self.mem.record_view("v1")
        self.mem.record_use("u1")
        self.mem.record_skip("s1")
        stats = self.mem.get_compliance_stats()
        event_types = [e["type"] for e in stats["recent_events"]]
        assert "viewed" in event_types
        assert "used" in event_types
        assert "skipped" in event_types

    def test_recent_events_limited_to_200(self):
        """最近事件不应超过 200 条"""
        for i in range(250):
            self.mem.record_view(f"skill-{i}")
        stats = self.mem.get_compliance_stats()
        assert len(stats["recent_events"]) <= 200

    # ── 场景模式 ──

    def test_scene_pattern_created(self):
        self.mem.record_usage("my-skill", "我要写代码", accepted=True)
        stats = self.mem.load()
        assert len(stats["scene_patterns"]) > 0
        assert any("写代码" in p["pattern"] for p in stats["scene_patterns"])

    def test_scene_pattern_existing_hit(self):
        """同一关键词再次触发应增加命中计数"""
        self.mem.record_usage("s1", "写代码", accepted=True)
        self.mem.record_usage("s2", "写代码工具", accepted=True)
        stats = self.mem.load()
        for p in stats["scene_patterns"]:
            if "写代码" in p["pattern"]:
                assert p["hit_count"] >= 2
                break
        else:
            assert False, "未找到 '写代码' 模式"

    # ── 触发短语 ──

    def test_trigger_phrase_recorded(self):
        self.mem.record_usage("s1", "test query", accepted=True)
        s = self.mem.get_skill_stats("s1")
        assert "test query" in s.get("trigger_phrases", [])

    def test_trigger_phrases_limited_to_20(self):
        for i in range(25):
            self.mem.record_usage("s1", f"query {i}", accepted=True)
        s = self.mem.get_skill_stats("s1")
        assert len(s.get("trigger_phrases", [])) <= 20

    # ── 多技能场景 ──

    def test_multiple_skills_independent_counts(self):
        self.mem.record_view("a")
        self.mem.record_view("a")
        self.mem.record_use("a")
        self.mem.record_view("b")
        self.mem.record_skip("c")
        stats = self.mem.get_compliance_stats()
        assert stats["per_skill"]["a"]["view_count"] == 2
        assert stats["per_skill"]["a"]["use_count"] == 1
        assert stats["per_skill"]["b"]["view_count"] == 1
        assert stats["per_skill"]["c"]["skip_count"] == 1
        assert stats["summary"]["total_views"] == 3
        assert stats["summary"]["total_uses"] == 1
        assert stats["summary"]["total_skips"] == 1
