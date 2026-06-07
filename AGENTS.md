# AGENTS.md — 双 AI 协作规范

本项目由 **Claude Code** 和 **Codex (OpenAI)** 共同维护。

## 角色分工

| 角色 | Claude Code | Codex |
|------|:--:|:--:|
| 主力开发 | ✅ 复杂功能、架构设计、大文件重构 | 补位：简单脚本、批量替换 |
| 代码审查 | — | ✅ 独立审查（不同模型，不同视角） |
| 数据分析 | ✅ 股票分析全链路 | — |
| 文档/技能维护 | ✅ SKILL.md、DOCX 报告 | — |
| Bug 修复 | ✅ 根因分析 | ✅ 第二意见验证 |

## 协作流程

```
Claude Code 改代码 → Codex review → 意见分歧人工判断
Codex 改代码 → Claude Code 最终检查 → 确认无误后提交
```



## 新增功能

### K线形态分析 (DOCX报告)
- 使用 generate_kline_interpretation_with_today() 聚焦近10个交易日形态识别
- 输出: trend_phase(趋势阶段)、recent_patterns(近期形态列表)、summary(综合判断)、key_observation(关键观察)
- 形态类型: bullish(看涨)/bearish(看跌)，含可靠性评级(高/中/低)
- 27种K线形态识别: 三只乌鸦、黄昏之星、早晨之星、阳包阴、阴包阳、锤子线、射击之星等

### 庄家意图分析 (DOCX报告)
- 使用 nalyze_manipulator_intention() 识别庄家四阶段
- 四阶段: 建仓 → 洗盘 → 拉升 → 出货 (含置信度)
- 输出: phase(当前阶段)、signals(判断依据列表)、volume_analysis(成交量分析)、assessment(综合评估)、risk_note(风险提示)



## 双层过滤选股

### ml_scan.py — ML过滤+自动降级选股工具

`
python ml_scan.py                    # 主板 top10，双层过滤
python ml_scan.py --mode full        # 全A股
python ml_scan.py --top-n 20         # 主板 top20
`

### 过滤层级

| 层级 | PE | PB | 量比 | 换手率 | ML条件 | 标记 |
|:----:|:--:|:--:|:----:|:------:|:------:|:----:|
| Tier1 严格 | 5-60 | ≤8 | ≥0.7 | ≤25% | 三模型看涨 | Tier1 |
| Tier2 宽松 | 5-100 | ≤15 | ≥0.5 | ≤35% | 三模型看涨 | Tier2 [宽松] |

- Tier1 选不够 → 自动降级到 Tier2
- 每个候选标注所属层级，Tier2 会额外提示风险更高
## 速度优化记录

| 优化项 | 优化前 | 优化后 | 方案 |
|:-----:|:------:|:------:|------|
| **周末K线不更新** | **数据停在上周** | **周末也拉取** | cache.py 放宽 is_weekend 条件，days_passed>=2时允许周末增量 |
| 宏观数据API | 23.8s | 0.006s | SQLite缓存(7天TTL) + macro_cache表 |
| ML三模型训练 | 4.7s | 0.001s | 内存缓存 _RESULT_CACHE |
| ML跨进程复用 | 4.7s | 0.01s | 磁盘缓存 models/pred_{hash}.pkl |
| gen_docx报告 | 47s | 12.9s | 以上两项合计 |
|:-----:|:------:|:------:|------|
| 宏观数据API | 23.8s | 0.006s | SQLite缓存(7天TTL) + macro_cache表 |
| ML三模型训练 | 4.7s | 0.001s | 内存缓存 _RESULT_CACHE |
| ML跨进程复用 | 4.7s | 0.01s | 磁盘缓存 models/pred_{hash}.pkl |
| gen_docx_report | 47s | 12.9s | 以上两项合计 |

## 工作规则

1. **大改动前先 commit**，两边在同一基准上干活，避免互相踩
2. **修改文件后必须更新 SKILL.md** 的相关内容（功能、模块列表、注意事项）
3. **项目结构变化**（新增/删除文件）立即同步到 SKILL.md 项目结构段
4. **发现的 bug/陷阱** 记录到 SKILL.md "注意事项 & 已知陷阱"段
5. **性能优化** 记录到 SKILL.md 性能优化记录表
6. **不要改对方的配置文件**（Claude: CLAUDE.md, Codex: 对应的配置）
7. **git commit 前双方确认** 没有语法错误和逻辑 bug

## 项目上下文

- 语言：Python 3.x + TypeScript (React) + Rust (Tauri)
- 数据源：新浪/腾讯/Baostock/东方财富/akshare/Tushare/TickFlow
- 数据库：SQLite (stock_cache.db ~152MB)
- 完整技能文档：`C:\Users\47535\.claude\skills\stock-quant-analysis\SKILL.md`

## 当前状态

- 5个文件有未提交改动（cli.py +194行、backend/main.py +34行、backend/routers/analysis.py 有 bug、run_full_scan.py 重构中、config.py checkpoint改名）
- 2个临时脚本待清理：`_edit_script.py`、`_fix2.py`
