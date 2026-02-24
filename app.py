"""
房估宝 - 房产估值新范式
Web应用入口
"""
import os
import sys
import json
import re
import glob
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import openpyxl
from price.careful_selection import careful_selection
from price.RealEstateValuation import RealEstateValuation
from record.record import Record
from database.mysql_manager import MySQLManager
from report.ocr import OCR_Table
from report.report_gen import property_report


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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'xlsx', 'xls'}
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


@app.route('/api/get_surrounding', methods=['POST'])
def api_get_surrounding():
    """获取周边环境描述API"""
    try:
        data = request.get_json()
        address = data.get('address')
        city = data.get('city')
        
        if not address or not city:
            return jsonify({"success": False, "error": "缺少地址或城市"}), 400
            
        from record.save_map import environment_main
        description = environment_main(address, city)
        
        return jsonify({
            "success": True, 
            "description": description
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/export_excel', methods=['POST'])
def api_export_excel():
    """将前端表格数据导出为 Excel"""
    try:
        data = request.get_json()
        table_data = data.get('table_data', [])
        if not table_data:
            return jsonify({"success": False, "error": "表格数据为空"}), 400
        
        # 使用 pandas 创建 Excel
        df = pd.DataFrame(table_data)
        
        # 写入内存字节流
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, header=False)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f"property_ocr_result_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/ocr_extract', methods=['POST'])
def api_ocr_extract():
    """提取房产证数据，支持图片OCR或Excel直接读取"""
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        if not image_path:
            return jsonify({"success": False, "error": "缺少图片或文件路径"}), 400
        
        # 安全地提取文件名
        img_filename = os.path.basename(image_path)
        file_ext = img_filename.rsplit('.', 1)[1].lower() if '.' in img_filename else ""
        
        rows = []
        content = ""
        
        # 1. 如果是 Excel 文件，直接读取
        if file_ext in ['xlsx', 'xls']:
            try:
                # 转换路径为绝对路径以防读取失败
                abs_path = os.path.abspath(image_path)
                df_dict = pd.read_excel(abs_path, sheet_name=None, header=None)
                
                excel_texts = []
                for sheet_name, df in df_dict.items():
                    # 替换 NaN 为空字符串
                    df = df.fillna("")
                    sheet_rows = df.values.tolist()
                    
                    for r in sheet_rows:
                        str_row = [str(x).strip() for x in r]
                        if any(x != "" for x in str_row):
                            rows.append(str_row)
                            excel_texts.append(" ".join(str_row))
                
                # 合并所有文本用于后续正则匹配
                content = "\n".join(excel_texts)
            except Exception as e:
                print(f"Excel 直接读取失败: {str(e)}")
                return jsonify({"success": False, "error": f"Excel 读取失败: {str(e)}"}), 500
        
        # 2. 如果是图片，执行 OCR
        else:
            # 使用 OCR_Table 获取表格化数据
            ocr_processor = OCR_Table()
            
            # 保存 Excel 并解析原始表格数据
            try:
                xlsx_paths = ocr_processor.trans_to_xlsx(img_filename)
                # 处理所有识别出的表格（针对摊开本子的多页情况）
                for xlsx_path in xlsx_paths:
                    raw_table_list = ocr_processor.trans_to_df(xlsx_path)
                    if raw_table_list:
                        for sheet_data in raw_table_list:
                            # --- 智能列剪枝 (过滤全空列) ---
                            if not sheet_data: 
                                continue
                            
                            max_cols = 0
                            for r in sheet_data: 
                                if r: max_cols = max(max_cols, len(r))
                            
                            valid_col_indices = []
                            for c in range(max_cols):
                                is_empty = True
                                for r in sheet_data:
                                    if c < len(r) and r[c] is not None and str(r[c]).strip() != "" and str(r[c]).strip().lower() != "nan":
                                        is_empty = False
                                        break
                                if not is_empty:
                                    valid_col_indices.append(c)
                            
                            # 如果没有有效列，跳过
                            if not valid_col_indices:
                                continue
                                
                            # 过滤行并仅保留有效列
                            for r in sheet_data:
                                if any(x is not None and str(x).strip() != "" for x in r):
                                    cleaned_row = []
                                    for idx in valid_col_indices:
                                        val = r[idx] if idx < len(r) else ""
                                        val_str = str(val).strip() if val is not None else ""
                                        if val_str.lower() == "nan": val_str = ""
                                        cleaned_row.append(val_str)
                                    rows.append(cleaned_row)
                            
                            # 在不同表格/页面之间加一个分割线
                            if xlsx_path != xlsx_paths[-1]:
                                rows.append(["---" for _ in range(len(valid_col_indices))])
            except Exception as e:
                print(f"表格提取/合并失败: {str(e)}")

            # 使用 trans_to_str 获取文本内容，用于后备提取和辅助识别
            result_str = ocr_processor.trans_to_str(image_path)
            if result_str:
                try:
                    res_obj = json.loads(result_str)
                    content = res_obj.get('body', {}).get('Data', {}).get('Content', '')
                except: pass

        # 3. 结构化数据提取 (建议值 - 统一使用 content)
        extracted_info = {
            "address": "",
            "city": "",
            "area": 0.0,
            "room": 2,
            "hall": 1,
            "year": 2015
        }
        
        if content:
            # 提取地址
            addr_match = re.search(r'(?:房地坐落|坐落)\s*[:：\s]*([^\n\r，。;；]*)', content)
            if addr_match:
                found_addr = addr_match.group(1).strip()
                extracted_info["address"] = found_addr
                
                # 城市自动识别 (上海/沪 优先)
                if "上海" in found_addr or "沪" in found_addr:
                    extracted_info["city"] = "上海"
                elif "北京" in found_addr:
                    extracted_info["city"] = "北京"
                elif "广州" in found_addr:
                    extracted_info["city"] = "广州"
                elif "深圳" in found_addr:
                    extracted_info["city"] = "深圳"
                # ... 其他城市可续
            
            # 提取面积
            area_match = re.search(r'建筑面积\s*[:：\s]*(\d+(\.\d+)?)\s*(?:平方米|㎡|平米|平)?', content)
            if not area_match:
                area_match = re.search(r'(\d+(\.\d+)?)\s*(?:平方米|㎡|平米|平)', content)
            if area_match:
                try:
                    extracted_info["area"] = float(area_match.group(1))
                except: pass
                
            # 提取户型，特别反混淆
            # 先找 几室几厅
            type_match = re.search(r'(\d{1,2})\s*(?:室|房)\s*(\d{1,2})\s*厅', content)
            if type_match:
                extracted_info["room"] = int(type_match.group(1))
                extracted_info["hall"] = int(type_match.group(2))
            else:
                # 寻找室：排除门牌号（302室等通常三位及以上，或者前面有号/幢）
                # 寻找典型的户型描述：[1-9]室
                room_match = re.search(r'(?:[^0-9]|^)([1-9])\s*(?:室|房)', content)
                if room_match:
                    extracted_info["room"] = int(room_match.group(1))
                
                hall_match = re.search(r'([0-9])\s*厅', content)
                if hall_match:
                    extracted_info["hall"] = int(hall_match.group(1))
                
            # 年份提取
            year_match = re.search(r'((?:20|19)\d{2})\s*年', content)
            if year_match:
                extracted_info["year"] = int(year_match.group(1))

        return jsonify({
            "success": True,
            "table_data": rows,
            "extracted_data": extracted_info
        })
    except Exception as e:
        print(f"OCR分析详细错误: {str(e)}")
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
                    "built_time": str(data.get('year', 2015)), # 简称年份只需要年份
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
                    
                    selection_example = careful_selection(
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
                    
                    df = selection_example.selection()
                    
                    if hasattr(selection_example, 'last_strategy_msg'):
                        yield json.dumps({"status": "progress", "stage": "estimate", "message": f"{selection_example.last_strategy_msg}，正在计算估值..."}) + "\n"

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
                            built_time_val = str(house_year) if house_year else "2015"

                            case = {
                                'price': float(i["u_price"]),
                                'size': float(i['house_area']),
                                'floor': i['house_floor'],
                                'fitment': i['house_decoration'],
                                'structure': i.get('house_structure', '平层'),
                                'built_time': built_time_val,
                                'transaction_time': str(i['transaction_time']),
                                'green_rate': green_val,
                                'address': i['house_loc'],
                                'house_type': i.get('house_type', '-'),
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
                
                # 进入预测阶段
                enable_prediction = data.get('enable_prediction', True)
                
                if enable_prediction:
                    yield json.dumps({"status": "progress", "stage": "predict", "message": "已完成基础估值，通过AI预测进行微调..."}) + "\n"
                else:
                    yield json.dumps({"status": "progress", "stage": "predict", "message": "已完成基础估值，跳过AI趋势预测...", "done": True}) + "\n"

                trend_factor = 0.0
                min_trend = 0.0
                max_trend = 0.0
                prediction = None
                
                if enable_prediction:
                    try:
                        address = data.get('address', '')
                        city = data.get('city', '上海')
                        region = city + address
                        currentTime = datetime.now()
                        beforeTime = currentTime - timedelta(days=180)
                        afterTime = currentTime + timedelta(days=60)
                        time_range = f"{beforeTime.strftime('%Y年%m月')}-{afterTime.strftime('%Y年%m月')}"
                        
                        query = f"{time_range}, {region}的房价走势如何?"
                        prediction = predict_region(query, max_retries=2, enable_evolution=False, debug=True)
                        
                        if prediction:
                            min_trend, max_trend, is_segmented, seg_info = extract_trend_factor(prediction)
                            trend_factor = (min_trend + max_trend) / 2.0
                    except Exception as e:
                        print(f"房价预测失败: {str(e)}")

                # 应用趋势调整
                original_price = estimation_result['estimated_price']
                if original_price is not None and enable_prediction:
                    min_adjusted_price = original_price * (1 + min_trend)
                    max_adjusted_price = original_price * (1 + max_trend)
                    estimation_result['estimated_price'] = (min_adjusted_price + max_adjusted_price) / 2
                    estimation_result['original_price'] = original_price
                    estimation_result['trend_factor'] = trend_factor
                    estimation_result['price_range'] = [min_adjusted_price, max_adjusted_price]
                    
                    if prediction:
                        # 提取更干净的核心预测文本
                        short_prediction = prediction.strip()
                        # 尝试捕获冒号后的核心预测段落 (例如: ...: - 先小幅上升...)
                        if ":" in short_prediction:
                            parts = short_prediction.split(":", 1)
                            short_prediction = parts[1].strip()
                        if short_prediction.startswith("- "):
                            short_prediction = short_prediction[2:].strip()
                        
                        # 处理单价范围显示，若相同则只显示一个值
                        adj_price_str = f"{min_adjusted_price:.2f} - {max_adjusted_price:.2f}"
                        if abs(min_adjusted_price - max_adjusted_price) < 0.01:
                            adj_price_str = f"{min_adjusted_price:.2f}"

                        estimation_result['explanation'] += f"\n\n【市场趋势调整】\n基于AI对 {region} 区域 {time_range} 的房价趋势预测：\n{short_prediction}\n\n估值已相应调整：\n- 调整前单价：{original_price:.2f} 元/平\n- 调整后单价：{adj_price_str} 元/平"
                        # 移除了细节分析部分以简化结果显示

                if enable_prediction:
                    yield json.dumps({"status": "progress", "stage": "predict", "message": "已完成趋势预测与价值微调", "done": True}) + "\n"
                
                # 提取一些必要数值
                area = float(data.get('area', 90))
                total_price = estimation_result['estimated_price'] * area
                
                # 生成报告文件名 (提前生成以便存入 JSON)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                pdf_filename = f"valuation_report_{timestamp}.pdf"
                pdf_url = f"/api/reports/{pdf_filename}"
                
                # 生成报告 JSON (存入 JSON 时包含 pdf_url)
                report_path = valuation_system.generate_report(property_data, estimation_result, target_property, price_prediction=prediction, pdf_url=pdf_url)
                
                # 生成及保存 PDF 报告
                reports_dir = os.path.join("static", "reports")
                os.makedirs(reports_dir, exist_ok=True)
                pdf_path = os.path.join(reports_dir, pdf_filename)
                
                # 构造 Record 对象用于 PDF 生成
                u_id = 999  # 临时使用的 UID
                u_record = Record(u_id)
                u_record.house_location = data.get('address', '未知')
                u_record.city = data.get('city', '上海')
                u_record.house_area = area
                
                # 填充报告描述信息
                u_record.client_name = data.get('client_name', '同小舟')
                u_record.report_logo = data.get('report_logo', '')
                u_record.surrounding_environment = data.get('surrounding_env', '')
                u_record.traffic_conditions = data.get('traffic_cond', '')
                u_record.property_overview = data.get('prop_overview', '')
                u_record.occupancy_status = data.get('occupancy_status', '')
                
                room = data.get('room', 2)
                hall = data.get('hall', 1)
                kitchen = data.get('kitchen', 1)
                bathroom = data.get('bathroom', 1)
                u_record.house_type = f"{room}室{hall}厅{kitchen}厨{bathroom}卫"
                
                u_record.house_year = int(data.get('year', 2015))
                u_record.house_floor = data.get('floor', '中楼层')
                u_record.house_decorating = data.get('fitment', '简装')
                u_record.house_structure = data.get('structure', '平层')
                u_record.green_rate = green_val
                u_record.price = estimation_result['estimated_price']
                
                # 地图和图片
                u_record.map = processed_data.get('original_data', {}).get('map_image', '')
                if data.get('cert_image'):
                    u_record.production_cert_img = [data.get('cert_image')]
                    # 如果前端传了表格数据，直接用前端的；否则用文件路径
                    if data.get('ocr_table'):
                        # 将列表处理成 save_report 需要的格式
                        temp_ocr_path = data.get('cert_image').replace('.png', '_tmp.xlsx').replace('.jpg', '_tmp.xlsx').replace('.jpeg', '_tmp.xlsx')
                        try:
                            import openpyxl # 确保导入
                            wb = openpyxl.Workbook()
                            ws = wb.active
                            for r_idx, r_data in enumerate(data.get('ocr_table')):
                                for c_idx, val in enumerate(r_data):
                                    ws.cell(row=r_idx+1, column=c_idx+1, value=str(val) if val is not None else "")
                            wb.save(temp_ocr_path)
                            u_record.production_ocr = temp_ocr_path
                        except Exception as e:
                            print(f"临时Excel生成失败: {str(e)}")
                            u_record.production_ocr = data.get('cert_image').replace('.png', '_OCR.xlsx').replace('.jpg', '_OCR.xlsx').replace('.jpeg', '_OCR.xlsx')
                    else:
                        u_record.production_ocr = data.get('cert_image').replace('.png', '_OCR.xlsx').replace('.jpg', '_OCR.xlsx').replace('.jpeg', '_OCR.xlsx')
                
                if data.get('property_photo'):
                    u_record.field_img = [data.get('property_photo')]
                
                pdf_gen_success = False
                try:
                    pdf_report = property_report(pdf_path, u_record.house_location)
                    pdf_report.save_report(u_id, u_record)
                    pdf_gen_success = True
                except Exception as pdf_error:
                    print(f"PDF生成失败: {str(pdf_error)}")
                    import traceback
                    traceback.print_exc()

                # 构建最终响应 (如果有 pdf_url 则传回)
                final_pdf_url = pdf_url if pdf_gen_success else None
                
                response_data = {
                    'success': True,
                    'estimated_price': estimation_result['estimated_price'],
                    'price_range': estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']]),
                    'confidence': estimation_result['confidence'],
                    'total_price': total_price,
                    'total_price_range': [p * area for p in estimation_result.get('price_range', [estimation_result['estimated_price'], estimation_result['estimated_price']])],
                    'explanation': estimation_result['explanation'],
                    'report_path': report_path,
                    'pdf_url': final_pdf_url
                }

                # --- Cleanup logic (Keep only final JSON and PDF) ---
                try:
                    cleanup_files = []
                    # 1. Certificate and Photo
                    if data.get('cert_image'): cleanup_files.append(data.get('cert_image'))
                    if data.get('property_photo'): cleanup_files.append(data.get('property_photo'))
                    # 2. Map snapshot
                    if hasattr(u_record, 'map') and u_record.map: cleanup_files.append(u_record.map)
                    # 3. OCR Excel
                    if hasattr(u_record, 'production_ocr') and u_record.production_ocr: cleanup_files.append(u_record.production_ocr)
                    # 4. Temp OCR Excel (if specifically generated as _tmp.xlsx)
                    try:
                        if 'temp_ocr_path' in locals() and temp_ocr_path: cleanup_files.append(temp_ocr_path)
                    except: pass
                    # 5. Report Logo
                    if data.get('report_logo'): cleanup_files.append(data.get('report_logo'))
                    # 6. OCR Tables directory cleanup (e.g. static/ocr_tables/xxx_0_OCR.xlsx)
                    if data.get('cert_image'):
                        img_stem = os.path.splitext(os.path.basename(data.get('cert_image')))[0]
                        ocr_wildcard = os.path.join("static", "ocr_tables", f"{img_stem}*")
                        cleanup_files.extend(glob.glob(ocr_wildcard))
                    
                    for f in set(cleanup_files):
                        if not f: continue
                        # 处理路径，移除开头的斜杠
                        norm_f = f.lstrip('/\\').replace('\\', '/')
                        if os.path.exists(norm_f):
                            # Safety check: do not delete from static/reports
                            if "static/reports" not in norm_f:
                                os.remove(norm_f)
                                print(f"Cleaned up temp file: {norm_f}")
                except Exception as ce:
                    print(f"Cleanup error: {ce}")

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
    """估值记录列表页面"""
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
    """查看估值记录页面"""
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