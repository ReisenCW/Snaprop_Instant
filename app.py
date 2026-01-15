"""
房估宝 - 房产估值新范式
Web应用入口
"""
import os
import sys
import json
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from price.careful_selection import careful_selection
from price.RealEstateValuation import RealEstateValuation
from record.record import Record
from database.mysql_manager import MySQLManager


try:
    from main import PropertyValuationSystem
    from llm_prediction.api import predict_region
    from database.mysql_manager import MySQLManager
    from price.imca import IMCA
    from price.careful_selection import careful_selection
except ImportError as e:
    print(f"导入模块失败: {str(e)}")
    print("请确保已安装所有依赖项，并且所有模块都存在")
    sys.exit(1)

# 创建Flask应用
app = Flask(__name__)

# 配置上传文件目录
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 创建房产估值系统
valuation_system = PropertyValuationSystem()

def extract_trend_factor(prediction_text):
    """
    从预测文本中提取趋势因子
    例如: "预计上涨 5%" -> (0.05, 0.05)
          "预计下跌 2.5%" -> (-0.025, -0.025)
          "预计上涨 3%-5%" -> (0.03, 0.05)
          "预计下跌 1%-2%" -> (-0.02, -0.01)
    返回: (min_factor, max_factor)
    """
    if not prediction_text:
        return 0.0, 0.0
    
    # 匹配范围模式，如 "3%-5%" 或 "3-5%"
    range_pattern = r'(\d+(?:\.\d+)?)(?:%|％)?\s*[-~至]\s*(\d+(?:\.\d+)?)(?:%|％)'
    
    # 匹配 "上涨" 或 "增长" 后跟范围
    rise_range_match = re.search(r'(?:上涨|增长|上升).*?' + range_pattern, prediction_text)
    if rise_range_match:
        min_val = float(rise_range_match.group(1)) / 100.0
        max_val = float(rise_range_match.group(2)) / 100.0
        return min_val, max_val

    # 匹配 "下跌" 或 "下降" 后跟范围
    fall_range_match = re.search(r'(?:下跌|下降|减少).*?' + range_pattern, prediction_text)
    if fall_range_match:
        # 注意：下跌时，数字大的代表跌幅大，即数值更小
        # 例如下跌 1%-2%，对应因子是 -0.01 和 -0.02
        # 范围应该是 [-0.02, -0.01]
        val1 = -float(fall_range_match.group(1)) / 100.0
        val2 = -float(fall_range_match.group(2)) / 100.0
        return min(val1, val2), max(val1, val2)

    # 如果没有匹配到范围，尝试匹配单个数值
    # 匹配 "上涨" 或 "增长" 后跟数字
    rise_match = re.search(r'(?:上涨|增长|上升).*?(\d+(?:\.\d+)?)%', prediction_text)
    if rise_match:
        val = float(rise_match.group(1)) / 100.0
        return val, val
        
    # 匹配 "下跌" 或 "下降" 后跟数字
    fall_match = re.search(r'(?:下跌|下降|减少).*?(\d+(?:\.\d+)?)%', prediction_text)
    if fall_match:
        val = -float(fall_match.group(1)) / 100.0
        return val, val
        
    return 0.0, 0.0

