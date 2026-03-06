"""
本模块包含多模态编码器类，用于处理房产估值的多模态信息
"""
import os
import re
import json
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from datetime import datetime
from config.path_config import MAP_PATH
from config.baidu_config import baidu_api_key

import time

class VisualEncoder:
    """
    视觉编码器类，用于处理房产相关图片
    """
    def __init__(self):
        """初始化视觉编码器"""
        pass

class TextEncoder:
    """
    文本编码器类，用于处理房产描述文本
    """
    def __init__(self):
        """初始化文本编码器"""
        pass

class SpatialEncoder:
    """
    空间编码器类，用于处理地理位置信息
    """
    def __init__(self):
        """初始化空间编码器"""
        self.api_key = baidu_api_key  # 百度地图API密钥
    
    def geocode(self, address, city):
        """
        地理编码，将地址转换为经纬度
        
        Args:
            address: 地址
            city: 城市
            
        Returns:
            tuple: (经度, 纬度)
        """
        url = f"https://api.map.baidu.com/geocoding/v3/?address={address}&city={city}&output=json&ak={self.api_key}"
        try:
            response = requests.get(url)
            result = response.json()
            if result.get('status') == 0:
                location = result['result']['location']
                return location['lng'], location['lat']
            else:
                print(f"地理编码失败: {result.get('message')}")
                return None, None
        except Exception as e:
            print(f"地理编码请求出错: {str(e)}")
            return None, None
    
    def generate_map_image(self, lng, lat):
        """
        生成地图图片
        
        Args:
            lng: 经度
            lat: 纬度
            
        Returns:
            str: 图片路径
        """
        url = f"https://api.map.baidu.com/staticimage/v2?ak={self.api_key}&width=512&height=400&zoom=16&center={lng},{lat}&markers={lng},{lat}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # 将响应内容转换为二进制流
                image_data = BytesIO(response.content)
                # 打开二进制流中的图片
                image = Image.open(image_data)
                # 保存图片到本地
                filename = f"map_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                # 使用pathlib处理路径
                image_path = os.path.join(MAP_PATH, filename)
                image.save(image_path)
                print(f"地图图片生成成功: {image_path}")
                return image_path
            else:
                print(f"地图图片生成失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"地图图片生成出错: {str(e)}")
            return None


class MultimodalEncoder:
    """
    多模态编码器，整合视觉、文本和空间编码器
    """
    def __init__(self):
        """初始化多模态编码器"""
        self.visual_encoder = VisualEncoder()
        self.text_encoder = TextEncoder()
        self.spatial_encoder = SpatialEncoder()
    
    def process_property_data(self, property_cert_image=None, property_photo=None, property_text=None, address=None, city=None):
        """
        处理房产数据
        
        Args:
            property_cert_image: 房产证图片路径
            property_photo: 房屋外观图片路径
            property_text: 房产描述文本
            address: 房产地址
            city: 所在城市
            
        Returns:
            dict: 处理结果
        """
        result = {}
        
        # 处理地理位置和生成地图
        if address and city:
            start_geo = time.time()
            lng, lat = self.spatial_encoder.geocode(address, city)
            
            if lng and lat:
                result["location"] = {"lng": lng, "lat": lat}
                
                # 生成地图图片 (报告中需要用到)
                start_map = time.time()
                map_image = self.spatial_encoder.generate_map_image(lng, lat)
                
                if map_image:
                    result["map_image"] = map_image
        
        return result 