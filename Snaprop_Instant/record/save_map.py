import requests
from PIL import Image
from io import BytesIO
from pathlib import Path
from datetime import datetime
from config.path_config import MAP_PATH
from config.baidu_config import baidu_api_key
from llm.llm_manager import QianwenManager
import json
import re


def get_origin_place(place_name, city, status):  # 定位函数
    # 0. 预处理地址：兰谷路2777弄1号202室 -> 兰谷路2777弄1号
    # 移除室、层字样，通常保留到 号 或 弄 能获得更好的匹配结果
    clean_place_name = re.sub(r'\d+[室层楼](.*)', '', place_name)
    if not clean_place_name:
        clean_place_name = place_name

    # 1. 尝试地点检索 (Place Search API) - 适用于小区名、POI
    url = f"https://api.map.baidu.com/place/v2/search?query={clean_place_name}&region={city}&output=json&ak={baidu_api_key}"
    try:
        response = requests.get(url, timeout=5)
        result = response.json()
        if result.get('status') == 0 and result.get('results'):
            location = result['results'][0]['location']
            if status == 0:
                return f'{location["lng"]},{location["lat"]}'
            elif status == 1:
                return f'{location["lat"]},{location["lng"]}', [r['name'] for r in result['results']]
    except Exception as e:
        print(f"Baidu Place API error (Query: {clean_place_name}): {e}")

    # 2. 如果地点检索失败，尝试地理编码 (Geocoding API) - 适用于具体门牌号、路弄
    geocode_url = f"https://api.map.baidu.com/geocoding/v3/?address={place_name}&city={city}&output=json&ak={baidu_api_key}"
    try:
        response = requests.get(geocode_url, timeout=5)
        result = response.json()
        if result.get('status') == 0 and result.get('result'):
            location = result['result']['location']
            if status == 0:
                return f'{location["lng"]},{location["lat"]}'
            elif status == 1:
                return f'{location["lat"]},{location["lng"]}', [place_name]
        else:
            print(f"Baidu Geocoding API failed (Status: {result.get('status', 'None')}, Msg: {result.get('message', 'None')})")
    except Exception as e:
        print(f"Baidu Geocoding API error (Addr: {place_name}): {e}")

    # 都失败了才返回 None
    if status == 1:
        return None, None
    return None


def get_nearby_places(location, search_place_name, radius=2000):  # 搜索函数
    url = f"https://api.map.baidu.com/place/v2/search?location={location}&radius={radius}&query={search_place_name}&output=json&ak={baidu_api_key}"
    try:
        response = requests.get(url, timeout=5)
        result = response.json()
        if result.get('status') == 0 and result.get('results'):
            return [r['name'] for r in result['results']]
    except Exception as e:
        print(f"Baidu Nearby Search error: {e}")
    return []


def map_location(location):
    if not location:
        return None
    url = f"https://api.map.baidu.com/staticimage/v2?ak={baidu_api_key}&width=512&height=400&zoom=16&scale=2&center={location}&markers={location}"
    # 发送HTTP GET请求获取图片
    try:
        response = requests.get(url, timeout=10)
        # 检查请求是否成功
        if response.status_code == 200:
            # 将响应内容转换为二进制流
            image_data = BytesIO(response.content)
            # 打开二进制流中的图片
            image = Image.open(image_data)
            # 保存图片到本地
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            # 使用pathlib处理路径
            image_path = Path(MAP_PATH) / filename
            image.save(image_path)
            print(f"位置图下载成功: {image_path}")
            return image_path
        else:
            print(f"位置图下载失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"位置图下载出错: {e}")
        return None


def map_main(place_name, city):
    location = get_origin_place(place_name, city, 0)
    # print(location)
    return map_location(location)


def nearby_list(loc, city):
    location, origin_places = get_origin_place(loc, city, 1)
    if location:
        nearby_places = get_nearby_places(location, "住宅区")
        # nearby_places.append(loc)
        nearby_list = QianwenManager().get_near_loc(str(nearby_places))
        try:
            list = json.loads(json.dumps(eval(nearby_list)))
            return list
        except:
            print(f"预期为二维列表，实际为{nearby_list}")
            return None
    else:
        print("百度地图api出错")
        return None


def environment_main(place_name, city):
    search_place_name = '住宅区'
    search_hospital = '医院'
    search_school = '学校'
    search_transportation = '交通设施'
    location, origin_places = get_origin_place(place_name, city, 1)
    if location:
        nearby_places = get_nearby_places(location, search_place_name)
        hospital = get_nearby_places(location, search_hospital)
        school = get_nearby_places(location, search_school)
        transportation = get_nearby_places(location, search_transportation)
        result = QianwenManager().get_environment(nearby_places, hospital, school)
        print(result)
        return result if result else "暂无该地区的详细环境评估。"
    else:
        print('未定位到小区')
        return "未能精确定位到小区位置，无法提供详细环境评估。"


if __name__ == '__main__':
    # print(nearby_list("世茂滨江花园", "上海"))
    environment_main("世茂滨江花园", "上海")
