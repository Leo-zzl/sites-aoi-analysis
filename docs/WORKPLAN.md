# 小区-AOI 空间匹配分析工具 — 综合改进工作计划

> 本计划覆盖项目当前全部风险点与 UX 债务，按**独立分支**拆解为可并行的任务清单。  
> 设计参考稿已用 Pencil 完成（`pencil-new.pen`），进度面板原型见截图。  
> **开发原则：每个 feature 开发前必须先写测试用例，遵循 DDD 分层设计 + TDD 测试驱动开发。**

---

## 零、开发原则（适用于所有 Phase）

### 0.1 DDD 分层与测试对应关系

项目已采用 DDD 分层架构，测试用例必须按层组织，禁止跨层直接测试实现细节：

| 分层 | 职责 | 测试类型 | 测试目录 |
|------|------|----------|----------|
| **Domain** 领域层 | 实体、值对象、领域规则 | 单元测试 | `tests/unit/domain/` |
| **Application** 应用层 | 用例编排、Service 编排 | 单元测试 + 集成测试 | `tests/unit/application/`、`tests/integration/application/` |
| **Infrastructure** 基础设施层 | 仓储、空间索引、投影 | 集成测试 | `tests/integration/infrastructure/` |
| **Interfaces** 接口层 | CLI/API/GUI 适配器 | 集成测试 + E2E 测试 | `tests/integration/interfaces/`、`e2e/` |

### 0.2 TDD 开发节奏

每个 feature 必须遵循 **红-绿-重构** 循环：

1. **红**：先写测试用例（此时测试失败）
2. **绿**：写最少代码使测试通过
3. **重构**：优化实现，确保测试仍通过

**禁止行为**：先写实现代码，再补测试。测试必须与实现代码在同一 PR 中提交。

### 0.3 每个 Phase 的测试准入标准

- **单元测试**：覆盖率 ≥ 80%（核心逻辑分支必须覆盖）
- **集成测试**：每个 API 端点、每个 Repository、每个 Service 至少 1 个集成测试
- **前端测试**：每个工具函数、每个状态转换、每个用户交互路径至少 1 个测试
- **所有测试通过**：`pytest` 全绿 + `npm test` 全绿，方可提交 PR

---

## 一、当前风险全景

| 编号 | 风险点 | 影响 | 现状 |
|------|--------|------|------|
| R1 | 同时维护 tkinter + Electron 两套 GUI | 🔴 高 | 任何新功能需改两处；`main.py --gui` 仍拉起 tkinter |
| R2 | 进度反馈太粗，用户误判"卡死" | 🔴 高 | 仅 6 个百分比节点，无数据量、无子步骤、无动画 |
| R3 | 前端 test 脚本为占位符 | 🟡 中 | `npm test` 直接 `exit 1`，Electron 零自动化测试 |
| R4 | API Session / Job 纯内存存储 | 🟡 中 | 进程重启后 session/job 全失效；内存只增不减 |
| R5 | 上传临时文件无清理策略 | 🟡 中 | `api.py` 只写不删，长期堆积 |
| R6 | 无文件大小限制 | 🟢 低 | 误传超大 Excel 可能导致 OOM |

---

## 二、分支策略与并行原则

### 2.1 分支命名规范

```
feature/remove-tkinter         → Phase 1
feature/backend-progress       → Phase 2
feature/frontend-ux            → Phase 3
feature/engineering-cleanup    → Phase 4
```

### 2.2 并行可行性矩阵

| Phase | 主要修改文件 | 与谁冲突 | 能否并行开发 |
|-------|-------------|---------|-------------|
| **P1 砍 tkinter** | `main.py`、删 `interfaces/gui/`、删 `tests/`、`application/import_service.py`、`api.py` 的 `/upload` | P2/P4 都触及 `api.py` | ⚠️ 可并行，但**必须最先合入主干** |
| **P2 后端进度** | `analysis_service.py`、`api.py` 的 `_run_analysis_job` | P4 触及 `api.py` finally 块 | ✅ 可与 P3 并行；与 P4 需约定 finally 块由谁改 |
| **P3 前端 UX** | `electron/renderer/*`（HTML/CSS/JS） | 无 | ✅ **完全独立，可与任何 Phase 并行** |
| **P4 工程化** | `api.py` 清理逻辑、`electron/main.js`、`package.json` | P2 触及 `api.py` | ⚠️ 可与 P1/P3 并行；与 P2 需约定 `api.py` 分工 |

