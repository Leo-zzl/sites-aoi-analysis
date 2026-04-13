import time
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads
import warnings
warnings.filterwarnings("ignore")

# ======================================
# 【路径配置】
# ======================================
AOI_FILE = r'基站站点样例数据.xlsx'
CELL_FILE = r'AOI样例数据.xlsx'
RESULT_FILE = r'小区_AOI匹配_1000米限制_' + time.strftime("%Y%m%d_%H%M%S") + '.xlsx'

# 列名配置
COL_COVER_TYPE = '覆盖类型'        # 区分室内外的列
VAL_INDOOR = '室内'                # 室内站标识（包含室分）
VAL_OUTDOOR = '室外'               # 室外站标识（宏站）
COL_FREQ = '使用频段'              # 频段列名
COL_SITE_NAME = '小区名称'         # 站点名称列名
CRS_METER = "EPSG:32650"           # 广东地区投影坐标系
MAX_SEARCH_DISTANCE = 1000         # 【关键参数】搜索半径：1000米

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
    indoor_outdoor = str(row.iloc[2]).strip()
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
        print(f"⚠️ AOI解析失败 行{idx+2}: {e}")

gdf_aoi = gpd.GeoDataFrame(aoi_records, crs="EPSG:4326")
print(f"🎯 有效AOI数量：{len(gdf_aoi)}")

# ======================================
# 2. 读取站点数据
# ======================================
print("\n🔵 加载站点数据...")
df_cell = pd.read_excel(CELL_FILE, sheet_name=0)
print(f"✅ 站点总数：{len(df_cell):,}")

# 检查列名
if COL_SITE_NAME not in df_cell.columns:
    raise KeyError(f"❌ 找不到列 '{COL_SITE_NAME}'")
if COL_FREQ not in df_cell.columns:
    raise KeyError(f"❌ 找不到列 '{COL_FREQ}'")
if COL_COVER_TYPE not in df_cell.columns:
    raise KeyError(f"❌ 找不到列 '{COL_COVER_TYPE}'")

# 识别经纬度列（根据样例：纬度D列idx3，经度F列idx5）
lat_col = df_cell.columns[3]
lon_col = df_cell.columns[5]
print(f"   经纬度列: [{lon_col}, {lat_col}]")

# 创建GeoDataFrame
gdf_cell = gpd.GeoDataFrame(
    df_cell,
    geometry=[Point(lon, lat) for lon, lat in zip(df_cell[lon_col], df_cell[lat_col])],
    crs="EPSG:4326"
)

# ======================================
# 3. AOI空间匹配（所有站点）
# ======================================
print("\n🚀 执行AOI空间匹配...")
joined_aoi = gpd.sjoin(
    gdf_cell,
    gdf_aoi[['aoi_province', 'aoi_city', 'aoi_scene', 'aoi_scene_big', 'aoi_scene_small', 'geometry']],
    how="left",
    predicate="within"
)
joined_aoi = joined_aoi[~joined_aoi.index.duplicated(keep='first')]

# 合并AOI结果到原始表
df_cell["AOI_省"] = joined_aoi["aoi_province"].reindex(df_cell.index).fillna("")
df_cell["AOI_市"] = joined_aoi["aoi_city"].reindex(df_cell.index).fillna("")
df_cell["AOI_场景"] = joined_aoi["aoi_scene"].reindex(df_cell.index).fillna("")
df_cell["AOI_场景大类"] = joined_aoi["aoi_scene_big"].reindex(df_cell.index).fillna("")
df_cell["AOI_场景小类"] = joined_aoi["aoi_scene_small"].reindex(df_cell.index).fillna("")
df_cell["AOI匹配状态"] = df_cell["AOI_场景"].apply(lambda x: "已匹配" if x and x != "" else "未匹配")

# ======================================
# 4. 室内站最近室外站分析（1000米限制）
# ======================================
print("\n🏠 识别室内/室外站...")

# 分离室内外（兼容多种写法：室内/室分 vs 室外/宏站/微站）
df_cell['is_indoor'] = df_cell[COL_COVER_TYPE].apply(
    lambda x: str(x).strip() in [VAL_INDOOR, '室内', '室分', '室分系统', 'Indoor']
)
df_cell['is_outdoor'] = df_cell[COL_COVER_TYPE].apply(
    lambda x: str(x).strip() in [VAL_OUTDOOR, '室外', '宏站', '微站', '杆站', 'Outdoor']
)

