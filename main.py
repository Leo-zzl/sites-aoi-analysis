import time
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads
import warnings

warnings.filterwarnings("ignore")

# ======================================
# 【路径配置】
# ======================================
AOI_FILE = r'AOI样例数据.xlsx'
CELL_FILE = r'基站站点样例数据.xlsx'
RESULT_FILE = r'小区_AOI匹配_1000米限制_' + time.strftime("%Y%m%d_%H%M%S") + '.xlsx'

# 列名配置
COL_COVER_TYPE = '覆盖类型'        # 区分室内外的列
VAL_INDOOR = '室内'                # 室内站标识（包含室分）
VAL_OUTDOOR = '室外'               # 室外站标识（宏站）
COL_FREQ = '使用频段'              # 频段列名
COL_SITE_NAME = '小区名称'         # 站点名称列名
MAX_SEARCH_DISTANCE = 1000         # 【关键参数】搜索半径：1000米

# 室内/室外兼容值
INDOOR_VALS = {'室内', '室分', '室分系统', 'Indoor', 'indoor'}
OUTDOOR_VALS = {'室外', '宏站', '微站', '杆站', 'Outdoor', 'outdoor', '宏蜂窝', '微蜂窝'}


def find_lat_lon_columns(df):
    """根据常见关键词自动识别经纬度列"""
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
    """根据经纬度自动计算UTM投影坐标系EPSG代码"""
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:326{zone:02d}" if lat >= 0 else f"EPSG:327{zone:02d}"


def classify_cover_type(x):
    """判断覆盖类型是室内、室外还是未知"""
    val = str(x).strip()
    if val in INDOOR_VALS:
        return 'indoor'
    if val in OUTDOOR_VALS:
        return 'outdoor'
    return 'unknown'


# ======================================
# 1. 读取 AOI 数据
# ======================================
print("🔵 加载 AOI 数据...")
df_aoi = pd.read_excel(AOI_FILE, sheet_name=0)
print(f"✅ AOI 表格总行数：{len(df_aoi)}")

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
    except Exception as e:
        print(f"⚠️ AOI解析失败 行{idx + 2}: {e}")

gdf_aoi = gpd.GeoDataFrame(aoi_records, crs="EPSG:4326")
print(f"🎯 有效AOI数量：{len(gdf_aoi)}")

# ======================================
# 2. 读取站点数据
# ======================================
print("\n🔵 加载站点数据...")
df_cell = pd.read_excel(CELL_FILE, sheet_name=0)
print(f"✅ 站点总数：{len(df_cell):,}")

# 检查必需列
for col in [COL_SITE_NAME, COL_FREQ, COL_COVER_TYPE]:
    if col not in df_cell.columns:
        raise KeyError(f"❌ 找不到列 '{col}'")

# 识别经纬度列
lat_col, lon_col = find_lat_lon_columns(df_cell)
if lat_col is None or lon_col is None:
    # 回退到硬编码位置（纬度D列idx3，经度F列idx5）
    lat_col = df_cell.columns[3]
    lon_col = df_cell.columns[5]
    print(f"   ⚠️ 未自动识别经纬度列，回退到位置: [{lon_col}, {lat_col}]")
else:
    print(f"   经纬度列: [{lon_col}, {lat_col}]")

# 清洗坐标（去除空值和非数字）
df_cell[lon_col] = pd.to_numeric(df_cell[lon_col], errors='coerce')
df_cell[lat_col] = pd.to_numeric(df_cell[lat_col], errors='coerce')
valid_coord_mask = df_cell[lon_col].notna() & df_cell[lat_col].notna()
if (~valid_coord_mask).sum() > 0:
    print(f"   ⚠️ 发现 {(~valid_coord_mask).sum()} 条无效坐标记录，已过滤")
    df_cell = df_cell[valid_coord_mask].reset_index(drop=True)