### 2.3 冲突消解方案

**核心冲突点：`api.py` 被 P1/P2/P4 三方触及。**

为最大化并行度，对 `api.py` 采用**区域责任制**：

| 区域 | 负责人 | 说明 |
|------|--------|------|
| `/upload` 接口 + 顶部 import | **P1** | 解耦 `MainViewModel`，重写 upload 逻辑 |
| `_run_analysis_job` + `/analyze` | **P2** | 只改任务执行体与进度 push，不改 finally 结构 |
| `finally` 块 + 全局清理 + `/cleanup` | **P4** | 在 P2 合并后基于最新主干开发，统一处理临时文件、TTL、大小限制 |

**实际执行顺序建议**：

```
main
├── P1 开发完成 → 合入 main（最先，因为删目录影响文件结构）
├── P3 开发完成 → 随时可合入（完全独立）
├── P2 开发完成 → 合入 main（此时 finally 块保持原样，只加 push 调用）
└── P4 基于 "main + P2" 开发 → 合入 main（统一改 finally、加 TTL、加清理）
```

**结论**：
- **P3 前端 UX** 完全可以现在就开分支独立开发，不依赖任何后端改动（只需 mock SSE 消息格式）。
- **P1 和 P3 可立即并行启动**。
- **P2 等 P1 合入后再启动**，避免 `api.py` 冲突；或 P2 基于 P1 分支继续开发。
- **P4 等 P2 合入后再启动**，一次性把 `api.py` 的 finally 块、TTL、清理逻辑、大小限制做完。

---

## Phase 1 — 砍掉 tkinter，统一 Electron 入口
**分支**：`feature/remove-tkinter`  
**目标**：彻底移除 tkinter 代码路径，所有 GUI 交互只保留 Electron。  
**预期收益**：减少 ~500 行无效代码，消除双 UI 维护负担。

### P1 测试先行清单

**开发前必须完成以下测试用例编写：**

| 测试ID | 层级 | 测试目标 | 测试内容 |
|--------|------|----------|----------|
| P1-T01 | Application | `ImportService.suggest_mapping()` 单元测试 | 给定列名列表，返回正确的 AOI/Site 自动映射；未知列名时返回空字符串 |
| P1-T02 | Application | `ImportService.preview_columns()` 边界测试 | xlsx/csv 文件预览；空文件；编码异常（gbk/utf-8-sig） |
| P1-T03 | Interfaces | `/upload` API 集成测试 | 上传 AOI/Site 文件后返回正确列名和映射；上传非法文件返回错误 |
| P1-T04 | Interfaces | `main.py` CLI 入口测试 | 不传参数走 CLI；传 `--gui` 返回友好提示并 exit 1 |
| P1-T05 | E2E | Electron 上传流程端到端 | 模拟选择文件 → 校验列映射 → 确认 upload 接口响应格式正确 |

### 1.1 迁移列检测逻辑（先迁后删，避免炸）
- **文件**：`src/site_analysis/application/import_service.py`
- **动作**：
  1. 将 `interfaces/gui/view_model.py` 中的关键词集（`_SCENE_KEYWORDS`、`_BOUNDARY_KEYWORDS` 等）与 `_detect_column` 方法迁移至此
  2. 新增 `suggest_mapping(columns: List[str], file_type: str) -> ColumnMapping` 静态方法
- **TDD 要求**：先写 P1-T01，确认测试失败 → 实现 `suggest_mapping` → 测试通过
- **验收**：`ImportService.suggest_mapping` 返回结果与原来 `MainViewModel` 完全一致

### 1.2 解耦 `api.py` 的 `/upload` 接口
- **文件**：`src/site_analysis/interfaces/api.py`
- **动作**：
  1. 移除 `from site_analysis.interfaces.gui.view_model import MainViewModel`
  2. `/upload` 中改为直接调用 `ImportService.preview_columns(dest)` + `ImportService.suggest_mapping(columns, file_type)`