gdf_indoor = gdf_cell[df_cell['is_indoor']].copy()
gdf_outdoor = gdf_cell[df_cell['is_outdoor']].copy()

print(f"   室内站数量：{len(gdf_indoor)}")
print(f"   室外站数量：{len(gdf_outdoor)}")

# 初始化室内站关联字段（默认空值）
df_cell["最近室外站_名称"] = ""
df_cell["最近室外站_频段"] = ""
df_cell["最近室外站_距离_米"] = None

if len(gdf_indoor) > 0 and len(gdf_outdoor) > 0:
    print(f"\n🔄 转换坐标系至米制({CRS_METER})...")
    gdf_indoor_m = gdf_indoor.to_crs(CRS_METER)
    gdf_outdoor_m = gdf_outdoor.to_crs(CRS_METER)
    
    # 重命名右表列避免冲突
    gdf_outdoor_m = gdf_outdoor_m[[COL_SITE_NAME, COL_FREQ, 'geometry']].rename(columns={
        COL_SITE_NAME: 'outdoor_name',
        COL_FREQ: 'outdoor_freq'
    })
    
    print(f"🎯 计算室内站→最近室外站（限制{MAX_SEARCH_DISTANCE}米）...")
    
    # 最近邻查询
    nearest = gpd.sjoin_nearest(
        gdf_indoor_m,
        gdf_outdoor_m,
        how="left",
        distance_col="距离_米"
    )
    nearest = nearest[~nearest.index.duplicated(keep='first')]
    
    # 【关键修改】过滤1000米限制：超距离的视为未找到
    over_limit = nearest["距离_米"] > MAX_SEARCH_DISTANCE
    nearest.loc[over_limit, "outdoor_name"] = None
    nearest.loc[over_limit, "outdoor_freq"] = None
    nearest.loc[over_limit, "距离_米"] = None
    
    valid_count = (~over_limit).sum()
    print(f"   ✓ 1000米内找到室外站：{valid_count}/{len(nearest)}个")
    
    if valid_count > 0:
        valid_distances = nearest.loc[~over_limit, "距离_米"]
        print(f"   平均距离：{valid_distances.mean():.1f}米")
        print(f"   中位距离：{valid_distances.median():.1f}米")
        print(f"   最大距离（≤1000米）：{valid_distances.max():.1f}米")
    
    # 将有效结果写回全量表
    df_cell.loc[nearest.index, "最近室外站_名称"] = nearest["outdoor_name"].fillna("").values
    df_cell.loc[nearest.index, "最近室外站_频段"] = nearest["outdoor_freq"].fillna("").values
    df_cell.loc[nearest.index, "最近室外站_距离_米"] = nearest["距离_米"].values

# ======================================
# 5. 整理输出
# ======================================
print("\n📊 整理输出...")

# 列顺序
front_cols = [
    "AOI_省", "AOI_市", "AOI_场景", "AOI_场景大类", "AOI_场景小类", "AOI匹配状态",
    "最近室外站_名称", "最近室外站_频段", "最近室外站_距离_米"
]
other_cols = [c for c in df_cell.columns if c not in front_cols and c not in ['geometry', 'is_indoor', 'is_outdoor']]
df_output = df_cell[front_cols + other_cols]

# 删除临时列
for col in ['geometry', 'is_indoor', 'is_outdoor']:
    if col in df_output.columns:
        df_output = df_output.drop(columns=[col])

# ======================================
# 6. 保存结果
# ======================================
print(f"\n💾 保存至: {RESULT_FILE}")
df_output.to_excel(RESULT_FILE, index=False, engine="openpyxl")

# 统计摘要
print("\n📈 结果统计：")
print(f"   总站点数：{len(df_output)}")
print(f"   AOI已匹配：{(df_output['AOI匹配状态']=='已匹配').sum()}")
indoor_with_outdoor = df_output["最近室外站_距离_米"].notna().sum()
indoor_total = df_output["最近室外站_距离_米"].notna().sum() + (df_output["最近室外站_距离_米"].isna() & (df_output[COL_COVER_TYPE].apply(lambda x: str(x).strip() in [VAL_INDOOR, '室内', '室分']))).sum()
print(f"   室内站总数：{indoor_total}")
print(f"   1000米内找到室外站：{indoor_with_outdoor}")
print(f"   1000米内未找到室外站：{indoor_total - indoor_with_outdoor}")

print(f"\n🎉 完成！文件路径：{RESULT_FILE}")