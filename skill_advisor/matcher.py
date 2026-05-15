"""
四维匹配引擎 — 词法 + 语义 + 场景 + 类别
"""

import logging
import json
import os
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("sra.matcher")

# ── SQS 质量评分文件 ──
SQS_SCORES_PATH = os.path.expanduser("~/.sra/data/sqs-scores.json")


class MatchWeight:
    """命名分值常量 — 所有魔法数字语义化"""

    # ── 词法匹配分值 ──
    SYNONYM_EXACT = 25        # 同义词精确匹配（name/trigger/tags）
    SYNONYM_BROAD = 12        # 同义词宽泛匹配（description/match_text）
    NAME_EXACT = 30           # 名称精确匹配
    NAME_PARTIAL = 20         # 名称部分匹配（3+字符）
    TRIGGER_MATCH = 25        # trigger 匹配
    TAG_MATCH = 15            # tag 匹配
    DESC_MATCH = 8            # 描述匹配（2+字符）
    MATCH_TEXT_MATCH = 3      # match_text 匹配

    # ── 语义匹配分值 ──
    SEMANTIC_DESC = 10        # 描述语义匹配
    SEMANTIC_BODY_KW = 5      # body_keywords 语义匹配

    # ── 场景匹配分值 ──
    SCENE_PATTERN_HIT = 3     # 场景模式命中（× hit_count）
    SCENE_USE_FREQ = 2        # 使用频率（× total_uses）

    # ── 类别匹配分值 ──
    CATEGORY_MATCH = 20       # 类别匹配
    TAG_CATEGORY_MATCH = 15   # tag 类别匹配

    # ── 权重配置 ──
    WEIGHT_LEXICAL = 0.40
    WEIGHT_SEMANTIC = 0.25
    WEIGHT_SCENE = 0.20
    WEIGHT_CATEGORY = 0.15

    # ── 修饰因子 ──
    SHORT_QUERY_BOOST = 1.6

    # ── 上限 ──
    MAX_SYNONYM_SCENE = 30    # 场景模式最高加分
    MAX_USE_FREQ_SCORE = 20   # 使用频率最高加分
    MAX_SCORE = 100           # 单维度最高分
    MAX_REASONS = 5           # 返回原因数上限