- **TDD 要求**：先写 P1-T03，确认测试失败 → 重写 upload 逻辑 → 测试通过
- **验收**：Electron 上传文件后，列名和自动映射与之前行为一致

### 1.3 删除 tkinter GUI 源码目录
- **范围**：`src/site_analysis/interfaces/gui/`（含 `app.py`、`view_model.py`、`widgets/` 下所有文件）
- **动作**：整目录删除
- **验收**：项目中不存在 `import tkinter` 或 `from tkinter`

### 1.4 清理 `main.py` 入口
- **文件**：`main.py`
- **动作**：移除 `--gui` 分支；保留友好提示
- **TDD 要求**：先写 P1-T04，确认测试失败 → 修改 main.py → 测试通过
- **修改后逻辑**：
  ```python
  if __name__ == "__main__":
      if len(sys.argv) > 1 and sys.argv[1] == "--gui":
          print("--gui 参数已移除，请使用 npm start 启动桌面应用")
          sys.exit(1)
      from site_analysis.interfaces.cli import main
      main()
  ```

### 1.5 删除 tkinter 相关测试文件
- **范围**：
  - `tests/unit/test_main_window.py`
  - `tests/unit/test_main_window_analyze.py`
  - `tests/unit/test_main_window_structure.py`
  - `tests/unit/test_main_window_macos_deadlock.py`
  - `tests/unit/test_main_window_file_select.py`
  - `tests/unit/test_mapping_frame.py`
  - `tests/integration/test_gui_launch.py`
- **动作**：删除文件，检查 `pyproject.toml` 中是否有针对这些测试的特殊配置

### 1.6 清理其他隐性 tkinter 引用
- **范围**：全项目搜索 `tkinter`、`run_gui`、`--gui`
- **文件注意**：根目录 `verify_subprocess_ui.py` 使用了 tkinter，确认是否仍在使用；如已废弃一并删除

### 1.7 验证 Electron 独立运行
- **命令**：`npm start`
- **验证流程**：选择 AOI 文件 → 选择站点文件 → 校验 → 开始分析 → 结果保存
- **通过标准**：全流程无需 `main.py --gui` 即可完成功能闭环

---

## Phase 2 — 后端进度精细化
**分支**：`feature/backend-progress`  
**目标**：让后端在关键步骤输出"当前在做什么 + 已处理多少数据"。  
**与 P1 的关系**：基于已合入 P1 的主干开发，避免 `api.py` 冲突。  
**与 P4 的约定**：**只改 `_run_analysis_job` 的执行体与 push 调用，不改 finally 块结构**。

### P2 测试先行清单

| 测试ID | 层级 | 测试目标 | 测试内容 |
|--------|------|----------|----------|
| P2-T01 | Application | `SiteAnalysisService.run()` 进度回调单元测试 | mock `progress_callback`，验证各阶段调用次数、stage 数值、message/detail 内容符合预期 |
| P2-T02 | Application | `_match_aois()` 统计准确性测试 | 给定 mock AOI 和 Site，验证匹配后 `matched_count` 计算正确 |
| P2-T03 | Application | `_find_nearest_outdoor()` 子步骤覆盖测试 | mock `progress_callback`，验证 7 个子步骤都被调用，且携带正确的数量信息 |
| P2-T04 | Domain | `AnalysisSummary.from_sites()` 单元测试 | 给定含 AOI 匹配/最近室外站结果的 Site 列表，验证统计字段计算正确 |
| P2-T05 | Interfaces | SSE 消息格式集成测试 | 启动分析任务后，通过 EventSource 接收消息，验证每条消息包含 `stage`/`message`/`detail` |

### 2.1 加载阶段增加数量反馈
- **文件**：`src/site_analysis/application/analysis_service.py`
- **修改点**：`SiteAnalysisService.run()`
- **TDD 要求**：先写 P2-T01，确认测试失败 → 实现数量反馈 → 测试通过
- **新增行为**：
  - AOI 加载完成后：`detail="已识别 {len(aois)} 个有效 AOI"`
  - 站点加载完成后：`detail="已识别 {len(sites)} 个站点（室内 {indoor_count} / 室外 {outdoor_count}）"`

