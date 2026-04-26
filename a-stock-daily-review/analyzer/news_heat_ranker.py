"""热点综合排名算法"""
import jieba
import logging
import re
import math

jieba.setLogLevel(logging.WARNING)

from collections import defaultdict
from typing import List, Tuple

from models.news import NewsItem, CompositeNewsRank
from logger import logger


SOURCE_WEIGHTS = {
    "微博": 1.0, "知乎": 0.9, "哔哩哔哩": 0.7, "百度热搜": 1.0, "华尔街见闻": 0.9,
}

STOPWORDS = {
    "的", "了", "是", "在", "和", "与", "或", "等", "被", "把", "将",
    "这", "那", "就", "也", "都", "而", "及", "着", "或", "一个", "没有",
    "我们", "你们", "他们", "它", "她", "他", "这个", "那个", "什么", "怎么",
    "如何", "为什么", "哪", "哪个", "哪些", "多少", "几", "之", "为", "以",
    "其", "可", "但", "却", "又", "还", "至", "使", "由", "从", "到", "于"
}

SIMILARITY_THRESHOLD = 0.42

SIMILARITY_WEIGHTS = {"ngram": 0.4, "jaccard": 0.3, "edit": 0.3}
N_GRAM_SIZE = 2

LOG_NORMALIZE_MAX = {
    "微博": 1e7, "知乎": 1e6,
}

LINEAR_NORMALIZE_RANGE = {
    "豆瓣": (5, 10),
}


def get_source_weight(source: str) -> float:
    return SOURCE_WEIGHTS.get(source, 0.6)


def tokenize(text: str) -> set:
    words = jieba.lcut(text)
    cleaned = {w for w in words if len(w) > 1 and w not in STOPWORDS and w.isalpha()}
    return cleaned


def normalize_text(text: str) -> str:
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    return text.replace(' ', '').lower()


def get_ngrams(text: str, n: int = 2) -> set:
    text = normalize_text(text)
    if len(text) < n:
        return {text}
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def ngram_similarity(text1: str, text2: str, n: int = 2) -> float:
    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)
    if not ngrams1 or not ngrams2:
        return 0.0
    return len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)


def jaccard_similarity(text1: str, text2: str) -> float:
    words1 = tokenize(text1)
    words2 = tokenize(text2)
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)


def edit_distance_similarity(text1: str, text2: str) -> float:
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)
    if not text1 or not text2:
        return 0.0

    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])

    max_len = max(m, n)
    return 1.0 - (dp[m][n] / max_len) if max_len > 0 else 1.0


def text_similarity(title1: str, title2: str) -> float:
    ngram_sim = ngram_similarity(title1, title2, N_GRAM_SIZE)
    jaccard_sim = jaccard_similarity(title1, title2)
    edit_sim = edit_distance_similarity(title1, title2)

    weights = SIMILARITY_WEIGHTS
    return (
        ngram_sim * weights["ngram"] +
        jaccard_sim * weights["jaccard"] +
        edit_sim * weights["edit"]
    )


def parse_numeric_from_extra(extra: str) -> float:
    if not extra or not isinstance(extra, str):
        return 0.0

    extra = extra.strip().lstrip("✰★☆").strip()

    if "%" in extra:
        match = re.search(r"(\d+\.?\d*)%", extra)
        if match:
            return float(match.group(1))

    if "亿" in extra:
        match = re.search(r"(\d+\.?\d*)\s*亿", extra)
        if match:
            return float(match.group(1)) * 1e8
    elif "万" in extra:
        match = re.search(r"(\d+\.?\d*)\s*万", extra)
        if match:
            return float(match.group(1)) * 1e4

    if "b" in extra.lower():
        match = re.search(r"(\d+\.?\d*)\s*[bB]", extra)
        if match:
            return float(match.group(1)) * 1e9
    elif "m" in extra.lower():
        match = re.search(r"(\d+\.?\d*)\s*[mM]", extra)
        if match:
            return float(match.group(1)) * 1e6
    elif "k" in extra.lower():
        match = re.search(r"(\d+\.?\d*)\s*[kK]", extra)
        if match:
            return float(match.group(1)) * 1e3

    match = re.search(r"(\d+\.?\d*)", extra)
    if match:
        return float(match.group(1))

    return 0.0


