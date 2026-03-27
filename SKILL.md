---
name: kimi-floral-pattern-trends
description: Use when the user asks to research recent 花型/印花/图案流行趋势 with Kimi Code, search the live web, rank the current Top 6 styles, and generate one Markdown article per trend. Suitable for 家纺、面料印花、服饰图案、surface pattern、motif trend discovery when the result must be current, source-backed, and saved as individual .md files.
---

# Kimi Floral Pattern Trends

## Overview

使用本地 `kimi` CLI 做实时联网研究，先从公开网页里找最近重复出现的花型/印花/图案趋势，再输出 Top 6 排名和 6 篇独立 Markdown 文章。

默认交付：
- `00-ranking.md`
- `00-scout-raw.md`
- `top6-trends.json`
- `01-*.md` 到 `06-*.md`

这个 skill 只负责“最新趋势研究 + Markdown 成稿”。脚本会尽量给每篇文章补一张代表图，但图必须是花型/印花/图案本身：优先让 Kimi 从证据页里挑选花型样图、pattern repeat、fabric swatch、wallpaper sample、print close-up 这类图片；只有选不到时才回退到本地抓图逻辑，而且会过滤掉人物、空间场景、整屋陈列、品牌封面和无关头图。抓不到合格图片时就省略图片行。如果用户还要网页、长图或 PDF，再基于这些 `.md` 继续扩展。

## Preconditions

- `kimi --version` 可执行
- 当前机器上的 `kimi` 已完成登录
- 在可写目录中运行脚本

## Default Workflow

1. 运行 `scripts/generate_floral_trend_markdown.py`，让 Kimi 先做一轮 Top 6 趋势搜集与结构化输出。
2. 查看 `00-ranking.md`，确认排名、命名和应用方向没有明显重复。
3. 抽查 `top6-trends.json` 里的 `evidence` 字段，优先确认前 3 名至少覆盖两类来源。
4. 如果用户限定行业、区域或时间窗，重新运行脚本并收窄 `--domain`、`--region`、`--time-window`。

## Commands

在任意工作目录中运行：

```powershell
python C:\Users\Charlo_O\.codex\skills\kimi-floral-pattern-trends\scripts\generate_floral_trend_markdown.py
```

常用参数：

```powershell
python C:\Users\Charlo_O\.codex\skills\kimi-floral-pattern-trends\scripts\generate_floral_trend_markdown.py `
  --time-window "最近90天" `
  --region "中国与全球" `
  --domain "家纺、面料印花、图案设计、软装与服饰图案" `
  --count 6 `
  --output-dir E:\App\kimi
```

更聚焦的例子：

```powershell
python C:\Users\Charlo_O\.codex\skills\kimi-floral-pattern-trends\scripts\generate_floral_trend_markdown.py `
  --time-window "最近180天" `
  --region "全球" `
  --domain "女装印花、连衣裙印花、丝巾图案" `
  --count 6
```

```powershell
python C:\Users\Charlo_O\.codex\skills\kimi-floral-pattern-trends\scripts\generate_floral_trend_markdown.py `
  --time-window "最近90天" `
  --region "中国" `
  --domain "家纺、床品、窗帘、靠垫花型" `
  --count 6
```

## Output Standard

单篇文章结构参考 [references/article-template.md](references/article-template.md)。

硬性要求：
- 只用 `kimi` 做联网研究，不要改用其他搜索代理
- 花型名称必须来自当次搜索结果，不要先主观预设
- 每篇文章都要区分“事实”和“研判”
- 每篇文章都要带来源链接
- 不能编造销量、GMV、平台后台热搜指数
- 只有在公开时间序列证据足够时才画 Mermaid 趋势线
- 代表图必须是花型/印花图样本身，不是人物照、模特图、房间场景图、品牌封面图
- 代表图优先来自证据页本身，不要随意混入无关图库图
- 图片链接找不到或来源页阻止抓取时，省略图片行，不要写占位图

## Source Ladder

来源优先级参考 [references/source-ladder.md](references/source-ladder.md)。

目标不是抓“单个平台一时很火”的花型，而是找：
- 被多家行业/媒体反复提到的主题
- 能跨社交平台扩散的视觉母题
- 已经出现商品化或零售露出的图案方向

## Quality Bar

- 排名依据必须来自公开网页的重复信号，而不是单一主观判断
- Top 6 中每个条目至少要有 3 条可追溯证据；能混合权威、社交、市场三类来源更好
- 如果后段位证据偏弱，必须明确标注 `待核验`
- `00-ranking.md` 中的排名说明要能和单篇文章互相对应
- 文章头图应尽量可追溯到 `evidence` 里的来源页，而且图像主体要和花型本身直接相关

## Resources

- `scripts/generate_floral_trend_markdown.py`: 调用 Kimi，生成 Top 6 JSON、从来源页回填代表图、输出排名页和 6 篇文章
- `references/article-template.md`: 单篇 Markdown 文章模板
- `references/source-ladder.md`: 花型趋势研究的来源分层与取证规则

## Common Mistakes

- 先拍脑袋设定趋势主题，再去补证据
- 把社交平台的单条爆款内容当成长期趋势
- 把“田园风”“疗愈风”这类大风格直接当成具体花型
- 只有观点，没有时间、平台和来源链接
- 输出了 6 个主题，但其中一半只是同一趋势的不同叫法