### 2.2 AOI 空间匹配增加子步骤与统计
- **文件**：`src/site_analysis/application/analysis_service.py`
- **修改点**：`_match_aois`
- **TDD 要求**：先写 P2-T02，确认测试失败 → 实现统计逻辑 → 测试通过
- **新增行为**：
  - 匹配前：`detail="构建空间数据...（{len(sites)} 个站点 / {len(aois)} 个 AOI）"`
  - 匹配后：`detail="已完成，{matched}/{len(sites)} 个站点已匹配 AOI"`

### 2.3 最近室外站查询拆分子步骤
- **文件**：`src/site_analysis/application/analysis_service.py`
- **修改点**：`_find_nearest_outdoor`
- **TDD 要求**：先写 P2-T03，确认测试失败 → 拆分子步骤 → 测试通过
- **子步骤**：
  1. `筛选室内/室外站点... 室内 {n} 个，室外 {m} 个`
  2. `计算 UTM 投影区... Zone {zone_number}{hemisphere}`
  3. `投影坐标到 UTM...`
  4. `构建室外站空间索引...（{m} 个站点）`
  5. `批量查询最近室外站...（{n} 个室内站）`
  6. `写入最近室外站结果...`
  7. `已完成，{found_count}/{n} 个室内站找到最近室外站`

### 2.4 重新校准进度百分比
- **文件**：`src/site_analysis/application/analysis_service.py`
- **新映射**：
  | 步骤 | 旧 | 新 |
  |------|-----|-----|
  | 准备分析 | — | 5% |
  | 加载 AOI | 10% | 10% → 15% |
  | 加载站点 | 30% | 25% → 30% |
  | AOI 匹配 | 45% | 40% → 45% → 50% → 55% |
  | 最近室外站 | 70% | 60% → 62% → 65% → 68% → 72% → 78% |
  | 生成统计摘要 | 85% | 85% → 95% |
  | 完成 | 100% | 100% |

### 2.5 API 层透传细粒度消息
- **文件**：`src/site_analysis/interfaces/api.py`
- **修改点**：`_run_analysis_job` 中的 `push()` 调用
- **TDD 要求**：先写 P2-T05，确认测试失败 → 透传 detail → 测试通过
- **要求**：所有 push 必须携带 `detail` 参数；与 P4 约定：**finally 块保持原样**

---

## Phase 3 — 前端进度 UX 全面升级
**分支**：`feature/frontend-ux`  
**目标**：把"一个进度条 + 一行文字"升级为"可视化步骤轨道 + 实时日志 + 动态动画"。  
**并行性**：✅ **完全独立，可与 P1/P2/P4 中的任何一个并行开发**。  
**唯一约定**：SSE 消息格式保持 `{"stage": int, "message": str, "detail": str}`，P3 只需消费这个格式。

### P3 测试先行清单

| 测试ID | 层级 | 测试目标 | 测试内容 |
|--------|------|----------|----------|
| P3-T01 | Unit (JS) | 进度状态机 reducer 测试 | 输入 `{stage, message, detail}`，验证 `progressSteps` 数组正确追加/更新；验证 done/doing/pending 状态转换 |
| P3-T02 | Unit (JS) | `defaultOutputName()` 工具函数测试 | 验证返回格式包含日期时间戳，扩展名为 `.xlsx` |
| P3-T03 | Unit (JS) | `setSelectOptions()` 工具函数测试 | 验证 select 元素正确清空、填充选项、设置选中值 |
| P3-T04 | Component (JS) | 步骤渲染测试 | mock 5 个步骤（2 done + 1 doing + 2 pending），验证 DOM 中正确渲染对应 CSS 类名和颜色 |
| P3-T05 | Component (JS) | 动画类名切换测试 | 分析开始时 `.progress-bar` 获得 `active` 类；完成后移除 |
| P3-T06 | Component (JS) | 取消/错误状态测试 | 模拟 SSE 发送 `cancelled`/`error` 事件，验证日志区保留历史、当前步骤标红 |
| P3-T07 | E2E | 完整分析流程视觉回归 | Playwright 截图对比：分析前 → 分析中（进度条有值）→ 分析后（摘要卡片可见） |

### 3.1 扩展进度区域 DOM 结构
- **文件**：`electron/renderer/index.html`
- **新增元素**：
  - `<div id="progress-meta">`：当前步骤标题 + doing 点点点动画区
  - `<p id="progress-detail">`：详细数据说明
  - `<div id="progress-log">`：步骤日志列表（可滚动）
  - `<div id="summary-card">`：分析完成后的统计摘要卡片（默认隐藏）

