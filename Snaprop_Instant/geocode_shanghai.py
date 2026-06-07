"""
使用百度地图 API 为 shanghai 表中缺失经纬度的记录进行地理编码。
- 优先从 house_loc 提取小区名 → "上海市 + 小区名"
- 否则用 house_position → "上海市 + 区 + 板块"
- 调用百度地图地理编码 API 获取坐标
"""
import pymysql
import requests
import time
import re
import os
from database.mysql_manager import MySQLManager

BAIDU_AK = os.getenv("BAIDU_MAP_API", "")

# 缓存：地址 → (lng, lat)
geo_cache = {}


def baidu_geocode(address):
    """调用百度地图地理编码 API。"""
    if address in geo_cache:
        return geo_cache[address]

    url = "https://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": address,
        "city": "上海市",
        "output": "json",
        "ak": BAIDU_AK,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == 0 and data.get("result"):
            loc = data["result"]["location"]
            result = (loc["lng"], loc["lat"])
            geo_cache[address] = result
            return result
        else:
            print(f"    ⚠ API返回异常: {data.get('message', 'unknown')} (addr={address})")
            return None
    except Exception as e:
        print(f"    ⚠ 请求失败: {e}")
        return None


def extract_community_name(house_loc):
    """
    从房源标题中提取可能的小区名。
    小区名通常以: 苑/花园/城/园/邸/名苑/新村/花苑/家园/公寓/庭/庐/湾/坊/里 等结尾
    """
    if not house_loc:
        return None

    # 小区名常见后缀模式
    community_suffixes = [
        "名苑", "花苑", "花园", "家园", "新苑", "佳苑", "雅苑", "馨苑",
        "新村", "花城", "新城", "公寓", "别墅", "华庭", "豪庭", "嘉园",
        "豪园", "华府", "星城", "绿洲", "名邸",
    ]

    # 后缀关键词（单字结尾）
    single_suffixes = ["苑", "园", "城", "邸", "庭", "庐", "湾", "坊", "里", "村", "庄", "馆"]

    # 1. 先尝试匹配包含已知后缀的短语
    # 匹配模式: 2-8个中文字符 + 后缀
    # 例如: "招商臻境" → "臻境" 以 "境" 结尾不常见，但 "招商臻境" 是完整小区名
    # 更通用: 找所有连续2-8个中文字符，然后测试是否像小区名

    # 尝试 "名词+后缀" 模式
    all_suffixes = community_suffixes + single_suffixes
    for suffix in sorted(all_suffixes, key=len, reverse=True):
        pattern = rf'([一-龥]{{1,6}}{suffix})'
        matches = re.findall(pattern, house_loc)
        for m in matches:
            if 3 <= len(m) <= 8:
                return m

    # 2. 尝试找 "XX·XX" 模式（如 "安高·申陇院"）
    dot_match = re.search(r'([一-龥]+·[一-龥]+)', house_loc)
    if dot_match:
        return dot_match.group(1)

    # 3. 尝试找 "XX区" / "XX路" 后的名称
    road_match = re.search(r'([一-龥]{2,6}(?:路|弄|街))\s*[\d号]', house_loc)
    if road_match:
        return road_match.group(1) + "附近"

    return None


def build_search_address(row):
    """根据记录构建用于地理编码的地址。"""
    house_id = row[0]
    house_loc = row[1]
    house_position = row[2]

    # 1. 优先尝试从标题提取小区名
    community = extract_community_name(house_loc)
    if community:
        if not community.startswith("上海"):
            # 加上区域前缀提高准确度
            district = ""
            if house_position:
                parts = house_position.split()
                if parts:
                    district = parts[0]  # 如 "浦东"
            return f"上海市{district}{community}"
        return f"上海市{community}"

    # 2. 用 house_position（区+板块）做区域级地理编码
    if house_position:
        return f"上海市{house_position.replace(' ', '')}"

    return None


def main():
    if not BAIDU_AK:
        print("❌ 请设置环境变量 BAIDU_MAP_API")
        return

    m = MySQLManager()
    conn = pymysql.connect(
        host=m._host, port=m._port, user=m._username, password=m._password,
        database=m._db, charset='utf8mb4'
    )
    cur = conn.cursor()

    # 获取所有缺失坐标的记录
    cur.execute("""
        SELECT house_id, house_loc, house_position
        FROM shanghai
        WHERE lng IS NULL OR lat IS NULL
    """)
    records = cur.fetchall()
    print(f"需要地理编码的记录: {len(records)} 条")

    # 先去重用 address → house_ids 映射
    addr_to_ids = {}
    for row in records:
        addr = build_search_address(row)
        if addr:
            addr_to_ids.setdefault(addr, []).append(row[0])

    print(f"去重后需查询的地址: {len(addr_to_ids)} 个")

    # 批量地理编码
    success_count = 0
    fail_count = 0

    for i, (addr, house_ids) in enumerate(addr_to_ids.items()):
        print(f"\n[{i+1}/{len(addr_to_ids)}] {addr}")
        print(f"  影响 {len(house_ids)} 条记录: {house_ids[:5]}...")

        coords = baidu_geocode(addr)
        if coords:
            lng, lat = coords
            print(f"  → ({lng}, {lat})")
            # 更新所有匹配的记录
            for hid in house_ids:
                cur.execute(
                    "UPDATE shanghai SET lng = %s, lat = %s WHERE house_id = %s",
                    (lng, lat, hid)
                )
            conn.commit()
            success_count += len(house_ids)
        else:
            fail_count += len(house_ids)
            print(f"  → 失败")

        # API 限流：每秒最多查询几次
        if i < len(addr_to_ids) - 1:
            time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"成功: {success_count} 条")
    print(f"失败: {fail_count} 条")

    # 验证
    cur.execute("SELECT COUNT(*) FROM shanghai WHERE lng IS NULL OR lat IS NULL")
    remaining = cur.fetchone()[0]
    print(f"剩余缺失: {remaining} 条")

    cur.close()
    conn.close()
    m.close()

    print("\n✅ 地理编码完成！")


if __name__ == "__main__":
    main()