# 创建GeoDataFrame
gdf_cell = gpd.GeoDataFrame(
    df_cell,
    geometry=gpd.points_from_xy(df_cell[lon_col], df_cell[lat_col]),
    crs="EPSG:4326"
)

# 自动确定UTM坐标系
centroid_lon = gdf_cell.geometry.x.median()
centroid_lat = gdf_cell.geometry.y.median()
CRS_METER = get_utm_epsg(centroid_lon, centroid_lat)
print(f"   自动选择投影坐标系: {CRS_METER} (中心经度: {centroid_lon:.2f})")

# ======================================
# 3. AOI空间匹配（所有站点）
# ======================================
print("\n🚀 执行AOI空间匹配...")
t0 = time.time()

joined_aoi = gpd.sjoin(
    gdf_cell[['geometry']],
    gdf_aoi[['aoi_province', 'aoi_city', 'aoi_scene', 'aoi_scene_big', 'aoi_scene_small', 'geometry']],
    how="left",
    predicate="within"
)
# 去重：重叠AOI取第一个
joined_aoi = joined_aoi[~joined_aoi.index.duplicated(keep='first')]

# 合并结果（按原始索引对齐）
df_cell["AOI_省"] = joined_aoi["aoi_province"].reindex(df_cell.index).fillna("").values
df_cell["AOI_市"] = joined_aoi["aoi_city"].reindex(df_cell.index).fillna("").values
df_cell["AOI_场景"] = joined_aoi["aoi_scene"].reindex(df_cell.index).fillna("").values
df_cell["AOI_场景大类"] = joined_aoi["aoi_scene_big"].reindex(df_cell.index).fillna("").values
df_cell["AOI_场景小类"] = joined_aoi["aoi_scene_small"].reindex(df_cell.index).fillna("").values
df_cell["AOI匹配状态"] = df_cell["AOI_场景"].apply(lambda x: "已匹配" if x and x != "" else "未匹配")

print(f"   AOI匹配耗时: {time.time() - t0:.2f}秒")
print(f"   已匹配AOI: {(df_cell['AOI匹配状态'] == '已匹配').sum()}")

# ======================================
# 4. 室内站最近室外站分析（1000米限制）
# ======================================
print("\n🏠 识别室内/室外站...")
df_cell['site_type'] = df_cell[COL_COVER_TYPE].apply(classify_cover_type)

indoor_mask = df_cell['site_type'] == 'indoor'
outdoor_mask = df_cell['site_type'] == 'outdoor'

print(f"   室内站数量：{indoor_mask.sum():,}")
print(f"   室外站数量：{outdoor_mask.sum():,}")
print(f"   未知类型：{(df_cell['site_type'] == 'unknown').sum():,}")

# 初始化结果列
df_cell["最近室外站_名称"] = ""
df_cell["最近室外站_频段"] = ""
df_cell["最近室外站_距离_米"] = pd.NA