### 3.2 增加 CSS 动画系统
- **文件**：`electron/renderer/style.css`
- **新增样式**：
  - `.progress-bar.active`：进度条脉冲 glow
  - `.dots-anim`：三个圆点呼吸动画（模拟 `...`）
  - `.step-item.done/.doing/.pending`：绿/橙/灰三色状态
  - `.log-entry`：新条目滑入动画

### 3.3 重构进度状态机
- **文件**：`electron/renderer/app.js`
- **TDD 要求**：先写 P3-T01 ~ P3-T06，确认测试失败 → 重构 JS → 测试通过
- **核心改动**：
  1. `setProgress(percent, message, detail)` → 扩展为对象 `{stage, message, detail, status}`
  2. 维护 `progressSteps[]` 数组，记录历史步骤
  3. SSE `progress` 事件：新步骤推入日志并滚动到底部；当前步骤更新 detail
  4. SSE `heartbeat` 事件：刷新 doing 动画，防止"冻住"感
  5. 分析完成后：渲染 `summary-card`，展示总站点数 / AOI 匹配数 / 室内站找到室外站数

### 3.4 取消/错误状态友好展示
- **文件**：`electron/renderer/app.js`
- **TDD 要求**：P3-T06 先行
- **要求**：
  - 取消：当前步骤标红为"已取消"，保留已完成步骤上下文
  - 报错：错误信息以红色卡片展示在日志底部

---

## Phase 4 — 工程化与稳定性加固
**分支**：`feature/engineering-cleanup`  
**目标**：补齐临时文件清理、内存 TTL、测试框架、上传限制。  
**与 P2 的关系**：基于已合入 P2 的主干开发，**统一修改 `api.py` 的 finally 块和全局逻辑**，避免与 P2 冲突。

### P4 测试先行清单

| 测试ID | 层级 | 测试目标 | 测试内容 |
|--------|------|----------|----------|
| P4-T01 | Interfaces | 临时文件清理集成测试 | mock 分析任务完成后，验证 `TEMP_DIR` 中对应文件被删除；`_upload_sessions` 中对应 session 被移除 |
| P4-T02 | Interfaces | `/cleanup` 接口测试 | 调用 `/cleanup` 后验证 `TEMP_DIR` 被清空 |
| P4-T03 | Application | Job TTL 单元测试 | 创建已完成的 job，模拟时间流逝 30 分钟，验证 `_analysis_jobs` 中该 job 被移除 |
| P4-T04 | Interfaces | 上传大小限制测试 | 上传 51MB 文件，验证返回 `{"error": "文件超过 50MB 限制"}`，且文件未写入磁盘 |
| P4-T05 | Unit (JS) | Vitest 框架接入测试 | 验证 `npm test` 命令能正确运行 Vitest，至少跑通一个 demo 测试 |
| P4-T06 | E2E | Electron 退出清理测试 | 模拟 app quit，验证 `/cleanup` 接口被调用（可通过 mock 或日志断言） |

### 4.1 分析完成后清理上传临时文件
- **文件**：`src/site_analysis/interfaces/api.py`
- **修改点**：`_run_analysis_job` 的 `finally` 块（此时 P2 已合入，finally 块由 P4 统一改写）
- **TDD 要求**：先写 P4-T01，确认测试失败 → 实现清理逻辑 → 测试通过
- **动作**：
  - 删除 `aoi_path` 和 `site_path` 临时文件
  - 从 `_upload_sessions` 中 pop 对应 session
- **安全边界**：只删 `TEMP_DIR` 内文件，绝不碰 `output_path`

### 4.2 应用退出时整体清理临时目录
- **文件**：`electron/main.js` + `api.py`
- **TDD 要求**：先写 P4-T02 和 P4-T06
- **动作**：
  - `api.py` 新增 `POST /cleanup` 接口，清空 `TEMP_DIR`
  - `electron/main.js` 的 `will-quit` 事件调用 `/cleanup`

