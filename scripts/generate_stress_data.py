"""生成压力测试数据：AOI + 站点（60万行以上）。

用法:
    PYTHONPATH=src python scripts/generate_stress_data.py

输出:
    tests/fixtures/stress_aoi.xlsx
    tests/fixtures/stress_site.xlsx
"""

import math
import os
import random
import sys
import time
from pathlib import Path

import pandas as pd

# 将项目根目录加入 sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# 输出目录
OUTPUT_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 广东省大致范围
LON_MIN, LON_MAX = 109.5, 117.5
LAT_MIN, LAT_MAX = 20.0, 25.5

# 频段列表
FREQS = ["700M", "2.1GHz", "2.6GHz", "3.5GHz", "4.9GHz"]

# 城市列表
CITIES = [
    ("广州", 113.1, 113.5, 22.9, 23.4),
    ("深圳", 113.7, 114.6, 22.4, 22.9),
    ("东莞", 113.5, 114.3, 22.7, 23.1),
    ("佛山", 112.8, 113.3, 22.8, 23.2),
    ("中山", 113.2, 113.5, 22.4, 22.7),
    ("珠海", 113.3, 113.7, 22.1, 22.5),
    ("惠州", 114.0, 114.8, 22.7, 23.5),
    ("江门", 112.5, 113.2, 22.2, 22.8),
    ("肇庆", 111.8, 112.8, 22.8, 24.0),
    ("清远", 112.5, 113.8, 23.3, 24.8),
    ("韶关", 113.3, 114.3, 24.5, 25.3),
    ("梅州", 115.8, 116.8, 23.8, 24.8),
    ("汕头", 116.5, 117.1, 23.2, 23.6),
    ("汕尾", 115.0, 115.8, 22.6, 23.2),
    ("阳江", 111.5, 112.3, 21.7, 22.5),
    ("茂名", 110.7, 111.5, 21.4, 22.5),
    ("湛江", 109.8, 110.7, 20.8, 21.8),
    ("云浮", 111.5, 112.2, 22.6, 23.4),
    ("揭阳", 116.0, 116.8, 23.3, 23.8),
    ("潮州", 116.5, 117.0, 23.5, 24.2),
]

AOI_SCENE_NAMES = [
    "万象城", "万达广场", "海岸城", "大悦城", "太古汇", "正佳广场",
    "天河城", "京基100", "平安金融中心", "华润万象天地", "COCO Park",
    "壹方城", "欢乐港湾", "海上世界", "东门老街", "华强北商圈",
    "南山科技园", "福田CBD", "前海自贸区", "蛇口工业区",
    "大梅沙海滨公园", "小梅沙度假村", "东部华侨城", "世界之窗",
    "欢乐谷", "锦绣中华", "华侨城创意园", "深圳湾公园",
    "市民中心", "会展中心", "宝安中心区", "龙华商业中心",
    "布吉关口", "龙岗大运中心", "坪山中心区", "光明科学城",
    "沙井中心", "松岗工业区", "福永物流园", "西乡商业街",
    "大学城", "高新园", "软件产业基地", "生物医药基地",
    "新能源汽车产业园", "跨境电商产业园", "智能制造基地",
]

SITE_NAME_TEMPLATES = [
    "{city}{district}{scene}D-{type}-{index}",
    "{city}{district}{scene}M-{type}-{index}",
    "{city}{district}{scene}H-{type}-{index}",
    "{city}{district}{road}{type}-{index}",
    "{city}{district}{community}{type}-{index}",
]

DISTRICTS = [
    "福田区", "罗湖区", "南山区", "宝安区", "龙岗区", "盐田区",
    "龙华区", "坪山区", "光明区", "大鹏新区",
    "天河区", "越秀区", "荔湾区", "海珠区", "白云区", "黄埔区",
    "番禺区", "花都区", "南沙区", "从化区", "增城区",
    "禅城区", "南海区", "顺德区", "三水区", "高明区",
]

ROADS = [
    "深南大道", "滨海大道", "北环大道", "沙河西路", "科苑路",
    "创业路", "南海大道", "后海大道", "前海路", "宝安大道",
    "广园快速", "中山大道", "黄埔大道", "东风路", "环市路",
    "建设大道", "工业大道", "人民路", "解放路", "友谊路",
]