class SkillMatcher:
    """四维技能匹配引擎"""

    def __init__(self, synonyms: Dict[str, List[str]], no_quality: bool = False):
        self.synonyms = synonyms
        self.no_quality = no_quality
        self._sqs_scores: Dict[str, float] = {}
        self._load_sqs_scores()

    def _load_sqs_scores(self):
        """从 JSON 文件加载 SQS 评分"""
        if not os.path.exists(SQS_SCORES_PATH):
            logger.debug("SQS 评分文件不存在: %s", SQS_SCORES_PATH)
            return
        try:
            with open(SQS_SCORES_PATH) as f:
                data = json.load(f)
            if not data.get("enabled", True):
                logger.debug("SQS 质量加权已禁用 (enabled=false)")
                return
            scores = data.get("scores", {})
            for skill_name, info in scores.items():
                self._sqs_scores[skill_name] = info.get("sqs_score", 50)
            logger.debug("已加载 %d 个 SQS 评分 (no_quality=%s)", len(self._sqs_scores), self.no_quality)
        except Exception as e:
            logger.warning("SQS 评分加载失败: %s", e)

    @staticmethod
    def _quality_modifier(sqs: float) -> float:
        """SQS → 质量权重映射
        SQS ≥ 80:  1.0 (不降权)
        SQS ≥ 60:  0.9 (轻度降权)
        SQS ≥ 40:  0.7 (中度降权)
        SQS < 40:  0.4 (严重降权)
        无评分:    0.5 (中性降权)
        """
        if sqs >= 80:
            return 1.0
        elif sqs >= 60:
            return 0.9
        elif sqs >= 40:
            return 0.7
        else:
            return 0.4

    def score(
        self,
        input_words: Set[str],
        skill: Dict,
        stats: Dict,
    ) -> Tuple[float, Dict, List[str]]:
        """
        对单个 skill 进行四维评分

        Returns:
            (total_score, details_dict, reasons_list)
        """
        lex_score, lex_reasons = self._score_lexical(input_words, skill)
        sem_score = self._score_semantic(input_words, skill)
        sce_score = self._score_scene(input_words, skill["name"], stats)
        cat_score = self._score_category(input_words, skill)

        total = (
            lex_score * MatchWeight.WEIGHT_LEXICAL +
            sem_score * MatchWeight.WEIGHT_SEMANTIC +
            sce_score * MatchWeight.WEIGHT_SCENE +
            cat_score * MatchWeight.WEIGHT_CATEGORY
        )

        # ═══ 短查询自动提升 ═══
        raw_word_count = len([w for w in input_words if len(w) >= 2])
        if raw_word_count <= 2 and lex_score >= 20:
            total = total * MatchWeight.SHORT_QUERY_BOOST

        # ═══ SQS 质量加权 ═══
        if not self.no_quality:
            skill_name = skill.get("name", "")
            sqs = self._sqs_scores.get(skill_name, 50)  # 无评分时默认 50
            modifier = self._quality_modifier(sqs)
            total = total * modifier
            logger.debug(
                "  quality | skill=%s sqs=%.1f modifier=%.1f adjusted=%.1f",
                skill_name, sqs, modifier, total,
            )

        details = {
            "lexical": round(lex_score, 1),
            "semantic": round(sem_score, 1),
            "scene": round(sce_score, 1),
            "category": round(cat_score, 1),
        }

        logger.debug(
            "score | skill=%s lexical=%.1f semantic=%.1f scene=%.1f category=%.1f total=%.1f",
            skill.get("name", "?"), lex_score, sem_score, sce_score, cat_score, total,
        )

        return total, details, lex_reasons[:MatchWeight.MAX_REASONS]

    # ── 词法匹配：拆分为 3 个子函数 ────────────────────────

    def _score_lexical(self, input_words: Set[str], skill: Dict) -> Tuple[float, List[str]]:
        """词法匹配统一入口：聚合 3 个子匹配"""
        score = 0
        reasons: List[str] = []

        s1, r1 = self._score_name(input_words, skill)
        s2, r2 = self._score_triggers(input_words, skill)
        s3, r3 = self._score_description(input_words, skill)

        score += s1 + s2 + s3
        reasons = list(set(r1 + r2 + r3))

        # 同义词反向匹配
        syn_score, syn_reasons = self._score_synonyms(input_words, skill)
        score += syn_score
        reasons.extend(r for r in syn_reasons if r not in reasons)

        logger.debug(
            "  _score_lexical | skill=%s name=%.1f triggers=%.1f desc=%.1f syn=%.1f total=%.1f",
            skill.get("name", "?"), s1, s2, s3, syn_score, min(score, MatchWeight.MAX_SCORE),
        )

        return min(score, MatchWeight.MAX_SCORE), reasons

    def _score_name(self, input_words: Set[str], skill: Dict) -> Tuple[float, List[str]]:
        """子匹配 1：名称匹配"""
        score = 0
        reasons: List[str] = []
        skill_name = skill["name"].lower()
        word_list = self._build_word_list(input_words)

        for w in word_list:
            if len(w) < 2:
                continue

            if w == skill_name or skill_name in w:
                score += MatchWeight.NAME_EXACT
                if "name匹配" not in reasons:
                    reasons.append(f"name匹配'{w}'")

            if len(w) >= 3 and w in skill_name:
                score += MatchWeight.NAME_PARTIAL
                if f"name部分'{w}'" not in reasons:
                    reasons.append(f"name部分'{w}'")

        return score, reasons

    def _score_triggers(self, input_words: Set[str], skill: Dict) -> Tuple[float, List[str]]:
        """子匹配 2：triggers + tags 匹配"""
        score = 0
        reasons: List[str] = []
        triggers = [t.lower() for t in skill.get("triggers", [])]
        tags = [t.lower() for t in skill.get("tags", [])]
        word_list = self._build_word_list(input_words)

        for w in word_list:
            if len(w) < 2:
                continue

            if w in triggers:
                score += MatchWeight.TRIGGER_MATCH
                if f"trigger'{w}'" not in reasons:
                    reasons.append(f"trigger'{w}'")

            if w in tags:
                score += MatchWeight.TAG_MATCH
                if f"tag'{w}'" not in reasons:
                    reasons.append(f"tag'{w}'")

        return score, reasons

    def _score_description(self, input_words: Set[str], skill: Dict) -> Tuple[float, List[str]]:
        """子匹配 3：description + match_text 匹配"""
        score = 0
        reasons: List[str] = []
        desc = skill.get("full_description", "").lower()
        match_text = skill.get("match_text", "").lower()
        word_list = self._build_word_list(input_words)

        for w in word_list:
            if len(w) < 2:
                continue

            if len(w) >= 2 and w in desc:
                score += MatchWeight.DESC_MATCH
                if f"描述'{w}'" not in reasons:
                    reasons.append(f"描述'{w}'")

            if len(w) >= 2 and w in match_text:
                score += MatchWeight.MATCH_TEXT_MATCH

        return score, reasons

    def _score_synonyms(self, input_words: Set[str], skill: Dict) -> Tuple[float, List[str]]:
        """同义词反向匹配"""
        score = 0
        reasons: List[str] = []
        skill_name = skill["name"].lower()
        triggers = [t.lower() for t in skill.get("triggers", [])]
        tags = [t.lower() for t in skill.get("tags", [])]
        desc = skill.get("full_description", "").lower()
        match_text = skill.get("match_text", "").lower()

        for word in input_words:
            if word not in self.synonyms:
                continue
            for syn in self.synonyms[word]:
                syn_lower = syn.lower()
                if len(syn_lower) < 2:
                    continue
                # 精确匹配：在 name/trigger/tags 中
                if syn_lower in skill_name or syn_lower in str(triggers) or syn_lower in str(tags):
                    score += MatchWeight.SYNONYM_EXACT
                    reason = f"同义词'{word}'→'{syn_lower}'"
                    if reason not in reasons:
                        reasons.append(reason)
                # 宽泛匹配：只在 description/match_text 中
                elif syn_lower in desc or syn_lower in match_text:
                    score += MatchWeight.SYNONYM_BROAD
                    reason = f"同义词(描述)'{word}'→'{syn_lower}'"
                    if reason not in reasons:
                        reasons.append(reason)

        return score, reasons

    def _build_word_list(self, input_words: Set[str]) -> List[str]:
        """构建词列表 + 中文组合词拆解"""
        word_list = list(input_words)
        extra_words = set()
        multi_word_syns = set()

        for w in word_list:
            # 中文组合词拆解
            if len(w) >= 3 and all('\u4e00' <= c <= '\u9fff' for c in w):
                for i in range(len(w)):
                    for j in range(2, min(4, len(w) - i + 1)):
                        sub = w[i:i+j]
                        if len(sub) >= 2:
                            extra_words.add(sub)
            # 多词同义词值拆解
            if ' ' in w:
                for part in w.split():
                    if len(part) >= 2:
                        multi_word_syns.add(part.lower())

        word_list.extend(extra_words)
        word_list.extend(multi_word_syns)
        return word_list

    # ── 语义匹配 ──────────────────────────────────────

    def _score_semantic(self, input_words: Set[str], skill: Dict) -> float:
        """语义匹配：基于 description + body_keywords"""
        desc = skill.get("full_description", "").lower()
        body_kws = set(skill.get("body_keywords", []))

        score = 0
        overlap = 0

        for word in input_words:
            w = word.lower()
            if len(w) < 2:
                continue

            if w in desc:
                score += MatchWeight.SEMANTIC_DESC
                overlap += 1
            if w in body_kws:
                score += MatchWeight.SEMANTIC_BODY_KW
                overlap += 1

        total = len(input_words)
        if total > 0:
            ratio = overlap / total
            score = min(int(score * (0.5 + ratio * 0.5)), MatchWeight.MAX_SCORE)

        return score

    def _score_scene(self, input_words: Set[str], skill_name: str, stats: Dict) -> float:
        """场景匹配：基于历史使用模式"""
        scene_patterns = stats.get("scene_patterns", [])

        score = 0
        for pattern in scene_patterns:
            pat = pattern["pattern"].lower()
            for word in input_words:
                if len(word) < 2:
                    continue
                if word.lower() in pat or pat in word.lower():
                    if skill_name in pattern.get("recommended_skills", []):
                        score += min(pattern.get("hit_count", 1) * MatchWeight.SCENE_PATTERN_HIT,
                                     MatchWeight.MAX_SYNONYM_SCENE)

        # 使用频率加分
        skill_stats = stats.get("skills", {}).get(skill_name, {})
        total_uses = skill_stats.get("total_uses", 0)
        score += min(total_uses * MatchWeight.SCENE_USE_FREQ, MatchWeight.MAX_USE_FREQ_SCORE)

        return min(score, MatchWeight.MAX_SCORE)

    def _score_category(self, input_words: Set[str], skill: Dict) -> float:
        """类别匹配：基于 category + tags"""
        score = 0
        category = skill.get("category", "").lower()
        tags = [t.lower() for t in skill.get("tags", [])]

        for word in input_words:
            w = word.lower()
            if len(w) < 2:
                continue
            if w in category:
                score += MatchWeight.CATEGORY_MATCH
            for tag in tags:
                if w in tag or tag in w:
                    score += MatchWeight.TAG_CATEGORY_MATCH

        return min(score, MatchWeight.MAX_SCORE)
