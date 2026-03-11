import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径，以便导入其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from report.ocr import OCR_Table
    from config.path_config import UPLOAD_FOLDER
except ImportError as e:
    print(f"导入模块失败: {str(e)}")
    sys.exit(1)

def test_single_image_ocr(image_name):
    print(f"开始测试图片: {image_name}")
    
    # 构造图片完整路径
    image_path = os.path.join("static", "uploads", image_name)
    
    if not os.path.exists(image_path):
        print(f"错误: 图片文件 {image_path} 不存在")
        return

    try:
        # 初始化 OCR 处理器
        ocr = OCR_Table()
        
        print("正在进行 OCR 提取 (trans_to_str)...")
        result_str = ocr.trans_to_str(image_path)
        
        if result_str:
            result_json = json.loads(result_str)
            print("OCR 提取成功！")
            # 打印部分结果以防太多
            print("提取结果概要:")
            # 尝试提取文本内容
            try:
                content = result_json.get('body', {}).get('Data', {}).get('Content', '')
                if not content:
                    # 尝试从 SubImages 中获取
                    sub_images = result_json.get('body', {}).get('Data', {}).get('SubImages', [])
                    if sub_images:
                        print(f"找到 {len(sub_images)} 个子图数据")
                        # 打印子图中的文本内容摘要
                        for i, sub in enumerate(sub_images):
                            print(f"子图 {i}:")
                            kv_info = sub.get('KVInfo', {}).get('KVList', [])
                            if kv_info:
                                print(f"  找到 {len(kv_info)} 个键值对")
                                for kv in kv_info[:5]: # 只看前5条
                                    print(f"    {kv.get('Key', '')}: {kv.get('Value', '')}")
                else:
                    print(f"提取全文内容 (前200字符): {content[:200]}...")
            except Exception as e:
                print(f"解析概要时出错: {e}")
                
            # 保存完整结果到 json 文件以便查看
            output_json = f"test_ocr_result_{Path(image_name).stem}.json"
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, ensure_ascii=False, indent=4)
            print(f"完整提取结果已保存至: {output_json}")
            
            # 测试转为 XLSX
            print("\n正在测试转为 Excel (trans_to_xlsx)...")
            save_path = ocr.trans_to_xlsx(image_name)
            print(f"Excel 文件已保存至: {save_path}")
            
        else:
            print("OCR 提取返回空结果")

    except Exception as e:
        print(f"执行 OCR 测试时发生异常: {str(e)}")

if __name__ == "__main__":
    target_image = "20250306195825_cropped_image.png"
    test_single_image_ocr(target_image)