COMMUNITIES = [
    "花园小区", "阳光花园", "锦绣家园", "翠竹苑", "明珠花园",
    "金碧花园", "汇景新城", "祈福新村", "星河湾", "凤凰城",
    "万科城", "保利花园", "中海锦城", "龙湖天街", "恒大绿洲",
    "招商花园", "金地格林", "碧桂园", "雅居乐", "龙光城",
]

COVERAGE_TYPES = ["室内", "室外"]
COVERAGE_WEIGHTS = [0.15, 0.85]


def _generate_polygon(center_lon, center_lat, width_km=0.5, height_km=0.5):
    """生成一个简单的矩形 WKT Polygon（4个角点）。"""
    # 粗略换算：1度纬度 ≈ 111 km，1度经度 ≈ 111 * cos(lat) km
    lat_deg = height_km / 111.0
    lon_deg = width_km / (111.0 * math.cos(math.radians(center_lat)))

    min_lon = center_lon - lon_deg / 2
    max_lon = center_lon + lon_deg / 2
    min_lat = center_lat - lat_deg / 2
    max_lat = center_lat + lat_deg / 2

    return (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )


def generate_aoi_data(n=100):
    """生成 n 条 AOI 数据。"""
    rows = []
    random.seed(42)
    for i in range(n):
        city_name, lon1, lon2, lat1, lat2 = random.choice(CITIES)
        center_lon = random.uniform(lon1, lon2)
        center_lat = random.uniform(lat1, lat2)
        scene = random.choice(AOI_SCENE_NAMES)
        scene_big = random.choice(["商业区", "居民区", "工业区", "文教区", "交通枢纽"])
        scene_small = random.choice(["大型商业购物区", "普通居民区", "科技园区", "高校区", "地铁站"])
        wkt = _generate_polygon(center_lon, center_lat, width_km=random.uniform(0.3, 2.0))
        rows.append({
            "省": "广东省",
            "市": city_name,
            "室内/外": "整体",
            "场景": f"{city_name}{scene}",
            "场景大类": scene_big,
            "场景小类": scene_small,
            "物业边界": wkt,
        })
    return pd.DataFrame(rows)


def generate_site_data(total_rows=600_000, batch_size=50_000):
    """分批生成站点数据，避免一次性占用过多内存。"""
    random.seed(2024)
    n_batches = total_rows // batch_size
    remainder = total_rows % batch_size

    file_path = OUTPUT_DIR / "stress_site.xlsx"

    # 使用 xlsxwriter 引擎，比 openpyxl 快很多
    writer = pd.ExcelWriter(file_path, engine="xlsxwriter")

    total_written = 0
    start_time = time.time()

    for batch_idx in range(n_batches + (1 if remainder else 0)):
        size = remainder if batch_idx == n_batches and remainder else batch_size

        batch_rows = []
        for _ in range(size):
            city_name, lon1, lon2, lat1, lat2 = random.choice(CITIES)
            lon = random.uniform(lon1, lon2)
            lat = random.uniform(lat1, lat2)

            coverage = random.choices(COVERAGE_TYPES, weights=COVERAGE_WEIGHTS)[0]
            freq = random.choice(FREQS)
            district = random.choice(DISTRICTS)
            road = random.choice(ROADS)
            community = random.choice(COMMUNITIES)
            scene = random.choice(AOI_SCENE_NAMES)
            site_type = "ZRH" if coverage == "室外" else "HRW"
            template = random.choice(SITE_NAME_TEMPLATES)
            idx = random.randint(1, 9)

            name = template.format(
                city=city_name, district=district, scene=scene,
                road=road, community=community, type=site_type, index=idx,
            )

            batch_rows.append({
                "小区名称": name,
                "经度": round(lon, 6),
                "纬度": round(lat, 6),
                "使用频段": freq,
                "覆盖类型": coverage,
            })

        df_batch = pd.DataFrame(batch_rows)
        sheet_name = "Sheet1" if batch_idx == 0 else None
        # 第一批写入，后续追加
        if batch_idx == 0:
            df_batch.to_excel(writer, sheet_name="Sheet1", index=False)
        else:
            # xlsxwriter 不支持 append，需要用 openpyxl 或者在内存中合并
            # 实际上 pandas 的 ExcelWriter 不同引擎行为不同
            # 为了简单，我们把所有 batch 合并成一个 DataFrame 再一次性写入
            # 但这会占用大量内存...
            # 换个策略：先写 CSV，再一次性转 xlsx
            pass

        total_written += size
        elapsed = time.time() - start_time
        print(f"  批次 {batch_idx + 1}: 已生成 {total_written:,} 行, 耗时 {elapsed:.1f}s")

    # 上面的 append 策略对 xlsxwriter 不生效，改用 CSV 中转
    writer.close()
    os.remove(file_path)
    raise NotImplementedError("请使用 generate_site_data_via_csv()")