if indoor_mask.sum() > 0 and outdoor_mask.sum() > 0:
    t1 = time.time()
    print(f"\n🔄 转换坐标系至米制({CRS_METER})...")

    # 直接投影整个gdf_cell，然后按索引切片（避免重复投影）
    gdf_cell_m = gdf_cell.to_crs(CRS_METER)
    gdf_indoor_m = gdf_cell_m[indoor_mask].copy()
    gdf_outdoor_m = gdf_cell_m[outdoor_mask].copy()

    # 提取numpy坐标数组
    indoor_coords = np.column_stack([gdf_indoor_m.geometry.x.values, gdf_indoor_m.geometry.y.values])
    outdoor_coords = np.column_stack([gdf_outdoor_m.geometry.x.values, gdf_outdoor_m.geometry.y.values])
    outdoor_names = gdf_outdoor_m[COL_SITE_NAME].values
    outdoor_freqs = gdf_outdoor_m[COL_FREQ].values

    print(f"🎯 计算室内站→最近室外站（限制{MAX_SEARCH_DISTANCE}米）...")

    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(outdoor_coords)
        distances, indices = tree.query(indoor_coords, k=1, distance_upper_bound=MAX_SEARCH_DISTANCE)

        valid_mask = indices < len(outdoor_coords)
        valid_count = valid_mask.sum()

        # 写回结果
        indoor_indices = gdf_indoor_m.index
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_名称"] = outdoor_names[indices[valid_mask]]
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_频段"] = outdoor_freqs[indices[valid_mask]]
        df_cell.loc[indoor_indices[valid_mask], "最近室外站_距离_米"] = distances[valid_mask]

        print(f"   ✓ 1000米内找到室外站：{valid_count}/{len(indoor_coords):,}个")
        if valid_count > 0:
            print(f"   平均距离：{distances[valid_mask].mean():.1f}米")
            print(f"   中位距离：{np.median(distances[valid_mask]):.1f}米")
            print(f"   最大距离（≤1000米）：{distances[valid_mask].max():.1f}米")

    except ImportError:
        print("   ⚠️ 未安装 scipy，回退到 geopandas sjoin_nearest（大数据量时极慢，建议: pip install scipy）")
        gdf_outdoor_m = gdf_outdoor_m[[COL_SITE_NAME, COL_FREQ, 'geometry']].rename(columns={
            COL_SITE_NAME: 'outdoor_name',
            COL_FREQ: 'outdoor_freq'
        })
        nearest = gpd.sjoin_nearest(
            gdf_indoor_m,
            gdf_outdoor_m,
            how="left",
            distance_col="距离_米"
        )
        nearest = nearest[~nearest.index.duplicated(keep='first')]
        over_limit = nearest["距离_米"] > MAX_SEARCH_DISTANCE
        nearest.loc[over_limit, "outdoor_name"] = None
        nearest.loc[over_limit, "outdoor_freq"] = None
        nearest.loc[over_limit, "距离_米"] = None

        df_cell.loc[nearest.index, "最近室外站_名称"] = nearest["outdoor_name"].fillna("").values
        df_cell.loc[nearest.index, "最近室外站_频段"] = nearest["outdoor_freq"].fillna("").values
        df_cell.loc[nearest.index, "最近室外站_距离_米"] = nearest["距离_米"].values

        valid_count = (~over_limit).sum()
        print(f"   ✓ 1000米内找到室外站：{valid_count}/{len(nearest):,}个")

    print(f"   最近邻计算耗时: {time.time() - t1:.2f}秒")

# ======================================
# 5. 整理输出
# ======================================
print("\n📊 整理输出...")

front_cols = [
    "AOI_省", "AOI_市", "AOI_场景", "AOI_场景大类", "AOI_场景小类", "AOI匹配状态",
    "最近室外站_名称", "最近室外站_频段", "最近室外站_距离_米"
]
other_cols = [c for c in df_cell.columns if c not in front_cols and c not in ['geometry', 'site_type']]
df_output = df_cell[front_cols + other_cols].copy()

# 删除临时列
for col in ['geometry', 'site_type']:
    if col in df_output.columns:
        df_output = df_output.drop(columns=[col])

# ======================================
# 6. 保存结果
# ======================================
print(f"\n💾 保存至: {RESULT_FILE}")
df_output.to_excel(RESULT_FILE, index=False, engine="openpyxl")

# 统计摘要
print("\n📈 结果统计：")
print(f"   总站点数：{len(df_output):,}")
print(f"   AOI已匹配：{(df_output['AOI匹配状态'] == '已匹配').sum():,}")

indoor_total = indoor_mask.sum()
indoor_with_outdoor = df_output["最近室外站_距离_米"].notna().sum()
print(f"   室内站总数：{indoor_total:,}")
print(f"   1000米内找到室外站：{indoor_with_outdoor:,}")
print(f"   1000米内未找到室外站：{indoor_total - indoor_with_outdoor:,}")

print(f"\n🎉 完成！文件路径：{RESULT_FILE}")
