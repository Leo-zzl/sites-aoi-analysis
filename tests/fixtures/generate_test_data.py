"""Generate synthetic test data for TDD and performance benchmarking."""

import random
import uuid

import pandas as pd
from shapely.geometry import Polygon

# 广东某区域
LON_MIN, LON_MAX = 113.2, 113.9
LAT_MIN, LAT_MAX = 22.4, 22.9

AOI_OUTPUT = "tests/fixtures/sample_data/test_aoi_data.xlsx"
SITE_OUTPUT = "tests/fixtures/sample_data/test_site_data.xlsx"

SCENES = ["商业区", "交通枢纽", "住宅区", "写字楼", "场馆", "工业区"]
SCENE_BIG = ["城市中心", "郊区", "交通枢纽", "工业区"]
SCENE_SMALL = ["核心", "边缘", "一级", "二级", "三级"]
FREQS = ["700M", "2.1G", "2.6G", "3.5G", "4.9G"]
COVER_TYPES = ["室内"] * 3 + ["室外"] * 6 + ["未知"] * 1


def random_polygon(center_lon, center_lat, size_deg=0.003):
    """Generate a simple 4-point polygon around a center."""
    half = size_deg / 2
    coords = [
        (center_lon - half, center_lat - half),
        (center_lon + half, center_lat - half),
        (center_lon + half, center_lat + half),
        (center_lon - half, center_lat + half),
        (center_lon - half, center_lat - half),
    ]
    return Polygon(coords)


def generate_aoi_data(n=1000):
    records = []
    for i in range(n):
        lon = random.uniform(LON_MIN, LON_MAX)
        lat = random.uniform(LAT_MIN, LAT_MAX)
        size = random.uniform(0.001, 0.005)  # ~100m to ~500m
        poly = random_polygon(lon, lat, size)
        records.append({
            "省": "广东省",
            "市": "深圳市",
            "覆盖类型": random.choice(["室内", "室外"]),
            "场景": random.choice(SCENES),
            "场景大类": random.choice(SCENE_BIG),
            "场景小类": random.choice(SCENE_SMALL),
            "边界WKT": poly.wkt,
        })
    df = pd.DataFrame(records)
    df.to_excel(AOI_OUTPUT, index=False)
    print(f"Generated AOI data: {AOI_OUTPUT} ({len(df)} rows)")
    return df


def generate_site_data(n=1000):
    records = []
    for i in range(n):
        lon = random.uniform(LON_MIN, LON_MAX)
        lat = random.uniform(LAT_MIN, LAT_MAX)
        records.append({
            "小区名称": f"CELL_{i:05d}_{uuid.uuid4().hex[:6]}",
            "使用频段": random.choice(FREQS),
            "覆盖类型": random.choice(COVER_TYPES),
            "纬度": lat,
            "经度": lon,
            "额外列A": random.randint(1, 100),
            "额外列B": random.choice(["A", "B", "C"]),
        })
    df = pd.DataFrame(records)
    df.to_excel(SITE_OUTPUT, index=False)
    print(f"Generated Site data: {SITE_OUTPUT} ({len(df)} rows)")
    return df


if __name__ == "__main__":
    random.seed(42)
    generate_aoi_data(1000)
    generate_site_data(1000)