### 4.3 Job / Session 内存 TTL
- **文件**：`src/site_analysis/interfaces/api.py`
- **TDD 要求**：先写 P4-T03，确认测试失败 → 实现 TTL → 测试通过
- **方案**：
  - 已完成的 job，30 分钟后自动从 `_analysis_jobs` 中移除
  - 实现：`threading.Timer(1800.0, lambda: _analysis_jobs.pop(job_id, None))`
  - 上传 session 在分析完成后立即清理（与 4.1 联动）

### 4.4 前端单元测试框架（替换占位脚本）
- **文件**：`package.json`
- **TDD 要求**：先写 P4-T05，确认测试失败 → 配置 Vitest → 测试通过
- **方案**：
  - 引入 `vitest` 为 devDependency
  - 新增 `electron/renderer/__tests__/` 目录
  - `test` 脚本改为 `"vitest run"`

### 4.5 Electron E2E 测试（可选，P3 优先级）
- **范围**：新增 `e2e/` 目录
- **方案**：引入 `playwright`，覆盖"选择文件 → 校验 → 分析 → 结果保存"主链路
- **备注**：需 CI 中配置 Python 环境

### 4.6 上传文件大小限制
- **文件**：`src/site_analysis/interfaces/api.py`
- **TDD 要求**：先写 P4-T04，确认测试失败 → 实现限制 → 测试通过
- **方案**：`/upload` 接口增加大小校验
  - 单文件上限 50 MB
  - 超限返回 `{"error": "文件超过 50MB 限制"}`

---

## 三、执行顺序与合并流程

### 推荐时序（最大化并行）

```
Day 1
├── git checkout -b feature/remove-tkinter
├── git checkout -b feature/frontend-ux
└── P1 与 P3 同时开发（各自先写测试用例）

Day 2-3
├── P1 完成（含测试）→ PR → 合入 main
└── P3 继续开发（含测试，不受 P1 影响）

Day 4
├── git checkout main && git pull
├── git checkout -b feature/backend-progress
└── 基于最新 main 开发 P2（先写测试用例）

Day 5
├── P2 完成（含测试）→ PR → 合入 main
└── P3 完成（含测试）→ PR → 合入 main（可随时合入，独立分支）

Day 6
├── git checkout main && git pull
├── git checkout -b feature/engineering-cleanup
└── 基于 "main + P2" 开发 P4（先写测试用例）

Day 7
└── P4 完成（含测试）→ PR → 合入 main
```

### 合并检查清单（每个 PR 必须通过）

| 检查项 | P1 | P2 | P3 | P4 |
|--------|----|----|----|----|
| 测试用例已先于实现提交 | ✅ | ✅ | ✅ | ✅ |
| 新增/修改代码有对应测试覆盖 | ✅ | ✅ | ✅ | ✅ |
| `pytest` 全绿 | ✅ | ✅ | — | ✅ |
| `npm test` 全绿（非占位） | — | — | ✅ | ✅ |
| Electron 全流程通过 | ✅ | ✅ | ✅ | ✅ |
| 无 tkinter 引用 | ✅ | — | — | — |
| 临时文件已清理 | — | — | — | ✅ |
| 代码审查 | ✅ | ✅ | ✅ | ✅ |

---

## 四、验收标准

| 检查项 | 通过标准 |
|--------|----------|
| tkinter 移除干净 | 全项目无 `import tkinter`；`main.py --gui` 提示已移除；`npm start` 全流程通过 |
| 进度可读性 | 界面上能看到 ≥8 个带数据量的步骤更新 |
| 动画感知 | 分析运行时，进度条有 active 脉冲，当前步骤有 doing 呼吸动画 |
| 步骤日志 | 已完成（绿✓）/ 进行中（橙高亮）/ 待办（灰），可滚动查看历史 |
| 统计摘要 | 分析完成后展示总站点数 / AOI 匹配数 / 室内站找到室外站数 |
| 临时文件 | 分析完成后 `site_analysis_api` 目录无本次残留 |
| 内存 TTL | 已完成的 job 在 30 分钟后从 `_analysis_jobs` 自动消失 |
| 测试 | `pytest` 全绿；`npm test` 跑通 renderer 单元测试；每个 feature 的测试先于实现提交 |
| 上传限制 | >50MB 文件上传返回清晰错误，不触发后端 OOM |

---

## 五、风险与回滚