def allowed_file(filename):
    """检查文件是否允许上传"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

@app.route('/valuation')
def valuation():
    """估值页面"""
    return render_template('valuation.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件API"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件部分'})
    
    file = request.files['file']
    file_type = request.form.get('type', 'photo')  # 文件类型：cert（房产证）或photo（房屋照片）
    
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    if file and allowed_file(file.filename):
        # 安全地获取文件名并保存
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'filename': new_filename,
            'file_path': file_path,
            'url': f"/static/uploads/{new_filename}"
        })
    
    return jsonify({'success': False, 'error': '不允许的文件类型'})

@app.route('/api/valuation', methods=['POST'])
def api_valuation():
    """估值API"""
    try:
        data = request.get_json()
        
        # 提取房产数据
        property_data = {
            "address": data.get('address'),
            "city": data.get('city'),
            "property_cert_image": data.get('cert_image'),
            "property_photo": data.get('property_photo'),
            "property_text": data.get('description')
        }
        
        # 处理房产数据
        processed_data = valuation_system.process_property_data(property_data)
        
        # 准备目标房产数据
        target_property = {
            "size": float(data.get('area', 90)),
            "floor": data.get('floor', '中楼层'),
            "fitment": data.get('fitment', '简装'),
            "built_time": f"{data.get('year', 2015)}",
            "room": int(data.get('room', 2)),
            "hall": int(data.get('hall', 1)),
            "kitchen": int(data.get('kitchen', 1)),
            "bathroom": int(data.get('bathroom', 1)),
            "green_rate": processed_data.get("enhanced_data", {}).get("property_info", {}).get("green_rate", 0.3),
            "transaction_type": 1
        }
        
        # 估算房产价值
        # 尝试从数据库获取可比案例
        comparable_cases = None
        try:
            mysql_manager = MySQLManager()
            city = data.get('city', '上海')
            
            # 使用careful_selection进行精筛
            # house_type = processed_data.get("enhanced_data", {}).get("property_info", {}).get("house_type", "2室1厅1厨1卫")
            # 从前端获取户型信息
            room = data.get('room', 2)
            hall = data.get('hall', 1)
            kitchen = data.get('kitchen', 1)
            bathroom = data.get('bathroom', 1)
            house_type = f"{room}室{hall}厅{kitchen}厨{bathroom}卫"
            
            house_loc = data.get('address', '')
            
            selction_example = careful_selection(
                username=mysql_manager._username,
                password=mysql_manager._password,
                host=mysql_manager._host,
                port=mysql_manager._port,
                database=mysql_manager._db,
                table=mysql_manager.get_table(city),
                house_floor=target_property['floor'],
                house_area=target_property['size'],
                house_type=house_type,
                house_decoration=target_property['fitment'],
                house_year=int(target_property['built_time'].split('-')[0]),
                house_loc=house_loc
            )
            # print args for careful_seslection
            print(f"careful_selection args:\nhouse_floor: {target_property['floor']}\nhouse_area: {target_property['size']}\nhouse_type: {house_type}\nhouse_decoration: {target_property['fitment']}\nhouse_year: {int(target_property['built_time'].split('-')[0])}\nhouse_loc: {house_loc}")
            
            df = selction_example.selction()
            mysql_manager.close()
            
            if df:
                print(f"精筛成功，获取到 {len(df)} 个可比案例")
                # 转换df为comparable_cases格式
                comparable_cases = []
                for i in df[:]:
                    case = {
                        'price': float(i["u_price"]),
                        'size': float(i['house_area']),
                        'floor': i['house_floor'],
                        'fitment': i['house_decoration'],
                        'built_time': f"{i['house_year']}",
                        'transaction_time': str(i['transaction_time']),
                        'green_rate': i.get('green_rate', 0.3),
                        'address': i['house_loc'],
                        'transaction_type': 1
                    }
                    comparable_cases.append(case)
            else:
                print("精筛失败，没有找到合适的案例，将使用示例案例")
        except Exception as e:
            print(f"获取可比案例失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        estimation_result = valuation_system.estimate_property_value(target_property, comparable_cases)
        
        # 房价趋势预测
        trend_factor = 0.0
        min_trend = 0.0
        max_trend = 0.0
        
        try:
            # 从地址中提取区域信息
            address = data.get('address', '')
            city = data.get('city', '上海')
            region = city + address
            
            # 计算时间范围
            currentTime = datetime.now()
            # 过去6个月
            beforeTime = currentTime - timedelta(days=180)
            # 未来2个月
            afterTime = currentTime + timedelta(days=60)

            time_range = f"{beforeTime.strftime('%Y年%m月')}-{afterTime.strftime('%Y年%m月')}"
            
            query = f"{time_range}, {region}的房价走势如何?"
            
            print(f"正在进行房价趋势预测: {query}")
            
            prediction = predict_region(query, max_retries=3, enable_evolution=False, debug=True)
            
            if prediction:
                # 提取趋势因子
                min_trend, max_trend = extract_trend_factor(prediction)
                trend_factor = (min_trend + max_trend) / 2.0
                print(f"提取到的趋势因子范围: {min_trend:.2%} ~ {max_trend:.2%}")
            
        except Exception as e:
            print(f"房价预测失败: {str(e)}")

        # 应用趋势调整
        original_price = estimation_result['estimated_price']
        if original_price is not None:
            # 计算调整后的价格范围
            min_adjusted_price = original_price * (1 + min_trend)
            max_adjusted_price = original_price * (1 + max_trend)
            
            estimation_result['estimated_price'] = (min_adjusted_price + max_adjusted_price) / 2
            estimation_result['original_price'] = original_price
            estimation_result['trend_factor'] = trend_factor
            estimation_result['price_range'] = [min_adjusted_price, max_adjusted_price]
            
            # 更新解释
            if trend_factor != 0:
                trend_desc = "上涨" if trend_factor > 0 else "下跌"
                
                # 构建趋势描述字符串
                if min_trend == max_trend:
                    trend_str = f"{abs(trend_factor):.2%}"
                else:
                    # 确保显示顺序正确（从小到大）
                    abs_min = abs(min_trend)
                    abs_max = abs(max_trend)
                    trend_str = f"{min(abs_min, abs_max):.2%} ~ {max(abs_min, abs_max):.2%}"

                estimation_result['explanation'] += f"\n\n【市场趋势调整】\n基于AI对 {region} 区域 {time_range} 的房价趋势预测，\n市场预期{trend_desc} {trend_str}。\n估值已相应调整：\n- 调整前单价：{original_price:.2f} 元/平\n- 调整后单价：{min_adjusted_price:.2f} - {max_adjusted_price:.2f} 元/平"

        # 生成报告
        report_path = valuation_system.generate_report(property_data, estimation_result, target_property)
        
        area = float(data.get('area', 90))
        total_price = estimation_result['estimated_price'] * area
        
        # 构建响应
        response = {
            'success': True,
            'estimated_price': estimation_result['estimated_price'],
            'price_range': estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']]),
            'confidence': estimation_result['confidence'],
            'total_price': total_price,
            'total_price_range': [p * area for p in estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']])],
            'explanation': estimation_result['explanation'],
            'report_path': report_path,
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"估值失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reports/<filename>')
def get_report(filename):
    """获取报告API"""
    reports_dir = os.path.join("static", "reports")
    return send_from_directory(reports_dir, filename)

@app.route('/reports')
def reports():
    """报告列表页面"""
    reports_dir = os.path.join("static", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    reports_list = []
    for filename in os.listdir(reports_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(reports_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # 提取报告信息
                address = report_data.get('property_data', {}).get('address', '未知地址')
                estimated_price = report_data.get('estimation_result', {}).get('estimated_price', 0)
                price_range = report_data.get('estimation_result', {}).get('price_range', None)
                generated_at = report_data.get('generated_at', '')
                
                reports_list.append({
                    'filename': filename,
                    'address': address,
                    'estimated_price': estimated_price,
                    'price_range': price_range,
                    'generated_at': generated_at
                })
            except Exception as e:
                print(f"读取报告失败 {filename}: {str(e)}")
    
    # 按生成时间排序
    reports_list.sort(key=lambda x: x['generated_at'], reverse=True)
    
    return render_template('reports.html', reports=reports_list)

@app.route('/report/<path:filename>')
def view_report(filename):
    """查看报告页面"""
    reports_dir = os.path.join("static", "reports")
    
    # 处理不同的路径格式
    if filename.startswith("static/reports/"):
        file_path = filename
    else:
        file_path = os.path.join(reports_dir, filename)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        return render_template('report.html', report=report_data)
    except Exception as e:
        return render_template('error.html', error=f"读取报告失败: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 