def normalize_platform_hot(source: str, extra: str) -> float:
    if not extra:
        return 50.0

    value = parse_numeric_from_extra(extra)
    if value <= 0:
        return 50.0

    if source in LOG_NORMALIZE_MAX:
        max_val = LOG_NORMALIZE_MAX[source]
        normalized = math.log10(value) / math.log10(max_val) * 100
        return min(normalized, 100.0)

    if source in LINEAR_NORMALIZE_RANGE:
        min_val, max_val = LINEAR_NORMALIZE_RANGE[source]
        normalized = (value - min_val) / (max_val - min_val) * 100
        return max(0.0, min(normalized, 100.0))

    if value >= 100:
        return min(value / 100.0, 100.0)
    else:
        return value

    return 0.0


def find_similar_groups(news: List[NewsItem], threshold: float = SIMILARITY_THRESHOLD) -> dict:
    """找出相似的新闻分组，返回每个新闻索引对应的相似新闻索引列表"""
    n = len(news)
    if n == 0:
        return {}

    similar_map = defaultdict(list)

    for i in range(n):
        for j in range(i + 1, n):
            if news[i].source == news[j].source:
                continue

            sim = text_similarity(news[i].title, news[j].title)
            if sim >= threshold:
                similar_map[i].append(j)
                similar_map[j].append(i)

    return dict(similar_map)


def calculate_hot_scores(news: List[NewsItem]) -> List[Tuple[NewsItem, float, List[NewsItem]]]:
    """
    综合热度排名算法

    核心思想：
    1. 找出相似新闻组（同一热点在不同平台的报道）
    2. 跨平台越多 = 热度越高（多平台验证了真实性）
    3. 组内排序：跨平台新闻优先于单平台新闻
    """
    if not news:
        return []

    n = len(news)

    normalized_hot = [normalize_platform_hot(item.source, item.extra) for item in news]

    similar_map = find_similar_groups(news)

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    for i, similar_indices in similar_map.items():
        for j in similar_indices:
            union(i, j)

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    group_scores = []
    for root, members in groups.items():
        representative = max(members, key=lambda i: get_source_weight(news[i].source))

        unique_sources = len(set(news[i].source for i in members))

        avg_hot = sum(normalized_hot[i] for i in members) / len(members)

        avg_source_weight = sum(get_source_weight(news[i].source) for i in members) / len(members)

        base_score = (avg_source_weight * 40 + avg_hot * 60)

        if unique_sources == 2:
            base_score *= 1.5
        elif unique_sources == 3:
            base_score *= 2.2
        elif unique_sources >= 4:
            base_score *= 3.2

        group_scores.append((representative, base_score, members))

    group_scores.sort(key=lambda x: x[1], reverse=True)

    final_scores = [(news[rep], score, [news[m] for m in members]) for rep, score, members in group_scores]

    return final_scores


class NewsHeatRanker:
    """新闻热度排名分析器"""

    @staticmethod
    def calculate_composite_news_heat(
        all_news: List[NewsItem],
        top: int = 30,
    ) -> List[CompositeNewsRank]:
        """
        计算复合资讯热度排名

        Args:
            all_news: 所有新闻列表
            top: 返回前N名

        Returns:
            复合资讯热度排名列表
        """
        logger.info("开始计算复合资讯热度排名")

        if not all_news:
            logger.warning("没有新闻数据，返回空列表")
            return []

        scored_news = calculate_hot_scores(all_news)

        result = []
        for rank, (rep_item, score, group_members) in enumerate(scored_news[:top], 1):
            unique_sources = list(set(item.source for item in group_members))
            avg_hot = sum(
                normalize_platform_hot(item.source, item.extra) 
                for item in group_members
            ) / len(group_members) if group_members else 0.0

            composite_rank = CompositeNewsRank(
                title=rep_item.title,
                representative_url=rep_item.url,
                composite_score=round(score, 2),
                source_count=len(unique_sources),
                sources=unique_sources,
                related_news=group_members,
                avg_hot_score=round(avg_hot, 2),
                rank=rank,
            )
            result.append(composite_rank)

        logger.info(f"复合资讯热度排名计算完成，共{len(result)}条资讯")
        return result
