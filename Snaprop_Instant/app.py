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
from flask_cors import CORS
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
CORS(app) # 启用跨域支持以对接新的 Vue 前端

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
    
@app.route('/api/login', methods=['POST'])
def api_login():
    """登录API"""
    try:
        data = request.get_json()
        account = data.get('account') # 账号或邮箱
        password = data.get('password')
        
        if not account or not password:
            return jsonify({"success": False, "error": "请提供账号和密码"}), 400
            
        mysql_manager = MySQLManager()
        user = mysql_manager.find_user(account)
        mysql_manager.close()
        
        if user and user['password'] == password:
            # 简单返回用户信息，生产环境应使用 JWT 等
            return jsonify({
                "success": True,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email']
                }
            })
        else:
            return jsonify({"success": False, "error": "账号或密码错误"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    """注册API"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            return jsonify({"success": False, "error": "请填写完整信息"}), 400
            
        if password != confirm_password:
            return jsonify({"success": False, "error": "两次输入的密码不一致"}), 400
            
        mysql_manager = MySQLManager()
        # 检查是否已存在
        if mysql_manager.find_user(username) or mysql_manager.find_user(email):
            mysql_manager.close()
            return jsonify({"success": False, "error": "用户名或邮箱已存在"}), 400
            
        success = mysql_manager.create_user(username, email, password)
        mysql_manager.close()
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "注册失败，请稍后再试"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
def api_change_password():
    """修改密码API"""
    try:
        data = request.get_json()
        username = data.get('username')
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not all([username, old_password, new_password]):
            return jsonify({"success": False, "error": "请提供完整信息"}), 400
            
        mysql_manager = MySQLManager()
        success, message = mysql_manager.update_password(username, old_password, new_password)
        mysql_manager.close()
        
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": message}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Admin APIs ---

@app.route('/api/admin/users', methods=['GET', 'DELETE'])
def api_admin_users():
    """管理员：用户管理"""
    try:
        mysql_manager = MySQLManager()
        if request.method == 'GET':
            users = mysql_manager.get_all_users()
            mysql_manager.close()
            return jsonify({"success": True, "users": users})
        
        elif request.method == 'DELETE':
            username = request.args.get('username')
            if not username:
                return jsonify({"success": False, "error": "缺少用户名"}), 400
            success = mysql_manager.delete_user(username)
            mysql_manager.close()
            return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/reports', methods=['GET', 'DELETE'])
def api_admin_reports():
    """管理员：报告管理"""
    try:
        mysql_manager = MySQLManager()
        if request.method == 'GET':
            reports = mysql_manager.get_all_reports()
            mysql_manager.close()
            return jsonify({"success": True, "reports": reports})
        
        elif request.method == 'DELETE':
            report_id = request.args.get('report_id')
            if not report_id:
                return jsonify({"success": False, "error": "缺少报告ID"}), 400
            success = mysql_manager.delete_report(report_id)
            mysql_manager.close()
            return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/upload_excel', methods=['POST'])
def api_admin_upload_excel():
    """管理员：通过Excel批量导入房产数据"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "请选择文件"}), 400
        
        file = request.files['file']
        city = request.form.get('city')
        
        if file.filename == '' or not city:
            return jsonify({"success": False, "error": "文件或城市信息缺失"}), 400
            
        # 临时保存文件
        uploads_dir = os.path.join("static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        temp_path = os.path.join(uploads_dir, file.filename)
        file.save(temp_path)
        
        # 调用 MySQLManager 导入数据
        mysql_manager = MySQLManager()
        mysql_manager.insert(city, temp_path)
        mysql_manager.close()
        
        return jsonify({"success": True, "message": f"成功导入 {city} 房产数据"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/manual_entry', methods=['POST'])
def api_admin_manual_entry():
    """管理员：手动单条录入房产数据"""
    try:
        data = request.get_json()
        city = data.get('city')
        if not city:
            return jsonify({"success": False, "error": "城市必填"}), 400
            
        mysql_manager = MySQLManager()
        success = mysql_manager.insert_manual_record(city, data)
        mysql_manager.close()
        
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cities', methods=['GET'])
def api_get_cities():
    """获取所有已支持的城市列表"""
    try:
        mysql_manager = MySQLManager()
        cities = mysql_manager.get_all_cities_list()
        mysql_manager.close()
        return jsonify({"success": True, "cities": cities})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/add_city', methods=['POST'])
def api_admin_add_city():
    """管理员：添加新城市"""
    try:
        data = request.get_json()
        city_name = data.get('city_name')
        table_name = data.get('table_name')
        intro = data.get('introduction', '')
        detail = data.get('detail', '')
        
        if not city_name or not table_name:
            return jsonify({"success": False, "error": "城市名称和表名必填"}), 400
            
        mysql_manager = MySQLManager()
        success = mysql_manager.add_new_city(city_name, table_name, intro, detail)
        mysql_manager.close()
        
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
        
        # Handle property photo(s) - consolidate into singular
        # Step 2 sends property_photos (list of base64), legacy might send property_photo (path/base64)
        all_photos = []
        if data.get('property_photos') and isinstance(data.get('property_photos'), list):
             all_photos = data.get('property_photos')
        elif data.get('property_photo'):
             all_photos = [data.get('property_photo')]
             
        main_photo = all_photos[0] if all_photos else None

        # 1. 提取和处理房产数据
        property_data = {
            "address": data.get('address'),
            "city": data.get('city'),
            "area": float(data.get('area', 100)),
            "house_type": f"{data.get('room')}室{data.get('hall')}厅",
            "year": data.get('year'),
            "floor": data.get('floor'),
            "fitment": data.get('fitment'),
            "structure": data.get('structure'),
            "property_cert_image": data.get('cert_image'),
            "property_photos": all_photos,
            "property_photo": main_photo,
            "property_text": data.get('description')
        }
        
        # 处理房产数据 (包含地图生成等)
        processed_data = valuation_system.process_property_data(property_data)
        
        # 获取绿化率
        green_val = 0.2
        if data.get('greening') is not None:
            try:
                val = float(data.get('greening'))
                green_val = val / 100.0 if val > 1 else val
            except: pass
        else:
            raw_green = processed_data.get("enhanced_data", {}).get("property_info", {}).get("green_rate", "0.2")
            try:
                if isinstance(raw_green, str):
                    if '%' in raw_green: green_val = float(raw_green.replace('%', '')) / 100.0
                    else: green_val = float(raw_green)
                else: green_val = float(raw_green)
            except: pass

        # 准备目标房产数据
        target_property = {
            "size": property_data['area'],
            "floor": data.get('floor', '中楼层'),
            "fitment": data.get('fitment', '精装'),
            "structure": data.get('structure', '平层'),
            "built_time": str(data.get('year', 2015)),
            "room": int(data.get('room', 2)),
            "hall": int(data.get('hall', 1)),
            "kitchen": int(data.get('kitchen', 1)),
            "bathroom": int(data.get('bathroom', 1)),
            "green_rate": green_val,
            "transaction_type": 1
        }
        
        # 2. 匹配案例并估算价值
        # 这里逻辑沿用原来的 PropertyValuationSystem.estimate_property_value 但不生成报告
        from price.careful_selection import careful_selection
        mysql_manager = MySQLManager()
        city = data.get('city', '上海')
        house_type_full = f"{data.get('room')}室{data.get('hall')}厅{data.get('kitchen',1)}厨{data.get('bathroom',1)}卫"
        
        selection_example = careful_selection(
            username=mysql_manager._username, password=mysql_manager._password,
            host=mysql_manager._host, port=mysql_manager._port,
            database=mysql_manager._db, table=mysql_manager.get_table(city),
            house_floor=target_property['floor'], house_area=target_property['size'],
            house_type=house_type_full, house_decoration=target_property['fitment'],
            house_year=int(target_property['built_time']), house_loc=property_data['address']
        )
        df = selection_example.selection()
        comparable_cases = []
        if df:
            for i in df:
                comparable_cases.append({
                    'price': float(i["u_price"]), 
                    'size': float(i['house_area']),
                    'floor': i['house_floor'], 
                    'fitment': i['house_decoration'],
                    'structure': i.get('house_structure', '-'),
                    'green_rate': i.get('green_rate', '-'),
                    'house_type': i.get('house_type', '-'),
                    'built_time': str(i.get('house_year', 2015)), 
                    'transaction_time': str(i['transaction_time']),
                    'address': i['house_loc']
                })
        mysql_manager.close()

        estimation_result = valuation_system.estimate_property_value(target_property, comparable_cases)
        
        # 3. AI 预测调整
        if data.get('enable_prediction', True):
            try:
                # 尝试预测趋势
                address = data.get('address', '')
                region = city + address
                query = f"最近6个月, {region}的房价走势如何?"
                prediction = predict_region(query)
                if prediction:
                    min_t, max_t, _, _ = extract_trend_factor(prediction)
                    trend_factor = (min_t + max_t) / 2.0
                    orig_p = estimation_result['estimated_price']
                    new_p = orig_p * (1 + trend_factor)
                    estimation_result['estimated_price'] = new_p
                    estimation_result['explanation'] += f"\n\n【AI趋势预测】\n{prediction}\n\n微调后单价：{int(new_p)}元/平"
            except Exception as pe:
                print(f"Prediction error: {pe}")

        # 4. 汇总结果并保存为 JSON
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_id = f"REPORT_{timestamp}"
        
        response_data = {
            "property_data": property_data,
            "target_property": target_property,
            "estimation_result": estimation_result,
            "total_price": estimation_result['estimated_price'] * property_data['area'],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_id": report_id,
            "pdf_url": None,
            "embedded_images": {
                "cert_image": property_data.get('property_cert_image'),
                "photo_image": property_data.get('property_photo'),
                "property_photos": property_data.get('property_photos'),
                "map_image": processed_data.get('original_data', {}).get('map_image', '')
            }
        }
        
        reports_dir = os.path.join("static", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        report_filename = f"property_valuation_report_{timestamp}.json"
        with open(os.path.join(reports_dir, report_filename), 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)

        # 5. 保存元数据到数据库以实现用户隔离
        try:
            username = data.get('username', 'admin') # 生产环境应用 session/token
            mysql_manager = MySQLManager()
            mysql_manager.save_user_report({
                'username': username,
                'report_id': report_id,
                'address': property_data['address'],
                'city': property_data['city'],
                'area': property_data['area'],
                'house_type': property_data['house_type'],
                'estimated_price': estimation_result['estimated_price'],
                'total_price': estimation_result['estimated_price'] * property_data['area'],
                'generated_at': datetime.now(),
                'pdf_url': None
            })
            mysql_manager.close()
        except Exception as db_err:
            print(f"Database save error: {db_err}")

        return jsonify({"success": True, "data": response_data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_pdf', methods=['POST'])
def api_generate_pdf():
    """按需生成 PDF 报告"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        if not report_id: return jsonify({"success": False, "error": "Missing report_id"}), 400
        
        # 提取时间戳 logic update
        timestamp = report_id
        if timestamp.startswith('REPORT_'):
            timestamp = timestamp.replace('REPORT_', '')
        elif timestamp.startswith('property_valuation_report_'):
             timestamp = timestamp.replace('property_valuation_report_', '')
             
        json_path = os.path.join("static", "reports", f"property_valuation_report_{timestamp}.json")
        
        if not os.path.exists(json_path):
            return jsonify({"success": False, "error": "Report data not found"}), 404
            
        with open(json_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        from record.record import Record
        u_record = Record(999) 
        u_record.house_location = report_data['property_data']['address']
        u_record.city = report_data['property_data']['city']
        u_record.house_area = report_data['property_data']['area']
        u_record.client_name = data.get('client_name', report_data['target_property'].get('client_name','同小舟'))
        
        def clean_img_path(p):
            """清理图片路径，处理 http URL 和绝对路径"""
            if not isinstance(p, str): return p
            # 如果是完整 URL，去掉协议和域名
            if p.startswith('http'):
                from urllib.parse import urlparse
                try:
                    p = urlparse(p).path
                except: pass
            # 去掉开头的 / 以便匹配本地相对路径
            return p.lstrip('/') if p.startswith('/') else p

        u_record.report_logo = clean_img_path(data.get('report_logo', ''))
        
        # Store these in u_record if Record supports them and save to json potentially
        u_record.surrounding_environment = data.get('surrounding', '')
        u_record.traffic_conditions = data.get('traffic', '')
        u_record.property_overview = data.get('property_overview', '')
        u_record.occupancy_status = data.get('occupancy', '')
        
        # Save extended info back to json so it persists if needed (optional but good practice)
        report_data['extended_info'] = {
            'client_name': u_record.client_name,
            'report_logo': u_record.report_logo,
            'surrounding': u_record.surrounding_environment,
            'traffic': u_record.traffic_conditions,
            'property_overview': u_record.property_overview,
            'occupancy': u_record.occupancy_status
        }
        
        u_record.house_type = report_data['property_data']['house_type']
        u_record.price = report_data['estimation_result']['estimated_price']
        u_record.explanation = report_data['estimation_result']['explanation']
        u_record.map = report_data['embedded_images'].get('map_image', '')

        # 处理可能的列表或字符串 cert_image 并移除路径前导斜杠
        raw_cert = report_data['embedded_images'].get('cert_image')
        if raw_cert:
            if isinstance(raw_cert, list):
                u_record.production_cert_img = [clean_img_path(p) for p in raw_cert]
            else:
                u_record.production_cert_img = [clean_img_path(raw_cert)]
        else:
            u_record.production_cert_img = []

        # 处理多张房屋图片
        raw_photos = report_data['embedded_images'].get('property_photos')
        if not raw_photos:
             # Fallback to single photo if list is missing (legacy data)
             single = report_data['embedded_images'].get('photo_image')
             raw_photos = [single] if single else []

        if raw_photos:
             u_record.field_img = [clean_img_path(p) for p in raw_photos]
        else:
             u_record.field_img = []

        pdf_filename = f"valuation_report_{timestamp}.pdf"
        pdf_path = os.path.join("static", "reports", pdf_filename)
        
        from report.report_gen import property_report
        pdf_gen = property_report(pdf_path, u_record.house_location)
        pdf_gen.save_report(999, u_record)
             
        report_data['pdf_url'] = f"/api/reports/{pdf_filename}"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
            
        # 同时更新数据库中的 PDF URL
        try:
            mysql_manager = MySQLManager()
            mysql_manager.update_report_pdf(report_id, report_data['pdf_url'])
            mysql_manager.close()
        except: pass
            
        return jsonify({"success": True, "pdf_url": report_data['pdf_url']})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/api/history', methods=['GET'])
def api_get_history():
    """获取指定用户的历史评估报告列表"""
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({"success": False, "error": "Missing username"}), 400
            
        mysql_manager = MySQLManager()
        reports_list = mysql_manager.get_user_history(username)
        mysql_manager.close()
        
        return jsonify({"success": True, "list": reports_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/upload/logo', methods=['POST'])
def api_upload_logo():
    """上传Logo API"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件部分'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"logo_{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'url': f"/static/uploads/{new_filename}" 
        })
    return jsonify({'success': False, 'error': '不允许的文件类型'})

@app.route('/api/upload/cert', methods=['POST'])
def api_upload_cert():
    """专门为房产证设计的上传 + 裁剪(可选) + OCR 解析 + LLM 提取"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有图片文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'})
    
    if file and allowed_file(file.filename):
        # 安全地保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"cert_{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        
        # 1. 执行 OCR 解析
        ocr_processor = OCR_Table()
        raw_text_content = ""
        try:
            # 获取文本内容用于 LLM
            result_str = ocr_processor.trans_to_str(file_path)
            if result_str:
                res_obj = json.loads(result_str)
                raw_text_content = res_obj.get('body', {}).get('Data', {}).get('Content', '')
        except Exception as e:
            print(f"OCR 文本提取失败: {str(e)}")

        # 2. 调用 LLM 转换为 Key-Value JSON
        structured_data = []
        if raw_text_content:
            try:
                from llm.llm_manager import QianwenManager
                llm = QianwenManager()
                prompt = """你是一个专业的房产数据助手。我会给你一段房产证OCR识别出的乱序文本，请你提取其中的关键信息并以JSON格式返回。
                要求：
                1. 返回格式必须是一个 JSON 数组，每个元素包含 'field' (字段名) 和 'value' (对应内容)。
                2. 必须包含的字段：房产地址、城市、建筑面积、户型、建成年份、权利人、共有情况、登记日期。
                3. 如果某项不存在，value 设为空字符串。
                4. 只返回 JSON 代码块，不要有其他解释。"""
                
                llm_reply = llm.interact_qwen(prompt, raw_text_content)
                
                # 提取 JSON 部分
                json_match = re.search(r'\[.*\]', llm_reply, re.DOTALL)
                if json_match:
                    structured_data = json.loads(json_match.group(0))
            except Exception as e:
                print(f"LLM 结构化处理失败: {str(e)}")

        # 如果 LLM 失败，回退到基础 OCR 表格数据
        if not structured_data:
            try:
                xlsx_paths = ocr_processor.trans_to_xlsx(new_filename)
                for xlsx_path in xlsx_paths:
                    raw_table_list = ocr_processor.trans_to_df(xlsx_path)
                    if raw_table_list:
                        for sheet_data in raw_table_list:
                            for r in sheet_data:
                                if any(x is not None and str(x).strip() != "" for x in r):
                                    structured_data.append({
                                        "field": str(r[0]).strip() if len(r) > 0 else "",
                                        "value": str(r[1]).strip() if len(r) > 1 else ""
                                    })
            except: pass

        return jsonify({
            'success': True,
            'url': f"http://127.0.0.1:5000/static/uploads/{new_filename}", # 使用完整 URL 解决前端显示问题
            'file_path': file_path,
            'table_data': structured_data  # 统一返回 JSON 对象数组
        })
    return jsonify({'success': False, 'error': '不支持此类文件格式'})

@app.route('/api/generate_report_content', methods=['POST'])
def api_generate_report_content():
    """生成报告默认内容"""
    try:
        data = request.get_json()
        city = data.get('city', '上海')
        address = data.get('address')
        house_type = data.get('house_type', '')
        area = data.get('area', '')
        
        if not address:
            return jsonify({"success": False, "error": "Missing address"}), 400
            
        from record.save_map import get_origin_place, get_nearby_places
        from llm.llm_manager import QianwenManager
        
        location, _ = get_origin_place(address, city, 1)
        if not location:
            # Fallback mock data or simple retry
             return jsonify({"success": True, "data": {
                "surrounding": f"位于{city}市区，周边生活配套便利。",
                "traffic": "交通便利，有多条公交线路。",
                "property_overview": f"建筑面积{area}平米，{house_type}。",
                "occupancy": "目前状况良好。"
            }})

        # Fetch POI
        nearby_places = get_nearby_places(location, '住宅区')
        hospitals = get_nearby_places(location, '医院')
        schools = get_nearby_places(location, '学校')
        transportation = get_nearby_places(location, '公交车站') + get_nearby_places(location, '地铁站')
        
        qm = QianwenManager()
        
        # Surrounding
        surrounding_prompt = f"已知住宅跟前有{','.join(nearby_places[:5])}等小区，附近有{','.join(hospitals[:3])}等医疗资源，{','.join(schools[:3])}等教育资源。请用一句话概括其临近环境及建筑物情况，语气专业客观。"
        surrounding_text = qm.interact_qwen(prompt="你是一位专业的房产评估师。", request=surrounding_prompt)
        
        # Traffic
        traffic_prompt = f"已知附近有{','.join(transportation[:5])}等交通设施。请用一句话概括其交通条件，语气专业客观。"
        traffic_text = qm.interact_qwen(prompt="你是一位专业的房产评估师。", request=traffic_prompt)
        
        # Overview - Template based
        overview_text = f"该物业坐落于{city}{address}，房屋类型为{house_type}，建筑面积{area}平方米。房屋维护状况良好，配套设施完善。"
        occupancy_text = "目前该物业处于自用状态，空置时间较短，室内维护保养较好。"

        return jsonify({"success": True, "data": {
            "surrounding": surrounding_text.replace('"','').strip(),
            "traffic": traffic_text.replace('"','').strip(),
            "property_overview": overview_text,
            "occupancy": occupancy_text
        }})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000) 