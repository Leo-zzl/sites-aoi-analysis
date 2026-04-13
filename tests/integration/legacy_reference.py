"""
Legacy reference implementation copied from main.py (commit f102ce2).
Used to generate Golden Master baseline for TDD refactoring.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.wkt import loads as wkt_loads

# 室内/室外兼容值
INDOOR_VALS = {'室内', '室分', '室分系统', 'Indoor', 'indoor'}
OUTDOOR_VALS = {'室外', '宏站', '微站', '杆站', 'Outdoor', 'outdoor', '宏蜂窝', '微蜂窝'}

COL_COVER_TYPE = '覆盖类型'
COL_FREQ = '使用频段'
COL_SITE_NAME = '小区名称'
MAX_SEARCH_DISTANCE = 1000


def find_lat_lon_columns(df):
    lat_keywords = {'纬度', 'lat', 'latitude', 'latitude_deg', 'lat_deg', 'y'}
    lon_keywords = {'经度', 'lon', 'longitude', 'longitude_deg', 'lon_deg', 'x'}
    lat_col = lon_col = None
    for c in df.columns:
        col_clean = str(c).strip().lower().replace(' ', '').replace('_', '')
        if col_clean in lat_keywords or any(k in col_clean for k in lat_keywords):
            lat_col = c
        if col_clean in lon_keywords or any(k in col_clean for k in lon_keywords):
            lon_col = c
    return lat_col, lon_col


def get_utm_epsg(lon, lat):
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:326{zone:02d}" if lat >= 0 else f"EPSG:327{zone:02d}"


def classify_cover_type(x):
    val = str(x).strip()
    if val in INDOOR_VALS:
        return 'indoor'
    if val in OUTDOOR_VALS:
        return 'outdoor'
    return 'unknown'


def run_legacy_analysis(aoi_file: Path, site_file: Path) -> pd.DataFrame:
    """Run the exact legacy analysis logic and return the output DataFrame."""
    # 1. 读取 AOI 数据
    df_aoi = pd.read_excel(aoi_file, sheet_name=0)

    aoi_records = []
    for idx, row in df_aoi.iterrows():
        province = str(row.iloc[0]).strip()
        city = str(row.iloc[1]).strip()
        scene = str(row.iloc[3]).strip()
        scene_big = str(row.iloc[4]).strip()
        scene_small = str(row.iloc[5]).strip()
        wkt_str = str(row.iloc[6]).strip()
        wkt_str = wkt_str.strip('"').strip("'").strip()
        if not wkt_str or wkt_str.lower() == "nan":
            continue
        try:
            polygon = wkt_loads(wkt_str)
            aoi_records.append({
                "geometry": polygon,
                "aoi_province": province,
                "aoi_city": city,
                "aoi_scene": scene,
                "aoi_scene_big": scene_big,
                "aoi_scene_small": scene_small
            })
        except Exception:
            continue

    gdf_aoi = gpd.GeoDataFrame(aoi_records, crs="EPSG:4326")

    # 2. 读取站点数据
    df_cell = pd.read_excel(site_file, sheet_name=0)

    for col in [COL_SITE_NAME, COL_FREQ, COL_COVER_TYPE]:
        if col not in df_cell.columns:
            raise KeyError(f"❌ 找不到列 '{col}'")

    lat_col, lon_col = find_lat_lon_columns(df_cell)
    if lat_col is None or lon_col is None:
        lat_col = df_cell.columns[3]
        lon_col = df_cell.columns[5]

    df_cell[lon_col] = pd.to_numeric(df_cell[lon_col], errors='coerce')
    df_cell[lat_col] = pd.to_numeric(df_cell[lat_col], errors='coerce')
    valid_coord_mask = df_cell[lon_col].notna() & df_cell[lat_col].notna()
    df_cell = df_cell[valid_coord_mask].reset_index(drop=True)

    gdf_cell = gpd.GeoDataFrame(
        df_cell,
        geometry=gpd.points_from_xy(df_cell[lon_col], df_cell[lat_col]),
        crs="EPSG:4326"
    )

    centroid_lon = gdf_cell.geometry.x.median()
    centroid_lat = gdf_cell.geometry.y.median()
    CRS_METER = get_utm_epsg(centroid_lon, centroid_lat)

    # 3. AOI空间匹配
    joined_aoi = gpd.sjoin(
        gdf_cell[['geometry']],
        gdf_aoi[['aoi_province', 'aoi_city', 'aoi_scene', 'aoi_scene_big', 'aoi_scene_small', 'geometry']],
        how="left",
        predicate="within"
    )
    joined_aoi = joined_aoi[~joined_aoi.index.duplicated(keep='first')]

    df_cell["AOI_省"] = joined_aoi["aoi_province"].reindex(df_cell.index).fillna("").values
    df_cell["AOI_市"] = joined_aoi["aoi_city"].reindex(df_cell.index).fillna("").values
    df_cell["AOI_场景"] = joined_aoi["aoi_scene"].reindex(df_cell.index).fillna("").values
    df_cell["AOI_场景大类"] = joined_aoi["aoi_scene_big"].reindex(df_cell.index).fillna("").values
    df_cell["AOI_场景小类"] = joined_aoi["aoi_scene_small"].reindex(df_cell.index).fillna("").values
    df_cell["AOI匹配状态"] = df_cell["AOI_场景"].apply(lambda x: "已匹配" if x and x != "" else "未匹配")

    # 4. 室内站最近室外站分析
    df_cell['site_type'] = df_cell[COL_COVER_TYPE].apply(classify_cover_type)
    indoor_mask = df_cell['site_type'] == 'indoor'
    outdoor_mask = df_cell['site_type'] == 'outdoor'

    df_cell["最近室外站_名称"] = ""
    df_cell["最近室外站_频段"] = ""
    df_cell["最近室外站_距离_米"] = pd.NA

    if indoor_mask.sum() > 0 and outdoor_mask.sum() > 0:
        gdf_cell_m = gdf_cell.to_crs(CRS_METER)
        gdf_indoor_m = gdf_cell_m[indoor_mask].copy()
        gdf_outdoor_m = gdf_cell_m[outdoor_mask].copy()

        indoor_coords = np.column_stack([gdf_indoor_m.geometry.x.values, gdf_indoor_m.geometry.y.values])
        outdoor_coords = np.column_stack([gdf_outdoor_m.geometry.x.values, gdf_outdoor_m.geometry.y.values])
        outdoor_names = gdf_outdoor_m[COL_SITE_NAME].values
        outdoor_freqs = gdf_outdoor_m[COL_FREQ].values

        from scipy.spatial import cKDTree
        tree = cKDTree(outdoor_coords)
        distances, indices = tree.query(indoor_coords, k=1, distance_upper_bound=MAX_SEARCH_DISTANCE)
        valid_mask = indices < len(outdoor_coords)

        indoor_indices = gdf_indoor_m.index
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_名称"] = outdoor_names[indices[valid_mask]]
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_频段"] = outdoor_freqs[indices[valid_mask]]
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_距离_米"] = distances[valid_mask]

    # 5. 整理输出
    front_cols = [
        "AOI_省", "AOI_市", "AOI_场景", "AOI_场景大类", "AOI_场景小类", "AOI匹配状态",
        "最近室外站_名称", "最近室外站_频段", "最近室外站_距离_米"
    ]
    other_cols = [c for c in df_cell.columns if c not in front_cols and c not in ['geometry', 'site_type']]
    df_output = df_cell[front_cols + other_cols].copy()

    for col in ['geometry', 'site_type']:
        if col in df_output.columns:
            df_output = df_output.drop(columns=[col])

    return df_output


if __name__ == "__main__":
    aoi_path = Path("tests/fixtures/sample_data/test_aoi_data.xlsx")
    site_path = Path("tests/fixtures/sample_data/test_site_data.xlsx")
    result = run_legacy_analysis(aoi_path, site_path)
    out_path = Path("tests/fixtures/sample_data/golden_master.xlsx")
    result.to_excel(out_path, index=False)
    print(f"Golden master saved to {out_path} ({len(result)} rows)")
    print(f"AOI matched: {(result['AOI匹配状态'] == '已匹配').sum()}")
    print(f"Indoor with outdoor: {result['最近室外站_距离_米'].notna().sum()}")
