# 小区-AOI空间匹配与室内站宏站分析工具

## 项目概述

本工具用于无线通信网络规划中的**站点-AOI空间关联分析**，包含两大核心功能：

1. **AOI空间匹配**：将所有站点（室内+室外）匹配到对应的AOI（Area of Interest）场景边界内，识别站点所属的场景（商业区、场馆、交通枢纽等）
2. **室内站最近室外站分析**：针对室分/室内站，在指定半径（默认1000米）内查找最近的宏站/室外站，输出距离和频段信息

---

## 功能特性

### 1. AOI空间匹配（全量输出）
- 支持多边形WKT格式的AOI边界数据
- 所有站点（无论是否在AOI内）全部输出
- 未匹配的站点AOI字段留空，状态标记为"未匹配"
- 自动处理重叠AOI（取第一个匹配结果）

### 2. 室内站最近室外站分析（1000米限制）
- 仅针对覆盖类型为"室内/室分"的站点
- 搜索半径：**1000米**（可配置）
- 超出1000米的室外站视为未找到
- 使用UTM投影坐标系计算精确距离（米制）

### 3. 坐标系支持
- 输入坐标：WGS84（EPSG:4326，经纬度）
- 距离计算：根据数据经纬度**自动计算UTM投影带**，支持全国各地

### 4. 高性能空间索引
- 室内站→室外站的最近邻查询使用 `scipy.spatial.cKDTree`
- **10万站点 × 1000 AOI** 规模下分析耗时约 **6 秒**

---

## 安装依赖

### Python 依赖（开发/命令行模式）

```bash
pip install -e .
```

### Electron 桌面应用（无需 Python 环境）

