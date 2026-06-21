# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 开场约定

每次会话首条回复必须以 **"物流徐，你好"** 开头。

## 项目定位

这不是一个传统代码仓库，而是 **北京科捷物流广东省仓库运营汇报工作区**。核心任务是为客户**中移物流（China Mobile Logistics）**制作月度运营汇报 PPT。

## 核心工作流

1. 用户（科捷物流广东项目经理）提供当月运营数据
2. Claude 根据 `monthly-logistics-report` agent 定义的标准框架，生成逐页 PPT 内容
3. 用户审核后将内容转移到 PowerPoint 交付客户

## Agent 架构

### `monthly-logistics-report`（`.claude/agents/monthly-logistics-report.md`）

核心 agent，包含完整的月度汇报框架：
- **7 个标准章节**：封面 → 执行摘要 → KPI 仪表盘 → 运营亮点分析 → 问题与改进计划 → 下月计划 → 附录
- **KPI 体系**：入库/出库/库存/逆向物流/客诉 五大类指标，每项需对比目标值、环比、同比
- **视觉规范**：中移品牌色系（绿色为主），商务风格，中文排版
- **行文原则**：商务中文，诚实透明，强调科捷的主动管理和增值服务
- **交互协议**：先收集数据 → 澄清背景 → 生成内容 → 审核优化

Agent 拥有独立记忆系统，位于 `.claude/agent-memory/monthly-logistics-report/`，用于积累客户偏好、KPI 目标值、季节性规律等机构知识。

### 记忆类型

该 agent 支持四种记忆类型：
- `user` — 用户角色、偏好、职责
- `feedback` — 用户纠正和确认的工作方式
- `project` — 项目状态、截止日期、约束条件
- `reference` — 外部系统链接（如客户门户、数据源）

## 工作语言

- **主要工作语言**：中文（简体）
- PPT 内容使用**商务中文**，面向客户管理层的正式汇报
- Agent 定义和配置使用中英混合

## 非项目文件

- `What-Can-Claude-Code-Do.md` — Claude Code 能力介绍（通用参考，非项目文档）
- `How-To-Setup-Subagents.md` — Subagent 搭建指南（通用参考，非项目文档）