| 风险 | 缓解措施 |
|------|----------|
| 多分支改 `api.py` 冲突 | 按"区域责任制"分工：P1 改 upload，P2 改 _run_analysis_job 执行体，P4 改 finally；P2/P4 串行合入 |
| 删除 tkinter 误删共用逻辑 | `MainViewModel` 的列检测先迁移到 `ImportService` 并验证 upload 接口通过后，再删除原文件 |
| TDD 增加开发时间 | 测试用例本身很小（每个 feature 5-6 个），且能提前发现接口契约问题，长期节省调试时间 |
| 进度消息过多 SSE 拥塞 | 前端可做 200ms throttle；后端同一子步骤内自然流量可控 |
| 前端动画低配机器卡顿 | 仅用 `transform` + `opacity`（GPU 加速），避免布局属性动画 |
| 临时文件清理误删结果 | 清理逻辑严格限定在 `TEMP_DIR`，与 `output_path` 物理隔离 |
| P3 提前合入但后端消息格式未最终确定 | P3 与 P2 约定 SSE 格式为 `{"stage","message","detail"}`，此格式稳定不变 |

---

## 六、关联文件与修改范围汇总

| Phase | 新增文件 | 修改文件 | 删除文件 |
|-------|---------|---------|---------|
| **P1** | `application/import_service.py`（新增方法）、`tests/unit/application/test_import_service.py`、`tests/integration/interfaces/test_upload_api.py` | `main.py`、`interfaces/api.py`（/upload） | `interfaces/gui/` 整目录、`tests/unit/test_main_window*.py`、`tests/integration/test_gui_launch.py`、`verify_subprocess_ui.py`（如废弃） |
| **P2** | `tests/unit/application/test_analysis_service.py`、`tests/unit/domain/test_analysis_summary.py`、`tests/integration/interfaces/test_progress_sse.py` | `application/analysis_service.py`、`interfaces/api.py`（_run_analysis_job） | — |
| **P3** | `electron/renderer/__tests__/progress.test.js`、`electron/renderer/__tests__/utils.test.js` | `electron/renderer/index.html`、`style.css`、`app.js` | — |
| **P4** | `electron/renderer/__tests__/`（Vitest 配置）、`e2e/`（可选）、`tests/integration/interfaces/test_cleanup.py`、`tests/integration/interfaces/test_upload_limit.py` | `interfaces/api.py`（finally/cleanup/TTL/限制）、`electron/main.js`、`package.json` | — |


---

# 后续工作计划（Phase 5+）

> 以下问题在 P1~P4 完成后发现，作为持续改进项列入计划，按优先级逐步消除。

---

## Phase 5 — 领域层外部依赖解耦

**目标**：将 `shapely` 从 `domain/models.py` 中移除，使领域层真正成为零外部依赖的纯业务规则层。  
**背景**：当前 `domain/models.py` 直接 `from shapely.geometry import Point, Polygon`，严格 DDD 中领域层不应依赖基础设施库。

### 5.1 抽取几何适配器
- **文件**：新增 `src/site_analysis/infrastructure/geo/geometry_adapter.py`
- **动作**：
  1. 定义 `GeometryAdapter` 接口（或直接使用 Python `Protocol`）
  2. 提供 `ShapelyAdapter` 实现，封装 `wkt_loads`、`Point`、`Polygon` 等操作
  3. `domain/models.py` 中的 `Site` / `AOI` 不再持有 `shapely` 对象，改为持有 WKT 字符串或简单坐标元组
- **TDD 要求**：先写 `test_geometry_adapter.py`，验证 WKT ↔ shapely 对象双向转换正确

### 5.2 重构 domain models
- **文件**：`src/site_analysis/domain/models.py`
- **动作**：
  1. `Site` 的 `geometry` 字段从 `shapely.geometry.Point` 改为 `(lon, lat)` 元组或 WKT 字符串
  2. `AOI` 的 `geometry` 字段从 `shapely.geometry.Polygon` 改为 WKT 字符串
  3. 所有依赖 `site.geometry` 的地方改为通过 `GeometryAdapter` 转换后再做空间计算
- **影响面**：`analysis_service.py`、所有 Repository、测试用例

