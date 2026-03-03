"""
房估宝 - 房产估值新范式
主程序入口
"""
import os
import sys
import json
import argparse
import base64
from datetime import datetime

# 确保可以导入其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from llm.multimodal_encoder import MultimodalEncoder
    from llm.llm_enhancer import LLMEnhancer
    from rules.differentiable_rule import DifferentiableRuleLearningFramework, create_example_rules
    from price.imca import IMCA
except ImportError as e:
    print(f"导入模块失败: {str(e)}")
    print("请确保已安装所有依赖项，并且所有模块都存在")
    sys.exit(1)

def get_base64_image(image_path):
    """将图片文件转换为 Base64 字符串"""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        if ext not in ['jpg', 'jpeg', 'png', 'gif']:
            ext = 'jpeg'
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/{ext};base64,{encoded_string}"
    except Exception as e:
        print(f"Error encoding image to base64: {e}")
        return None

class PropertyValuationSystem:
    """
    房产估值系统
    """
    def __init__(self):
        """初始化房产估值系统"""
        print("初始化房产估值系统...")
        
        # 创建多模态编码器
        self.multimodal_encoder = MultimodalEncoder()
        
        # 创建LLM增强器
        self.llm_enhancer = LLMEnhancer()
        
        # 创建规则框架
        self.rule_framework = None
        try:
            # 尝试加载规则框架
            rules_dir = os.path.join("rules", "trained_rules")
            if os.path.exists(rules_dir):
                self.rule_framework = DifferentiableRuleLearningFramework.load(rules_dir)
                print("已加载训练好的规则框架")
            else:
                # 创建示例规则
                print("创建示例规则框架...")
                self.rule_framework = DifferentiableRuleLearningFramework()
                example_rules = create_example_rules()
                self.rule_framework.add_rule_set(example_rules)
                
                # 保存示例规则
                os.makedirs(rules_dir, exist_ok=True)
                self.rule_framework.save(rules_dir)
                print("已创建并保存示例规则框架")
        except Exception as e:
            print(f"初始化规则框架失败: {str(e)}")
            self.rule_framework = None
        
        # 创建IMCA估值器
        self.imca = IMCA(rule_framework=self.rule_framework)
        
        print("房产估值系统初始化完成")
    
    def process_property_data(self, property_data):
        """
        处理房产数据
        
        Args:
            property_data: 房产数据，包含以下字段：
                - property_cert_image: 房产证图片路径（可选）
                - property_photo: 房屋外观图片路径（可选）
                - property_text: 房产描述文本（可选）
                - address: 房产地址
                - city: 所在城市
            
        Returns:
            dict: 处理结果
        """
        print("处理房产数据...")
        
        # 使用多模态编码器处理房产数据
        multimodal_result = self.multimodal_encoder.process_property_data(
            property_cert_image=property_data.get('property_cert_image'),
            property_photo=property_data.get('property_photo'),
            property_text=property_data.get('property_text'),
            address=property_data.get('address'),
            city=property_data.get('city')
        )
        
        # 使用LLM增强信息
        enhanced_result = self.llm_enhancer.process_and_enhance(multimodal_result)
        
        return enhanced_result
    
    def estimate_property_value(self, target_property, comparable_cases=None, pro_adjustments=None):
        """
        估算房产价值
        
        Args:
            target_property: 目标房产数据
            comparable_cases: 可比案例数据（可选）
            pro_adjustments: 专业调整参数 (可选)
            
        Returns:
            dict: 估值结果
        """
        print("估算房产价值...")
        
        # 如果没有提供可比案例，使用默认的示例案例
        if comparable_cases is None or len(comparable_cases) == 0:
            print("未提供可比案例，使用示例案例...")
            comparable_cases = [
                {
                    'price': 50000,
                    'size': 90,
                    'floor': '中楼层',
                    'fitment': '精装',
                    'built_time': '2015',
                    'transaction_time': '2023-01-01',
                    'green_rate': 0.3,
                    'address': '示例小区B',
                    'transaction_type': 1
                },
                {
                    'price': 45000,
                    'size': 120,
                    'floor': '低楼层',
                    'fitment': '简装',
                    'built_time': '2010',
                    'transaction_time': '2023-03-01',
                    'green_rate': 0.25,
                    'address': '示例小区B',
                    'transaction_type': 1
                },
                {
                    'price': 55000,
                    'size': 75,
                    'floor': '高楼层',
                    'fitment': '精装',
                    'built_time': '2018',
                    'transaction_time': '2023-02-01',
                    'green_rate': 0.35,
                    'address': '示例小区C',
                    'transaction_type': 1
                }
            ]
        
        # 使用IMCA估算房产价值
        estimation_result = self.imca.estimate(target_property, comparable_cases, pro_adjustments=pro_adjustments)
        
        # 生成估值解释
        explanation = self.imca.generate_explanation(estimation_result, target_property, comparable_cases)
        estimation_result['explanation'] = explanation
        
        if pro_adjustments:
            estimation_result['explanation'] += "\n\n【专业调整已应用】\n根据手动设置的专业调整参数对相似度计算及修正系数进行了微调。"
        
        return estimation_result
    
    def generate_report(self, property_data, estimation_result, target_property=None, price_prediction=None, pdf_url=None):
        """
        生成房产估值报告
        
        Args:
            property_data: 房产数据
            estimation_result: 估值结果
            target_property: 目标房产数据（可选）
            price_prediction: 房价预测数据（可选）
            pdf_url: PDF文件的URL路径（可选）
            
        Returns:
            str: 报告文件路径
        """
        print("生成房产估值报告...")
        
        # 创建报告目录
        reports_dir = os.path.join("static", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_filename = f"property_valuation_report_{timestamp}.json"
        report_path = os.path.join(reports_dir, report_filename)
        
        # 转换并存储图片的 Base64 数据，以便在删除本地文件后仍能查看报告
        cert_img_b64 = get_base64_image(property_data.get('property_cert_image'))
        photo_img_b64 = get_base64_image(property_data.get('property_photo'))
        map_img_b64 = None
        # 如果 property_data 本身包含 map_image 或从处理后的原始数据中提取
        map_path = property_data.get('map_image') # 可能由 api 填充
        if map_path:
            map_img_b64 = get_base64_image(map_path)

        # 构建报告数据
        report_data = {
            "property_data": property_data,
            "target_property": target_property,
            "estimation_result": estimation_result,
            "price_prediction": price_prediction,
            "pdf_url": pdf_url,
            "generated_at": timestamp,
            "report_id": f"REPORT_{timestamp}",
            "embedded_images": {
                "cert_image": cert_img_b64,
                "photo_image": photo_img_b64,
                "map_image": map_img_b64
            }
        }
        
        # 保存报告
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"报告已生成: {report_path}")
        return report_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="房估宝 - 房产估值新范式")
    parser.add_argument("--address", help="房产地址", required=True)
    parser.add_argument("--city", help="所在城市", required=True)
    parser.add_argument("--area", help="房屋面积（平方米）", type=float, required=True)
    parser.add_argument("--floor", help="楼层（低楼层/中楼层/高楼层）", default="中楼层")
    parser.add_argument("--fitment", help="装修情况（毛坯/简装/精装）", default="简装")
    parser.add_argument("--year", help="建成年份", type=int, default=2015)
    parser.add_argument("--cert", help="房产证图片路径")
    parser.add_argument("--photo", help="房屋外观图片路径")
    parser.add_argument("--text", help="房产描述文本")
    
    args = parser.parse_args()
    
    # 创建房产估值系统
    system = PropertyValuationSystem()
    
    # 准备房产数据
    property_data = {
        "address": args.address,
        "city": args.city,
        "property_cert_image": args.cert,
        "property_photo": args.photo,
        "property_text": args.text
    }
    
    # 处理房产数据
    processed_data = system.process_property_data(property_data)
    
    # 准备目标房产数据
    raw_green = processed_data.get("enhanced_data", {}).get("property_info", {}).get("green_rate", 0.2)
    green_val = 0.2
    try:
        if isinstance(raw_green, str):
            if '%' in raw_green:
                green_val = float(raw_green.replace('%', '')) / 100.0
            else:
                val = float(raw_green)
                green_val = val / 100.0 if val > 1 else val
        else:
            val = float(raw_green)
            green_val = val / 100.0 if val > 1 else val
    except:
        green_val = 0.2

    target_property = {
        "size": args.area,
        "floor": args.floor,
        "fitment": args.fitment,
        "built_time": str(args.year),
        "green_rate": green_val,
        "transaction_type": 1
    }
    
    # 估算房产价值
    estimation_result = system.estimate_property_value(target_property)
    
    # 生成报告
    report_path = system.generate_report(property_data, estimation_result, target_property)
    
    # 打印估值结果
    print("\n===== 房产估值结果 =====")
    print(f"估计单价: {estimation_result['estimated_price']:.2f} 元/平方米")
    print(f"置信度: {estimation_result['confidence']:.2%}")
    print(f"总价: {estimation_result['estimated_price'] * args.area:.2f} 元")
    print("\n===== 估值解释 =====")
    print(estimation_result['explanation'])
    print(f"\n报告已保存至: {report_path}")

if __name__ == "__main__":
    main()