下载 [Releases](https://github.com/Leo-zzl/sites-aoi-analysis/releases) 中的 Windows 安装包或便携版即可直接运行。

---

## 样例数据与字段映射

项目根目录提供了两份样例数据，可直接用于测试：

| 文件 | 说明 | 用途 |
|------|------|------|
| `AOI样例数据.xlsx` | 广东省 20 个城市的 AOI 区域边界 | AOI 空间匹配 |
| `基站站点样例数据.xlsx` | 真实基站站点数据（约 50+ 字段） | 站点数据源 |

### 字段映射指南

在 Electron GUI 中上传文件后，工具会**自动识别**字段名，但仍需确认以下映射：

**AOI 字段（2 个必填）**

| 映射项 | 样例列名 | 说明 |
|--------|---------|------|
| 场景字段 | `场景` | AOI 场景名称，如"深圳大梅沙8号仓" |
| 边界字段 | `物业边界` | WKT 格式的多边形边界 |

**站点字段（5 个必填）**

| 映射项 | 样例列名 | 说明 |
|--------|---------|------|
| 名称 | `小区名称` | 站点唯一标识 |
| 经度 | `经度` | WGS84 经度 |
| 纬度 | `纬度` | WGS84 纬度 |
| 频段 | `使用频段` | 如 2.6GHz、700M |
| 覆盖类型 | `覆盖类型` | `室内` / `室外`（支持自动分类） |

**覆盖类型自动识别关键词**

- **室内**：`室内`、`室分`、`室分系统`、`Indoor`、`indoor`
- **室外**：`室外`、`宏站`、`微站`、`杆站`、`Outdoor`、`outdoor`、`宏蜂窝`、`微蜂窝`

---

## 输入数据格式

### AOI数据（Excel）

文件名称默认为 `AOI样例数据.xlsx`，按以下列顺序排列：

| 列序号 | 字段名 | 说明 | 示例 |
|-------|--------|------|------|
| 1 | 省 | AOI所在省份 | 广东省 |
| 2 | 市 | AOI所在城市 | 深圳市 |
| 3 | - | （预留列，工具不读取） | - |
| 4 | 场景 | AOI场景名称 | 商业区 |
| 5 | 场景大类 | 场景一级分类 | 城市中心 |
| 6 | 场景小类 | 场景二级分类 | 核心 |
| 7 | 边界WKT | AOI多边形边界，WKT格式 | POLYGON((113.2 22.4, ...)) |

### 站点数据（Excel）

文件名称默认为 `基站站点样例数据.xlsx`，**必须包含以下列**：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `小区名称` | 站点唯一标识 | CELL_001 |
| `使用频段` | 站点使用频段 | 2.6G |
| `覆盖类型` | 室内/室外分类 | 室内 / 室外 / 宏站 / 室分 |

**经纬度列**支持自动识别，以下列名均可识别：
- 纬度列：`纬度`、`lat`、`latitude`、`y` 等
- 经度列：`经度`、`lon`、`longitude`、`x` 等
- 若自动识别失败，将回退到第4列（纬度）和第6列（经度）

**覆盖类型兼容值**：
- **室内**：`室内`、`室分`、`室分系统`、`Indoor`
- **室外**：`室外`、`宏站`、`微站`、`杆站`、`Outdoor`、`宏蜂窝`、`微蜂窝`

---

## 使用方法

### 命令行运行

将AOI数据和站点数据放入项目根目录，执行：

```bash
python main.py
```

程序将自动生成结果文件：`小区_AOI匹配_1000米限制_YYYYMMDD_HHMMSS.xlsx`

### 使用 Python API

```python
from pathlib import Path
from site_analysis.application.analysis_service import SiteAnalysisService
from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter

service = SiteAnalysisService(
    aoi_repo=ExcelAoiRepository(Path("AOI样例数据.xlsx")),
    site_repo=ExcelSiteRepository(Path("基站站点样例数据.xlsx")),
    exporter=ExcelResultExporter(),
)
result = service.run()
df = result.to_dataframe()
```

---

## 输出数据格式

结果Excel会在原始站点数据前面插入以下9列分析结果：

### AOI匹配结果（6列）

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `AOI_省` | 匹配到的AOI省份 | 广东省 |
| `AOI_市` | 匹配到的AOI城市 | 深圳市 |
| `AOI_场景` | 匹配到的AOI场景 | 商业区 |
| `AOI_场景大类` | 场景一级分类 | 城市中心 |
| `AOI_场景小类` | 场景二级分类 | 核心 |
| `AOI匹配状态` | 是否匹配到AOI | 已匹配 / 未匹配 |

### 最近室外站分析结果（3列）

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `最近室外站_名称` | 1000米内最近室外站的名称 | CELL_002 |
| `最近室外站_频段` | 该室外站的使用频段 | 2.1G |
| `最近室外站_距离_米` | 精确距离（米），超出1000米为空 | 356.2 |

> 注：只有**覆盖类型为室内**的站点才会计算最近室外站；室外站和未知类型站点的这3列为空。

---

## 项目架构（DDD 分层）

```
src/site_analysis/
├── domain/              # 领域层：纯业务逻辑，无外部依赖
│   ├── models.py        # Site, AOI 实体
│   └── value_objects.py # CoverageType, UtmZone, AnalysisResult
├── application/         # 应用层：编排领域对象完成用例
│   └── analysis_service.py
├── infrastructure/      # 基础设施层：外部实现
│   ├── repositories/    # Excel 数据读写
│   └── geo/             # UTM投影、cKDTree空间索引
└── interfaces/          # 接口层
    └── cli.py           # 命令行入口
```

### 架构原则
- **Repository 模式**：数据读取通过抽象接口，Excel 只是其中一种实现
- **领域对象不可变**：`CoverageType`、`UtmZone`、`AnalysisResult` 等使用值对象
- **应用服务无状态**：`SiteAnalysisService` 只负责编排，不持有持久状态

---

## 测试

### 运行全部测试

```bash
pytest
```

### 运行集成测试（含 Golden Master 校验）

```bash
pytest tests/integration/ -v
```

### 运行压力测试

```bash
pytest tests/integration/test_stress.py -v -s
```

### 测试覆盖说明
- **单元测试**：验证 `CoverageType` 分类、`UtmZone` 计算等纯领域逻辑
- **集成测试**：使用 **1000 行 AOI + 1000 行站点** 的测试数据，对比重构前后的输出是否完全一致（Golden Master）
- **压力测试**：使用 **1000 行 AOI + 10 万行站点** 的测试数据，验证性能在 30 秒以内

---

## 性能基准

| 数据规模 | AOI 匹配 | 最近室外站查询 | 总耗时 |
|---------|---------|--------------|--------|
| 1000 站点 × 1000 AOI | ~0.1s | ~0.1s | **~0.2s** |
| 10万 站点 × 1000 AOI | ~5s | ~1s | **~6s** |

*测试环境：Apple Silicon (M1/M2), Python 3.9*