### 5.3 更新仓储实现
- **文件**：`infrastructure/repositories/excel_aoi_repo.py`、`csv_aoi_repo.py` 等
- **动作**：加载 WKT 后不再直接传给 `AOI(..., geometry=wkt_loads(...))`，而是传 WKT 字符串，由应用层或基础设施层在需要时转换

### 5.4 验收标准
| 检查项 | 通过标准 |
|--------|----------|
| 零外部依赖 | `domain/` 目录下无任何 `import shapely`、`import geopandas`、`import scipy` |
| 功能无损 | 全部 66 个 pytest 通过，分析结果与重组前完全一致 |
| 性能无退化 | `test_performance.py` 耗时与基线差异 < 5% |

---

## Phase 6 — 工程化加固续篇

**目标**：消除打包阻塞、测试不稳定、跨平台编码等工程债务。

### 6.1 补齐 Electron 打包图标
- **文件**：`electron/assets/`
- **动作**：
  1. 放置 `icon.ico`（Windows，256×256 或至少 128×128）
  2. 放置 `icon.icns`（macOS，包含多分辨率）
  3. 删除临时 `README.md` 或改为 `.gitkeep`
- **验收**：`npm run build:mac` / `build:win` 不再报 icon 缺失警告

### 6.2 稳定 Electron 启动测试
- **文件**：`tests/integration/legacy/test_electron_launch.py`
- **动作**：
  1. 方案 A：给测试打 `@pytest.mark.xfail(reason="环境时序不稳定，待替换为 Playwright")`
  2. 方案 B：删除该测试，由 `e2e/basic.spec.js`（Playwright）完全接管 Electron UI 验证
- **建议**：选方案 B，避免维护两套 Electron 测试

### 6.3 中文文件名跨平台安全
- **文件**：根目录下的 `AOI样例数据.xlsx`、`基站站点样例数据.xlsx`
- **动作**：
  1. 在 `.github/workflows/release.yml` 中增加 `env: LANG: en_US.UTF-8` 和 `PYTHONIOENCODING: utf-8`
  2. 在 `pyproject.toml` 或 `readme.md` 中注明：项目要求 UTF-8 环境
  3. （可选）将样例文件重命名为英文（如 `sample_aoi.xlsx`、`sample_sites.xlsx`），但需同步更新所有文档和测试引用
- **验收**：GitHub Actions 在 Windows + Ubuntu + macOS 三平台均能正常检出和读取样例文件

### 6.4 清理历史 `__pycache__` 残留
- **命令**：
  ```bash
  git rm -r --cached src/**/__pycache__
  git rm -r --cached tests/**/__pycache__
  ```
- **动作**：确认 `.gitignore` 已包含 `__pycache__/`（当前已有），然后清理历史跟踪残留

### 6.5 引入类型检查（可选，P2）
- **工具**：`mypy` 或 `pyright`
- **动作**：在 `pyproject.toml` 增加 `[tool.mypy]` 配置，先对 `domain/` 和 `application/` 启用类型检查
- **收益**：提前发现接口契约错误，尤其 Repository 抽象迁移后，类型提示能防止实现类漏写方法

---

## 三、优先级与执行建议

```
立即（本周）
  └─ 6.1 补齐 Electron 图标（阻塞打包）
  └─ 6.2 处理不稳定 Electron 测试（减少 CI 噪音）

短期（2 周内）
  └─ 6.4 清理 __pycache__ 残留（一次性操作）
  └─ 6.3 中文文件名 CI 安全（GitHub Actions 配置）

中期（1 个月内）
  └─ Phase 5 领域层解耦（工作量最大，需充分测试）

长期（按需）
  └─ 6.5 类型检查（团队熟悉后可逐步推进）
```

---

## 四、验收总表（新增项）

| 检查项 | 通过标准 |
|--------|----------|
| Electron 打包 | `npm run build:mac` 成功生成 `.dmg`，无 icon 缺失警告 |
| CI 稳定 | GitHub Actions 三平台全部 green，无 Electron 启动测试超时 |
| 编码安全 | Windows CI 能正确检出并读取含中文文件名的样例数据 |
| 领域纯净 | `grep -r "import shapely" src/site_analysis/domain/` 返回空 |
| 缓存干净 | `git ls-files | grep __pycache__` 返回空 |
