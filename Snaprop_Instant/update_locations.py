"""
批量更新数据库中房产记录的经纬度
使用百度地图API获取位置信息
"""
import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.mysql_manager import MySQLManager
from record.save_map import get_origin_place
from config.baidu_config import baidu_api_key


def clean_address(addr):
    """清理地址，提取小区名"""
    if not addr:
        return None
    # 移除室、层、车位等
    addr = re.sub(r'\d+[室层楼车位号弄]', '', str(addr))
    # 保留到弄/号/路
    match = re.search(r'.+?(?:路|街|弄|号|巷)', addr)
    if match:
        return match.group(0)
    return addr[:20] if len(addr) > 20 else addr


def update_locations(city="上海", batch_size=50, max_records=500):
    """批量更新经纬度"""
    db = MySQLManager()
    
    print(f"开始获取 {city} 暂无位置信息的记录...")
    records = db.get_records_without_location(city, limit=max_records)
    
    if not records:
        print("没有需要更新的记录")
        db.close()
        return
    
    print(f"找到 {len(records)} 条需要更新位置的记录")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, record in enumerate(records):
        record_id = record['id']
        house_loc = record['house_loc']
        house_position = record['house_position']
        
        # 优先使用 house_position（通常是更精确的地址）
        address = house_position or house_loc
        clean_addr = clean_address(address)
        
        if not clean_addr:
            print(f"[{i+1}] 记录 {record_id}: 地址为空，跳过")
            fail_count += 1
            continue
        
        # 调用百度地图API获取经纬度
        try:
            # status=0 返回 lng,lat 格式
            result = get_origin_place(clean_addr, city, status=0)
            
            if result:
                lng, lat = result.split(',')
                lng = float(lng)
                lat = float(lat)
                
                # 更新数据库
                if db.update_location(city, record_id, lng, lat):
                    print(f"[{i+1}] 记录 {record_id}: {clean_addr} -> ({lng}, {lat}) ✓")
                    success_count += 1
                else:
                    print(f"[{i+1}] 记录 {record_id}: 数据库更新失败 ✗")
                    fail_count += 1
            else:
                print(f"[{i+1}] 记录 {record_id}: {clean_addr} -> API返回空 ✗")
                fail_count += 1
            
            # 避免API调用过快
            time.sleep(0.3)
            
        except Exception as e:
            print(f"[{i+1}] 记录 {record_id}: 错误 - {str(e)[:50]} ✗")
            fail_count += 1
        
        # 每批打印进度
        if (i + 1) % batch_size == 0:
            print(f"\n已完成 {i+1}/{len(records)}，成功: {success_count}，失败: {fail_count}")
            print("-" * 50)
    
    db.close()
    print("\n" + "=" * 50)
    print(f"完成！共处理 {len(records)} 条记录")
    print(f"成功: {success_count}，失败: {fail_count}")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="批量更新房产经纬度")
    parser.add_argument("--city", default="上海", help="城市名")
    parser.add_argument("--batch", type=int, default=50, help="每批数量")
    parser.add_argument("--max", type=int, default=500, help="最大处理数量")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("房产经纬度批量更新工具")
    print("=" * 50)
    update_locations(city=args.city, batch_size=args.batch, max_records=args.max)
