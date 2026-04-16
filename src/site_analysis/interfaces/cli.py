"""Command-line interface for the site analysis tool."""

import time
from pathlib import Path
from typing import Optional

from site_analysis.application.analysis_service import SiteAnalysisService
from site_analysis.infrastructure.repositories.excel_aoi_repo import ExcelAoiRepository
from site_analysis.infrastructure.repositories.excel_result_exporter import ExcelResultExporter
from site_analysis.infrastructure.repositories.excel_site_repo import ExcelSiteRepository


def main(
    aoi_file: Path = Path("AOI样例数据.xlsx"),
    site_file: Path = Path("基站站点样例数据.xlsx"),
    output_file: Optional[Path] = None,
) -> None:
    if output_file is None:
        output_file = Path(
            f"小区_AOI匹配_1000米限制_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

    print("🔵 加载 AOI 数据...")
    aoi_repo = ExcelAoiRepository(aoi_file)
    print("🔵 加载站点数据...")
    site_repo = ExcelSiteRepository(site_file)
    exporter = ExcelResultExporter()

    service = SiteAnalysisService(aoi_repo, site_repo, exporter)
    print("🚀 执行分析...")
    result = service.run()

    print(f"💾 保存至: {output_file}")
    exporter.export_with_summary(result.sites, result.summary, output_file)

    summary = result.summary
    print("\n📈 结果统计：")
    print(f"   总站点数：{summary.total_sites:,}")
    print(f"   AOI已匹配：{summary.aoi_matched:,}")
    print(f"   室内站总数：{summary.indoor_sites:,}")
    print(f"   室外站总数：{summary.outdoor_sites:,}")
    print(f"   1000米内找到室外站：{summary.indoor_with_outdoor:,}")
    print(f"   1000米内未找到室外站：{summary.indoor_sites - summary.indoor_with_outdoor:,}")
    print(f"\n🎉 完成！文件路径：{output_file}")


if __name__ == "__main__":
    main()
