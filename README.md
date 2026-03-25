# Kimi Floral Pattern Trends

一个基于 Kimi Code CLI 的趋势研究 skill，用来搜索最近网上的花型/印花/图案流行趋势，默认筛出 Top 6，并生成 6 篇独立 Markdown 文章。

## 功能

- 联网搜索最近的花型、印花、图案趋势
- 输出 `Top 6` 排名页
- 生成结构化趋势数据 JSON
- 为每个趋势生成一篇独立 Markdown 文章
- 自动尝试从证据来源页回填代表图
- 区分“事实”和“研判”

## 目录结构

```text
kimi-floral-pattern-trends/
├─ SKILL.md
├─ README.md
├─ agents/
│  └─ openai.yaml
├─ references/
│  ├─ article-template.md
│  └─ source-ladder.md
└─ scripts/
   └─ generate_floral_trend_markdown.py
```

## 依赖

- `kimi` CLI 已安装且可执行
- 当前环境中的 `kimi` 已登录
- Python 3.10+

检查方式：

```powershell
kimi --version
python --version
```

## 默认输出

脚本默认生成：

- `00-ranking.md`
- `00-scout-raw.md`
- `top6-trends.json`
- `01-*.md` 到 `06-*.md`

## 使用方法

在仓库根目录运行：

```powershell
python .\scripts\generate_floral_trend_markdown.py
```

常用参数示例：

```powershell
python .\scripts\generate_floral_trend_markdown.py `
  --time-window "最近90天" `
  --region "中国与全球" `
  --domain "家纺、面料印花、图案设计、软装与服饰图案" `
  --count 6 `
  --output-dir E:\App\kimi
```

更聚焦的例子：

```powershell
python .\scripts\generate_floral_trend_markdown.py `
  --time-window "最近180天" `
  --region "全球" `
  --domain "女装印花、连衣裙印花、丝巾图案" `
  --count 6
```

## 输出原则

- 只使用 `kimi` 做联网研究
- 趋势名必须来自当次搜索结果
- 不编造销量、GMV、后台热搜指数
- 每篇文章都保留来源链接
- 代表图优先取证据页本身的公开图片
- 抓不到图时省略图片行

## 备注

这个仓库主要保存 skill 本体，不包含批量生成后的示例输出目录。生成结果会写到你运行脚本时指定的输出目录中。
