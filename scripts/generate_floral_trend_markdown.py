#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import unicodedata
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_TIME_WINDOW = "最近90天"
DEFAULT_REGION = "中国与全球"
DEFAULT_DOMAIN = "家纺、面料印花、图案设计、软装与服饰图案"
DEFAULT_LANGUAGE = "中文"
DEFAULT_COUNT = 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use Kimi Code to research the latest floral/pattern trends and generate Top 6 Markdown articles."
    )
    parser.add_argument("--time-window", default=DEFAULT_TIME_WINDOW)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_output_dir(base_dir: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(base_dir).expanduser().resolve() if base_dir else Path.cwd()
    return root / f"floral-pattern-trends-{stamp}"


def trends_json_name(count: int) -> str:
    return f"top{count}-trends.json"


def read_reference(name: str) -> str:
    return (skill_root() / "references" / name).read_text(encoding="utf-8")


def ensure_kimi() -> None:
    if shutil.which("kimi") is None:
        raise RuntimeError("`kimi` was not found in PATH.")
    result = subprocess.run(
        ["kimi", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "`kimi --version` failed.")


def run_kimi(prompt: str, cwd: Path) -> str:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        ["kimi", "--quiet", "-p", prompt],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Kimi returned a non-zero exit code.")
    return result.stdout.strip()


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def extract_json_block(raw_text: str) -> str:
    fence_match = re.search(r"```json\s*(.*?)```", raw_text, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    generic_fences = re.findall(r"```(.*?)```", raw_text, flags=re.DOTALL)
    for block in generic_fences:
        block = block.strip()
        if block.startswith("[") and block.endswith("]"):
            return block

    start = raw_text.find("[")
    end = raw_text.rfind("]")
    if start >= 0 and end > start:
        return raw_text[start : end + 1].strip()

    raise ValueError("Could not locate a JSON array in Kimi output.")


def parse_json_array(raw_text: str, cwd: Path) -> list[dict[str, Any]]:
    candidate = extract_json_block(raw_text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        repair_prompt = textwrap.dedent(
            f"""
            下面是一段原始文本。请把其中的趋势列表修复为严格 JSON 数组。
            要求：
            - 只输出 JSON 数组
            - 不要解释
            - 去掉代码块、注释、尾逗号和无效字符
            - 保留原始字段和值，不要补写新的事实

            原始文本如下：
            {raw_text}
            """
        ).strip()
        repaired = run_kimi(repair_prompt, cwd)
        data = json.loads(extract_json_block(repaired))

    if not isinstance(data, list):
        raise ValueError("Parsed JSON is not an array.")
    return [item for item in data if isinstance(item, dict)]


def slugify(value: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug or fallback


def ensure_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def normalize_evidence(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "source_type": str(item.get("source_type", "待核验")).strip() or "待核验",
                "source_name": str(item.get("source_name", "待核验")).strip() or "待核验",
                "title": str(item.get("title", "待核验")).strip() or "待核验",
                "date": str(item.get("date", "待核验")).strip() or "待核验",
                "url": str(item.get("url", "")).strip(),
                "note": str(item.get("note", "待核验")).strip() or "待核验",
            }
        )
    return normalized


def normalize_data_points(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "metric": str(item.get("metric", "待核验")).strip() or "待核验",
                "value": str(item.get("value", "待核验")).strip() or "待核验",
                "period": str(item.get("period", "待核验")).strip() or "待核验",
                "source_name": str(item.get("source_name", "待核验")).strip() or "待核验",
                "url": str(item.get("url", "")).strip(),
                "note": str(item.get("note", "待核验")).strip() or "待核验",
            }
        )
    return normalized


def normalize_trends(raw_trends: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    trends: list[dict[str, Any]] = []
    for index, item in enumerate(raw_trends[:count], start=1):
        name_zh = str(item.get("name_zh", "")).strip() or f"花型趋势 {index}"
        slug = str(item.get("slug", "")).strip()
        normalized = {
            "rank": int(item.get("rank", index)) if str(item.get("rank", "")).isdigit() else index,
            "name_zh": name_zh,
            "name_en": str(item.get("name_en", "待核验")).strip() or "待核验",
            "slug": slugify(slug or item.get("name_en", "") or name_zh, f"trend-{index:02d}"),
            "category": str(item.get("category", "待核验")).strip() or "待核验",
            "confidence": str(item.get("confidence", "待核验")).strip() or "待核验",
            "why_now": str(item.get("why_now", "待核验")).strip() or "待核验",
            "core_visuals": ensure_list(item.get("core_visuals")),
            "keywords": ensure_list(item.get("keywords")),
            "suggested_applications": ensure_list(item.get("suggested_applications")),
            "representative_image_url": str(item.get("representative_image_url", "")).strip(),
            "evidence": normalize_evidence(item.get("evidence")),
            "data_points": normalize_data_points(item.get("data_points")),
        }
        trends.append(normalized)

    trends.sort(key=lambda entry: entry["rank"])
    for index, trend in enumerate(trends, start=1):
        trend["rank"] = index
        trend["article_file"] = f"{index:02d}-{trend['slug']}.md"
    return trends


def is_usable_image_url(url: str) -> bool:
    candidate = (url or "").strip()
    if not candidate or "待核验" in candidate:
        return False
    if candidate.startswith("data:"):
        return False
    lowered = candidate.lower()
    if "favicon" in lowered:
        return False
    return lowered.startswith("http://") or lowered.startswith("https://")


def confirm_image_asset(url: str) -> bool:
    if not is_usable_image_url(url):
        return False
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            ),
            "Range": "bytes=0-0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
        return content_type.startswith("image/")
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return False


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read(512_000)
    return payload.decode(charset, errors="replace")


def iter_candidate_image_urls(html: str, page_url: str) -> list[str]:
    patterns = [
        re.compile(r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+name=["\']image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']image["\']', re.IGNORECASE),
        re.compile(r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<link[^>]+as=["\']image["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),
    ]
    candidates: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(html):
            candidate = urljoin(page_url, unescape(match.group(1).strip()))
            if not is_usable_image_url(candidate):
                continue
            if candidate in candidates:
                continue
            candidates.append(candidate)
    return candidates


def extract_image_url_from_html(html: str, page_url: str) -> str:
    for candidate in iter_candidate_image_urls(html, page_url):
        parsed = urlparse(candidate)
        suffix = Path(parsed.path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"} and confirm_image_asset(candidate):
            return candidate
        if confirm_image_asset(candidate):
            return candidate
    return ""


def backfill_representative_image(trend: dict[str, Any]) -> None:
    existing = str(trend.get("representative_image_url", "")).strip()
    if confirm_image_asset(existing):
        return

    for evidence in trend.get("evidence", []):
        page_url = str(evidence.get("url", "")).strip()
        if not page_url.startswith(("http://", "https://")):
            continue
        try:
            html = fetch_html(page_url)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            continue
        image_url = extract_image_url_from_html(html, page_url)
        if image_url:
            trend["representative_image_url"] = image_url
            return


def cleanup_article(raw_text: str) -> str:
    fence_match = re.fullmatch(r"```(?:markdown)?\s*(.*?)```", raw_text.strip(), flags=re.DOTALL | re.IGNORECASE)
    cleaned = fence_match.group(1).strip() if fence_match else raw_text.strip()
    heading_index = cleaned.find("# ")
    if heading_index > 0:
        cleaned = cleaned[heading_index:].strip()
    return cleaned


def article_is_valid(markdown: str) -> bool:
    required_sections = [
        "# ",
        "## 趋势解读",
        "## 数据支撑",
        "## 应用建议",
        "## 来源",
    ]
    return len(markdown) >= 800 and all(section in markdown for section in required_sections)


def build_scout_prompt(args: argparse.Namespace, source_ladder: str) -> str:
    return textwrap.dedent(
        f"""
        你是花型趋势研究员。请联网搜索最近公开网页中的花型/印花/图案流行趋势，并输出当前最流行的 Top {args.count}。

        研究范围：
        - 时间窗：{args.time_window}
        - 区域：{args.region}
        - 领域：{args.domain}
        - 输出语言：{args.language}

        来源分层与取证规则如下：
        {source_ladder}

        任务要求：
        1. 不要预设主题，必须根据搜索结果归纳趋势名称。
        2. 尽量同时覆盖权威/行业、社交扩散、市场验证三类来源。
        3. 排出 Top {args.count}，从强到弱。
        4. 只保留有公开网页证据支持的花型趋势。
        5. 如果后段位证据较弱，字段里明确写“待核验”。
        6. 不要编造销量、GMV、平台后台指数或闭门数据。
        7. `slug` 使用英文小写连字符。
        8. `representative_image_url` 尽量给公开文章头图或可直接访问的图片 URL；没有就写空字符串。

        只输出一个 ```json 代码块，不要输出其他说明。JSON 数组中的每个对象都必须包含以下字段：
        - rank
        - name_zh
        - name_en
        - slug
        - category
        - confidence
        - why_now
        - core_visuals
        - keywords
        - suggested_applications
        - representative_image_url
        - evidence
        - data_points

        `evidence` 是数组，每项都包含：
        - source_type
        - source_name
        - title
        - date
        - url
        - note

        `data_points` 是数组，每项都包含：
        - metric
        - value
        - period
        - source_name
        - url
        - note
        """
    ).strip()


def build_article_prompt(
    trend: dict[str, Any],
    args: argparse.Namespace,
    article_template: str,
    retry_note: str = "",
) -> str:
    trend_json = json.dumps(trend, ensure_ascii=False, indent=2)
    retry_block = f"\n补充提醒：\n{retry_note}\n" if retry_note else ""
    return textwrap.dedent(
        f"""
        你是花型趋势编辑。请把下面的结构化趋势信息写成一篇中文 Markdown 文章。

        研究范围：
        - 时间窗：{args.time_window}
        - 区域：{args.region}
        - 领域：{args.domain}

        写作要求：
        1. 只输出最终 Markdown，不要解释，不要额外加封套语。
        2. 优先使用给定 JSON 中的事实、证据和链接；不要自己补新的来源。
        3. “趋势解读”中必须拆成“事实”和“研判”。
        4. “数据支撑”里必须先给证据表，再决定是否画 Mermaid 趋势线。
        5. 只有当公开时间序列证据足够时，才输出 Mermaid 折线图；否则改写为“公开时间序列证据不足，暂不绘制趋势线，详见上表。”
        6. 如果 `representative_image_url` 为空、无效或待核验，删除整行图片语法。
        7. 不要编造销量、GMV、平台后台热搜指数。
        8. 所有来源链接都用 Markdown 链接。
        9. 语言使用中文。
        10. 不要写“已完成”“已保存”“如下所示”这类交付说明，直接输出文章正文。
        11. 最终内容必须以 `# ` 开头，并且必须包含 `## 趋势解读`、`## 数据支撑`、`## 应用建议`、`## 来源`。

        Markdown 模板如下：
        {article_template}
        {retry_block}

        趋势 JSON：
        {trend_json}
        """
    ).strip()


def generate_article(
    trend: dict[str, Any],
    args: argparse.Namespace,
    article_template: str,
    output_dir: Path,
) -> str:
    retry_note = ""
    last_raw = ""
    for attempt in range(3):
        article_prompt = build_article_prompt(trend, args, article_template, retry_note=retry_note)
        last_raw = run_kimi(article_prompt, output_dir)
        article_markdown = cleanup_article(last_raw)
        if article_is_valid(article_markdown):
            return article_markdown
        retry_note = (
            "上一次输出不合格，返回了说明文字或缺失了必需章节。"
            " 这次请严格只输出完整 Markdown 正文，不要解释，不要提文件名。"
        )

    invalid_path = output_dir / f"{trend['rank']:02d}-{trend['slug']}.invalid.txt"
    write_text(invalid_path, last_raw)
    raise RuntimeError(f"Failed to generate a valid article for {trend['name_zh']}. See {invalid_path.name}.")


def build_ranking_markdown(trends: list[dict[str, Any]], args: argparse.Namespace) -> str:
    lines = [
        "# 花型流行趋势 Top 排名",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 时间窗：{args.time_window}",
        f"- 区域：{args.region}",
        f"- 领域：{args.domain}",
        "",
        "> 说明：排名依据是公开网页中的重复提及、跨平台扩散和商品化痕迹，不代表平台后台销量或闭门数据库结果。",
        "",
        "| 排名 | 花型 | 分类 | 可信度 | Why now | 文章 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for trend in trends:
        lines.append(
            f"| {trend['rank']} | {trend['name_zh']} / {trend['name_en']} | {trend['category']} | "
            f"{trend['confidence']} | {trend['why_now']} | [{trend['article_file']}]({trend['article_file']}) |"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1.")

    ensure_kimi()

    source_ladder = read_reference("source-ladder.md")
    article_template = read_reference("article-template.md")

    output_dir = default_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scout_prompt = build_scout_prompt(args, source_ladder)
    scout_raw = run_kimi(scout_prompt, output_dir)
    write_text(output_dir / "00-scout-raw.md", scout_raw)

    raw_trends = parse_json_array(scout_raw, output_dir)
    trends = normalize_trends(raw_trends, args.count)
    for trend in trends:
        backfill_representative_image(trend)
    write_text(output_dir / trends_json_name(len(trends)), json.dumps(trends, ensure_ascii=False, indent=2))

    for trend in trends:
        article_markdown = generate_article(trend, args, article_template, output_dir)
        write_text(output_dir / trend["article_file"], article_markdown)

    ranking = build_ranking_markdown(trends, args)
    write_text(output_dir / "00-ranking.md", ranking)

    print(str(output_dir))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