def generate_site_data_via_csv(total_rows=600_000, batch_size=100_000):
    """先写 CSV（快），再一次性转 xlsx。"""
    random.seed(2024)
    csv_path = OUTPUT_DIR / "stress_site.csv"
    xlsx_path = OUTPUT_DIR / "stress_site.xlsx"

    # 写 CSV header
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("小区名称,经度,纬度,使用频段,覆盖类型\n")

    total_written = 0
    start_time = time.time()
    n_batches = (total_rows + batch_size - 1) // batch_size

    for batch_idx in range(n_batches):
        size = min(batch_size, total_rows - total_written)

        lines = []
        for _ in range(size):
            city_name, lon1, lon2, lat1, lat2 = random.choice(CITIES)
            lon = random.uniform(lon1, lon2)
            lat = random.uniform(lat1, lat2)
            coverage = random.choices(COVERAGE_TYPES, weights=COVERAGE_WEIGHTS)[0]
            freq = random.choice(FREQS)
            district = random.choice(DISTRICTS)
            road = random.choice(ROADS)
            community = random.choice(COMMUNITIES)
            scene = random.choice(AOI_SCENE_NAMES)
            site_type = "ZRH" if coverage == "室外" else "HRW"
            template = random.choice(SITE_NAME_TEMPLATES)
            idx = random.randint(1, 9)
            name = template.format(
                city=city_name, district=district, scene=scene,
                road=road, community=community, type=site_type, index=idx,
            )
            lines.append(f'"{name}",{round(lon, 6)},{round(lat, 6)},{freq},{coverage}\n')

        with open(csv_path, "a", encoding="utf-8-sig") as f:
            f.writelines(lines)

        total_written += size
        elapsed = time.time() - start_time
        print(f"  CSV 批次 {batch_idx + 1}/{n_batches}: 已写 {total_written:,} 行, 耗时 {elapsed:.1f}s")

    print(f"\nCSV 写入完成: {csv_path}")
    print(f"正在转换为 xlsx（60万行可能需要几分钟）...")

    convert_start = time.time()
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False, engine="xlsxwriter")
    convert_elapsed = time.time() - convert_start

    csv_size = csv_path.stat().st_size / (1024 * 1024)
    xlsx_size = xlsx_path.stat().st_size / (1024 * 1024)
    print(f"xlsx 转换完成: {xlsx_path}")
    print(f"  CSV 大小: {csv_size:.1f} MB")
    print(f"  xlsx 大小: {xlsx_size:.1f} MB")
    print(f"  转换耗时: {convert_elapsed:.1f}s")

    # 清理 CSV
    csv_path.unlink()
    return xlsx_path


def main():
    print("=" * 60)
    print("生成压力测试数据")
    print("=" * 60)

    # 1. AOI 数据
    print("\n[1/2] 生成 AOI 数据 (100 个区域)...")
    aoi_df = generate_aoi_data(n=100)
    aoi_path = OUTPUT_DIR / "stress_aoi.xlsx"
    aoi_df.to_excel(aoi_path, index=False, engine="xlsxwriter")
    print(f"  AOI 数据已保存: {aoi_path} ({len(aoi_df)} 行)")

    # 2. 站点数据
    print("\n[2/2] 生成站点数据 (600,000 行)...")
    site_path = generate_site_data_via_csv(total_rows=600_000, batch_size=100_000)

    print("\n" + "=" * 60)
    print("压力测试数据生成完毕！")
    print(f"  AOI : {aoi_path}")
    print(f"  Site: {site_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
