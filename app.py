"""
房估宝 - 房产估值新范式
Web应用入口
"""
import os
import sys
import json
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
import pandas as pd
from price.careful_selection import careful_selection
from price.RealEstateValuation import RealEstateValuation
from record.record import Record
from database.mysql_manager import MySQLManager
from report.ocr import OCR_Table
from llm.clip_service import clip_service


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
    返回: (min_factor, max_factor, is_segmented, segmented_info)
    """
    if not prediction_text:
        return 0.0, 0.0, False, None
    
    # 检查分段趋势，如 "先上升 1% ... 后下降 2%"
    segmented_pattern = r'先.*?(上升|上涨|增长).*?(\d+(?:\.\d+)?)(?:%|％).*?后.*?(下降|下跌|诚少).*?(\d+(?:\.\d+)?)(?:%|％)'
    seg_match = re.search(segmented_pattern, prediction_text)
    if seg_match:
        rise_val = float(seg_match.group(2)) / 100.0
        fall_val = -float(seg_match.group(4)) / 100.0
        # 整体趋势取两者之和（近似）
        net_trend = rise_val + fall_val
        return net_trend, net_trend, True, (rise_val, abs(fall_val))

    # 反向分段也可检查 "先下降 ... 后上升"
    segmented_pattern_rev = r'先.*?(下降|下跌|减少).*?(\d+(?:\.\d+)?)(?:%|％).*?后.*?(上升|上涨|增长).*?(\d+(?:\.\d+)?)(?:%|％)'
    seg_match_rev = re.search(segmented_pattern_rev, prediction_text)
    if seg_match_rev:
        fall_val = -float(seg_match_rev.group(2)) / 100.0
        rise_val = float(seg_match_rev.group(4)) / 100.0
        net_trend = fall_val + rise_val
        return net_trend, net_trend, True, (abs(fall_val), rise_val, "下降/上升")

    # 匹配范围模式 ... (existing logic)
    range_pattern = r'(\d+(?:\.\d+)?)(?:%|％)?\s*[-~至]\s*(\d+(?:\.\d+)?)(?:%|％)'
    
    # 匹配 "上涨" 或 "增长" 后跟范围
    rise_range_match = re.search(r'(?:上涨|增长|上升).*?' + range_pattern, prediction_text)
    if rise_range_match:
        min_val = float(rise_range_match.group(1)) / 100.0
        max_val = float(rise_range_match.group(2)) / 100.0
        return min_val, max_val, False, None

    # 匹配 "下跌" 或 "下降" 后跟范围
    fall_range_match = re.search(r'(?:下跌|下降|减少).*?' + range_pattern, prediction_text)
    if fall_range_match:
        val1 = -float(fall_range_match.group(1)) / 100.0
        val2 = -float(fall_range_match.group(2)) / 100.0
        return min(val1, val2), max(val1, val2), False, None

    # 如果没有匹配到范围，尝试匹配单个数值
    rise_match = re.search(r'(?:上涨|增长|上升).*?(\d+(?:\.\d+)?)%', prediction_text)
    if rise_match:
        val = float(rise_match.group(1)) / 100.0
        return val, val, False, None
        
    fall_match = re.search(r'(?:下跌|下降|减少).*?(\d+(?:\.\d+)?)%', prediction_text)
    if fall_match:
        val = -float(fall_match.group(1)) / 100.0
        return val, val, False, None
        
    return 0.0, 0.0, False, None

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


@app.route('/api/ocr_extract', methods=['POST'])
def api_ocr_extract():
    """提取房产证OCR数据"""
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        if not image_path:
            return jsonify({"success": False, "error": "缺少图片路径"}), 400
        
        # 使用 OCR_Table 处理
        ocr_processor = OCR_Table()
        result_str = ocr_processor.trans_to_str(image_path)
        
        if not result_str:
            return jsonify({"success": False, "error": "OCR 提取失败"}), 500
            
        result_json = json.loads(result_str)
        content = result_json.get('body', {}).get('Data', {}).get('Content', '')
        
        # 简单提取 logic
        extracted_info = {
            "address": "",
            "area": 0.0,
            "room": 2,
            "hall": 1,
            "year": 2015
        }
        
        # 提取地址: 房地坐落/坐落
        addr_match = re.search(r'(?:房地坐落|坐落)\s*[:：\s]*([^\n\r，。;；]*)', content)
        if addr_match:
            extracted_info["address"] = addr_match.group(1).strip()
            
        # 提取建筑面积, 注意可能含小数点
        area_match = re.search(r'建筑面积\s*[:：\s]*(\d+(\.\d+)?)\s*(?:平方米|㎡|平米|平)?', content)
        if not area_match:
            area_match = re.search(r'(\d+(\.\d+)?)\s*(?:平方米|㎡|平米|平)', content)
        if area_match:
            try:
                extracted_info["area"] = float(area_match.group(1))
            except:
                pass
            
        # 户型提取 (如: 2室1厅, 3房2厅)
        room_match = re.search(r'(\d+)\s*(?:室|房)', content)
        if room_match:
            extracted_info["room"] = int(room_match.group(1))
        
        hall_match = re.search(r'(\d+)\s*(?:厅)', content)
        if hall_match:
            extracted_info["hall"] = int(hall_match.group(1))
            
        # 年份提取, 查找 20XX年 或 19XX年
        year_match = re.search(r'((?:20|19)\d{2})\s*年', content)
        if not year_match:
             year_match = re.search(r'((?:20|19)\d{2})[-\/]\d{2}[-\/]\d{2}', content)
        if year_match:
            extracted_info["year"] = int(year_match.group(1))

        return jsonify({
            "success": True,
            "data": extracted_info
        })
    except Exception as e:
        print(f"OCR分析详细错误: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/recognize_decoration', methods=['POST'])
def api_recognize_decoration():
    """识别装修情况: 自动判别装修是精装/简装/毛坯，使用CLIP模型"""
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        if not image_path:
            return jsonify({"success": False, "error": "缺少图片路径"}), 400
        
        # 将相对路径转换为绝对路径
        if not os.path.isabs(image_path):
            if image_path.startswith('/static/'):
                image_path = image_path.replace('/static/', 'static/')
            image_path = os.path.join(os.getcwd(), image_path)
        
        # 使用 CLIPService 进行识别
        result = clip_service.classify_decoration(image_path)
        
        return jsonify({
            "success": True,
            "decoration": result
        })
    except Exception as e:
        print(f"Decoration recognition error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/valuation', methods=['POST'])
def api_valuation():
    """估值API"""
    try:
        data = request.get_json()
        
        def generate():
            try:
                # 1. 提取和处理房产数据
                yield json.dumps({"status": "progress", "stage": "process", "message": "正在处理房产数据及地图..."}) + "\n"
                
                property_data = {
                    "address": data.get('address'),
                    "city": data.get('city'),
                    "property_cert_image": data.get('cert_image'),
                    "property_photo": data.get('property_photo'),
                    "property_text": data.get('description')
                }
                
                # 处理房产数据 (内部会包含地图获取)
                processed_data = valuation_system.process_property_data(property_data)
                yield json.dumps({"status": "progress", "stage": "process", "message": "已完成房产数据及地图处理", "done": True}) + "\n"
                
                # 获取绿化率
                green_val = 0.3
                if data.get('greening') is not None:
                    try:
                        green_val = float(data.get('greening')) / 100.0
                    except:
                        pass
                else:
                    # 尝试从处理过的数据中获取
                    raw_green = processed_data.get("enhanced_data", {}).get("property_info", {}).get("green_rate", "0.3")
                    try:
                        if isinstance(raw_green, str):
                            if '%' in raw_green:
                                green_val = float(raw_green.replace('%', '')) / 100.0
                            else:
                                green_val = float(raw_green)
                        else:
                            green_val = float(raw_green)
                    except:
                        green_val = 0.3

                # 准备目标房产数据
                target_property = {
                    "size": float(data.get('area', 90)),
                    "floor": data.get('floor', '中楼层'),
                    "fitment": data.get('fitment', '简装'),
                    "structure": data.get('structure', '平层'),
                    "built_time": f"{data.get('year', 2015)}-01-01",
                    "room": int(data.get('room', 2)),
                    "hall": int(data.get('hall', 1)),
                    "kitchen": int(data.get('kitchen', 1)),
                    "bathroom": int(data.get('bathroom', 1)),
                    "green_rate": green_val,
                    "transaction_type": 1
                }
                
                # 2. 匹配历史可比案例及估算价值
                yield json.dumps({"status": "progress", "stage": "estimate", "message": "正在匹配案例并估算房产价值..."}) + "\n"
                comparable_cases = None
                mysql_manager = None
                try:
                    mysql_manager = MySQLManager()
                    city = data.get('city', '上海')
                    
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
                    
                    df = selction_example.selction()
                    
                    if df:
                        comparable_cases = []
                        for i in df[:]:
                            # 处理绿化率字符串
                            raw_green = i.get('green_rate', '0.3')
                            try:
                                if isinstance(raw_green, str):
                                    if '%' in raw_green:
                                        green_val = float(raw_green.replace('%', '')) / 100.0
                                    else:
                                        green_val = float(raw_green)
                                else:
                                    green_val = float(raw_green)
                            except:
                                green_val = 0.3
                                
                            # 处理房龄
                            house_year = i.get('house_year')
                            built_time_str = f"{house_year}-01-01" if house_year else "2015-01-01"

                            case = {
                                'price': float(i["u_price"]),
                                'size': float(i['house_area']),
                                'floor': i['house_floor'],
                                'fitment': i['house_decoration'],
                                'structure': i.get('house_structure', '平层'),
                                'built_time': built_time_str,
                                'transaction_time': str(i['transaction_time']),
                                'green_rate': green_val,
                                'address': i['house_loc'],
                                'transaction_type': 1
                            }
                            comparable_cases.append(case)
                except Exception as e:
                    print(f"获取可比案例失败: {str(e)}")
                finally:
                    if mysql_manager:
                        mysql_manager.close()
                
                # 提取专业调整参数
                pro_adjustments = data.get('pro_adjustments')
                
                # 开始估价计算
                estimation_result = valuation_system.estimate_property_value(target_property, comparable_cases, pro_adjustments=pro_adjustments)
                trend_factor = 0.0
                min_trend = 0.0
                max_trend = 0.0
                
                try:
                    address = data.get('address', '')
                    city = data.get('city', '上海')
                    region = city + address
                    currentTime = datetime.now()
                    beforeTime = currentTime - timedelta(days=180)
                    afterTime = currentTime + timedelta(days=60)
                    time_range = f"{beforeTime.strftime('%Y年%m月')}-{afterTime.strftime('%Y年%m月')}"
                    
                    query = f"{time_range}, {region}的房价走势如何?"
                    prediction = predict_region(query, max_retries=3, enable_evolution=False, debug=True)
                    
                    if prediction:
                        min_trend, max_trend, is_segmented, seg_info = extract_trend_factor(prediction)
                        trend_factor = (min_trend + max_trend) / 2.0
                except Exception as e:
                    print(f"房价预测失败: {str(e)}")

                # 应用趋势调整
                original_price = estimation_result['estimated_price']
                if original_price is not None:
                    min_adjusted_price = original_price * (1 + min_trend)
                    max_adjusted_price = original_price * (1 + max_trend)
                    estimation_result['estimated_price'] = (min_adjusted_price + max_adjusted_price) / 2
                    estimation_result['original_price'] = original_price
                    estimation_result['trend_factor'] = trend_factor
                    estimation_result['price_range'] = [min_adjusted_price, max_adjusted_price]
                    
                    if trend_factor != 0:
                        if is_segmented and seg_info:
                            # 处理分段趋势样式: 上升/下降|a-b|
                            if len(seg_info) == 2:
                                trend_desc = "上升/下降"
                                trend_str = f"|{seg_info[0]:.1%} - {seg_info[1]:.1%}|"
                            else:
                                # 下降/上升 情景
                                trend_desc = seg_info[2]
                                trend_str = f"|{seg_info[0]:.1%} - {seg_info[1]:.1%}|"
                        else:
                            trend_desc = "上涨" if trend_factor > 0 else "下跌"
                            abs_min = abs(min_trend)
                            abs_max = abs(max_trend)
                            if abs_min == abs_max:
                                trend_str = f"{abs_min:.2%}"
                            else:
                                trend_str = f"{min(abs_min, abs_max):.2%} ~ {max(abs_min, abs_max):.2%}"
                        
                        # 处理单价范围显示，若相同则只显示一个值
                        adj_price_str = f"{min_adjusted_price:.2f} - {max_adjusted_price:.2f}"
                        if abs(min_adjusted_price - max_adjusted_price) < 0.01:
                            adj_price_str = f"{min_adjusted_price:.2f}"

                        estimation_result['explanation'] += f"\n\n【市场趋势调整】\n基于AI对 {region} 区域 {time_range} 的房价趋势预测，\n市场预期{trend_desc} {trend_str}。\n估值已相应调整：\n- 调整前单价：{original_price:.2f} 元/平\n- 调整后单价：{adj_price_str} 元/平"

                yield json.dumps({"status": "progress", "stage": "predict", "message": "已完成趋势预测与价值微调", "done": True}) + "\n"

                # 生成报告
                report_path = valuation_system.generate_report(property_data, estimation_result, target_property)
                area = float(data.get('area', 90))
                total_price = estimation_result['estimated_price'] * area
                
                # 构建最终响应
                response_data = {
                    'success': True,
                    'estimated_price': estimation_result['estimated_price'],
                    'price_range': estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']]),
                    'confidence': estimation_result['confidence'],
                    'total_price': total_price,
                    'total_price_range': [p * area for p in estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']])],
                    'explanation': estimation_result['explanation'],
                    'report_path': report_path,
                }
                
                yield json.dumps({"status": "success", "result": response_data}) + "\n"
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield json.dumps({"status": "error", "message": str(e)}) + "\n"

        return Response(stream_with_context(generate()), mimetype='application/x-ndjson')
    
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