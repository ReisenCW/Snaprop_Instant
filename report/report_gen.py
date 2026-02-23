import datetime
import cn2an
import os
import pandas as pd
from reportlab.lib.colors import black
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from report.ocr import OCR_Table
from record.record import Record
from database.mysql_manager import MySQLManager
from config.path_config import REPORT_PATH
from record.save_map import environment_main
from datetime import datetime, date

pdfmetrics.registerFont(TTFont("SimHei", "SimHei.ttf"))
pdfmetrics.registerFont(TTFont("SimSun", "SimSun.ttc"))
pdfmetrics.registerFont(TTFont("SimSunb", "simsunb.ttf"))
pdfmetrics.registerFont(TTFont("simfang", "simfang.ttf"))
pdfmetrics.registerFont(TTFont("simkai", "simkai.ttf"))
pdfmetrics.registerFont(TTFont("segoeuib", "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("segoeuil", "segoeuil.ttf"))
pdfmetrics.registerFont(TTFont("segoeuisl", "segoeuisl.ttf"))
pdfmetrics.registerFont(TTFont("seguisb", "seguisb.ttf"))


class PageElement:
    def __init__(self, content, page_number, x, y, width=None, height=None, **kwargs):
        """
        页面元素基类
        :param content: 内容（文本/图片路径/表格数据）
        :param page_number: 指定页码
        :param x: x坐标（从左边开始，单位：cm）
        :param y: y坐标（从底部开始，单位：cm）
        :param width: 宽度（cm）
        :param height: 高度（cm）
        :param kwargs: 其他参数
        """
        self.content = content
        self.page_number = page_number
        self.x = x * cm  # 转换为点
        self.y = y * cm  # 转换为点
        self.width = width * cm if width else None
        self.height = height * cm if height else None
        self.kwargs = kwargs


class TextElement(PageElement):
    def __init__(self, text, page_number, x, y, width=None, font_size=12,
                 align='left', font_name='SimSun', auto_next_page=True):
        """
        文本元素
        :param text: 文本内容
        :param page_number: 页码
        :param x: x坐标（cm）
        :param y: y坐标（cm）
        :param width: 文本宽度（cm）
        :param font_size: 字体大小
        :param align: 对齐方式 ('left', 'center', 'right')
        :param font_name: 字体名称
        :param auto_next_page: 是否自动移动到下一页
        """
        super().__init__(text, page_number, x, y, width)
        self.font_size = font_size
        self.align = align
        self.font_name = font_name
        self.auto_next_page = auto_next_page


class ImageElement(PageElement):
    pass


class TableElement(PageElement):
    def __init__(self, data, page_number, x, y, width, table_styles=None, col_widths=None,
                 wrap_cols=None, row_heights=None, font_size=12,
                 align='left', font_name='SimSun', factor=1.2):
        super().__init__(data, page_number, x, y, width)
        self.col_widths = [w * cm for w in col_widths] if col_widths else None
        self.wrap_cols = wrap_cols
        self.row_heights = [h * cm for h in row_heights] if row_heights else None
        self.font_size = font_size
        self.align = align
        self.font_name = font_name
        self.factor = factor
        if table_styles == None:
            self.table_styles = [
                ('FONT', (0, 0), (-1, -1), 'SimHei', 7),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 2, black),
                ('FONT', (1, 0), (1, -1), 'SimSun', 7),
            ]
        else:
            self.table_styles = table_styles


class LineElement(PageElement):
    def __init__(self, page_number, start_x, start_y, end_x, end_y,
                 line_width=0.1, line_color=colors.black, dash_pattern=None):
        """
        直线元素
        :param page_number: 页码
        :param start_x: 起点x坐标（cm）
        :param start_y: 起点y坐标（cm）
        :param end_x: 终点x坐标（cm）
        :param end_y: 终点y坐标（cm）
        :param line_width: 线条宽度（cm）
        :param line_color: 线条颜色
        :param dash_pattern: 虚线模式，如 [1, 2] 表示1个点划线2个点空白
        """
        super().__init__(None, page_number, start_x, start_y)
        self.end_x = end_x * cm
        self.end_y = end_y * cm
        self.line_width = line_width * cm
        self.line_color = line_color
        self.dash_pattern = dash_pattern


class PDFGenerator:
    def __init__(self, output_path, font_path=None):
        """
        初始化 PDF 生成器
        :param output_path: PDF 输出路径
        :param font_path: 字体文件路径
        """
        self.output_path = output_path
        self.elements = []
        self.page_size = A4
        self.page_width = A4[0]  # 页面宽度（点）
        self.page_height = A4[1]  # 页面高度（点）
        self.margin = 1 * cm  # 页面边距（1厘米）
        # 注册中文字体
        if font_path:
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
        # 创建样式
        self.styles = getSampleStyleSheet()
        self.chinese_style = ParagraphStyle(
            'ChineseStyle',
            fontName='CustomFont' if font_path else 'SimHei',
            fontSize=12,
            leading=20
        )

    def add_text(self, text: str, page_number, x, y, width=None, font_size=12,
                 align='left', font_name='SimSun', auto_next_page=False):
        """
        添加文本，支持自动分页
        :param text: 文本内容
        :param page_number: 页码
        :param x: x坐标（cm）
        :param y: y坐标（cm）
        :param width: 文本宽度（cm）
        :param font_size: 字体大小
        :param align: 对齐方式 ('left', 'center', 'right')
        :param font_name: 字体名称
        :param auto_next_page: 是否自动移动到下一页
        """
        # 返回分段后的高度
        #TODO：自动分页功能不完善，主要是缺少传入参数确定页面正文的起始位置，以及函数嵌套导致的返回信息丢失，涉及大面积代码更改，目前仍采用update方法在实例化模板时处理越界

        # 确保x坐标不小于页面边距
        x = max(x, self.margin / cm)
        # 确保y坐标在页面范围内
        y = min(max(y, self.margin / cm), (self.page_height - self.margin) / cm)
        # 如果指定了宽度，确保不超过页面边界
        available_width = self.page_width - x * cm - self.margin
        width = min(width * cm if width else available_width, available_width)
        # 创建文本样式
        style = ParagraphStyle(
            'CustomStyle',
            parent=self.chinese_style,
            fontSize=font_size,
            fontName=font_name,
            alignment={'left': 0, 'center': 1, 'right': 2}[align],
            wordWrap='CJK'  # 支持中文换行
        )
        # 创建段落对象来计算尺寸
        p = Paragraph(text, style)
        w, h = p.wrap(width, self.page_height)
        # 计算当前页面可用高度
        available_height = y * cm - self.margin
        if h > available_height and auto_next_page:
            # 计算分割点
            split_ratio = available_height / h
            split_index = int(len(text) * split_ratio)
            # 尝试在合适的位置分割文本
            split_chars = ['。', '！', '？', '；', '，', ' ', '\n']
            for i in range(split_index, 0, -1):
                if text[i] in split_chars:
                    split_index = i + 1
                    break
            # 分割文本
            current_page_text = text[:split_index]
            next_page_text = text[split_index:]
            # 添加当前页面的文本
            element = TextElement(
                current_page_text,
                page_number,
                x,
                y,
                width / cm,
                font_size,
                align,
                font_name,
                False  # 当前页面文本不需要再分页
            )
            self.elements.append(element)
            # 如果还有剩余文本，添加到下一页
            if next_page_text.strip():
                self.add_text(
                    next_page_text,
                    page_number + 1,
                    x,
                    (self.page_height - self.margin) / cm,  # 新页面顶部
                    width / cm,
                    font_size,
                    align,
                    font_name,
                    auto_next_page  # 继续启用自动分页
                )
        else:
            # 如果不需要分页，直接添加全部文本
            element = TextElement(
                text,
                page_number,
                x,
                y,
                width / cm,
                font_size,
                align,
                font_name,
                False
            )
            self.elements.append(element)
        return min(h, available_height)

    def update_text(self, index, text, page_number, x, y, width=None, font_size=12,
                    align='left', font_name='SimSun'):
        """
        更新文本
        """
        # 返回分段后的高度
        # 确保x坐标不小于页面边距
        x = max(x, self.margin / cm)
        # 确保y坐标在页面范围内
        y = min(max(y, self.margin / cm), (self.page_height - self.margin) / cm)
        # 如果指定了宽度，确保不超过页面边界
        available_width = self.page_width - x * cm - self.margin
        width = min(width * cm if width else available_width, available_width)
        # 创建文本样式
        style = ParagraphStyle(
            'CustomStyle',
            parent=self.chinese_style,
            fontSize=font_size,
            fontName=font_name,
            alignment={'left': 0, 'center': 1, 'right': 2}[align],
            wordWrap='CJK'  # 支持中文换行
        )
        # 创建段落对象来计算尺寸
        p = Paragraph(text, style)
        w, h = p.wrap(width, self.page_height)
        # 计算当前页面可用高度
        element = TextElement(
            text,
            page_number,
            x,
            y,
            width / cm,
            font_size,
            align,
            font_name,
            False
        )
        self.elements[index] = element
        return h

    def add_image(self, image_path, page_number, x, y, width=None, height=None):
        """
        添加图片
        :param image_path: 图片路径
        :param page_number: 页码
        :param x: x坐标（cm）
        :param y: y坐标（cm）
        :param width: 图片宽度（cm）
        :param height: 图片高度（cm）
        """
        element = ImageElement(image_path, page_number, x, y, width, height)
        self.elements.append(element)

    def _calculate_optimal_widths(self, data, total_width, font_name, font_size):
        """
        计算最优列宽分配
        :param data: 表格数据
        :param total_width: 总宽度（点）
        :param font_name: 字体名字
        :param font_size: 字体大小
        :return: 列宽列表（点）
        """
        if not data or not isinstance(data, list) or len(data) == 0:
            return []
            
        # 获取最大列数，防止 IndexError
        num_cols = 0
        for row in data:
            if isinstance(row, (list, tuple)):
                num_cols = max(num_cols, len(row))
        
        if num_cols == 0:
            return []
            
        # 计算每列的最大内容宽度
        max_widths = [0] * num_cols
        for row in data:
            if not isinstance(row, (list, tuple)):
                continue
            for i, cell in enumerate(row):
                if i >= num_cols: break # 冗余检查
                # 处理多行文本
                lines = str(cell if cell is not None else "").split('\n')
                for line in lines:
                    # 使用当前字体计算文本宽度
                    width = stringWidth(line, font_name, font_size)
                    max_widths[i] = max(max_widths[i], width)
        # 添加一些padding（左右各5点）
        padding = 10
        max_widths = [w + padding for w in max_widths]
        # 计算总需求宽度
        total_needed = sum(max_widths)
        if total_needed <= 0: return [total_width / num_cols] * num_cols
        
        # 按比例分配可用宽度
        ratio = total_width / total_needed
        col_widths = [w * ratio for w in max_widths]
        return col_widths

    def add_table(self, data, page_number, x, y, width, table_styles=None, col_widths=None,
                  wrap_cols=None, row_heights=None, font_size=10, align='left', font_name='SimSun', factor=1.2):
        """
        添加表格
        :return: 表格实际高度（cm）
        """
        # 转换列宽和行高为点数
        if not col_widths:
            col_widths = self._calculate_optimal_widths(data, width * cm, font_name, font_size)
        else:
            col_widths = [w * cm for w in col_widths]
            
        # 创建表格元素
        element = TableElement(data, page_number, x, y, width, table_styles, col_widths,
                               wrap_cols, row_heights, font_size, align, font_name, factor)
        
        # 直接计算高度，避免创建临时文件
        table_height = self._get_table_height(element)
        
        # 添加表格元素到列表
        self.elements.append(element)
        # 返回表格高度（转换为厘米）
        return table_height / cm

    def update_table(self, index, data, page_number, x, y, width, table_styles=None, col_widths=None,
                     wrap_cols=None, row_heights=None, font_size=12, align='left', font_name='SimSun', factor=1.2):
        # 转换列宽和行高为点数
        if not col_widths:
            col_widths = self._calculate_optimal_widths(data, width * cm, font_name, font_size)
        else:
            col_widths = [w * cm for w in col_widths]
            
        # 创建表格元素
        element = TableElement(data, page_number, x, y, width, table_styles, col_widths,
                               wrap_cols, row_heights, font_size, align, font_name, factor)
        
        # 直接计算高度
        table_height = self._get_table_height(element)
        
        # 更新表格元素
        self.elements[index] = element
        # 返回表格高度（转换为厘米）
        return table_height / cm

    def _get_table_height(self, element):
        """仅用于计算表格高度，不进行实际绘制"""
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            wordWrap='CJK',
            fontSize=element.font_size,
            fontName=element.font_name,
            alignment={'left': 0, 'center': 1, 'right': 2}[element.align],
            leading=element.font_size * element.factor
        )
        
        processed_data = []
        max_cols = 0
        if element.content:
            for row in element.content:
                if isinstance(row, (list, tuple)):
                    max_cols = max(max_cols, len(row))

        for row in element.content:
            processed_row = []
            if not isinstance(row, (list, tuple)):
                continue
            for col_idx in range(max_cols):
                cell = row[col_idx] if col_idx < len(row) else ""
                cell = cell if cell is not None else ""
                if element.wrap_cols and col_idx in element.wrap_cols:
                    cell = Paragraph(str(cell), cell_style)
                processed_row.append(cell)
            processed_data.append(processed_row)
            
        if not processed_data:
            return 0
            
        table = Table(processed_data, colWidths=element.col_widths, 
                      rowHeights=element.row_heights)
        table.setStyle(element.table_styles)
        # 使用 dummy canvas 只需要计算高度
        w, h = table.wrap(element.width * cm if hasattr(element, 'width') and element.width else 1000, 10000)
        return h

    def add_line(self, page_number, start_x, start_y, end_x, end_y,
                 line_width=0.1, line_color=colors.black, dash_pattern=None):
        """
        添加直线
        :param page_number: 页码
        :param start_x: 起点x坐标（cm）
        :param start_y: 起点y坐标（cm）
        :param end_x: 终点x坐标（cm）
        :param end_y: 终点y坐标（cm）
        :param line_width: 线条宽度（cm）
        :param line_color: 线条颜色
        :param dash_pattern: 虚线模式，如 [1, 2] 表示1个点划线2个点空白
        """
        element = LineElement(page_number, start_x, start_y, end_x, end_y,
                              line_width, line_color, dash_pattern)
        self.elements.append(element)

    def _draw_text(self, canvas, element):
        available_width = self.page_width - element.x - self.margin
        width = min(element.width, available_width) if element.width else available_width
        style = ParagraphStyle(
            'CustomStyle',
            parent=self.chinese_style,
            fontSize=element.font_size,
            fontName=element.font_name,
            alignment={'left': 0, 'center': 1, 'right': 2}[element.align],
            wordWrap='CJK'
        )
        p = Paragraph(element.content, style)
        w, h = p.wrap(width, self.page_height)
        p.drawOn(canvas, element.x, element.y - h)

    def _draw_image(self, canvas, element):
        if not element.content or not os.path.exists(element.content):
            print(f"警告: 忽略未找到的图片: {element.content}")
            return
        try:
            img = Image(element.content)
            if element.width:
                img.drawWidth = element.width
            if element.height:
                img.drawHeight = element.height
            img.drawOn(canvas, element.x, element.y)
        except Exception as e:
            print(f"Error drawing image {element.content}: {e}")

    def _draw_table(self, canvas, element, dry_run=False):
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            wordWrap='CJK',
            fontSize=element.font_size,
            fontName=element.font_name,
            alignment={'left': 0, 'center': 1, 'right': 2}[element.align],
            leading=element.font_size * element.factor
        )
        processed_data = []
        
        # 确定最大列数，补齐所有行
        max_cols = 0
        if element.content:
            for row in element.content:
                if isinstance(row, (list, tuple)):
                    max_cols = max(max_cols, len(row))

        for row in element.content:
            processed_row = []
            if not isinstance(row, (list, tuple)):
                continue
            for col_idx in range(max_cols):
                cell = row[col_idx] if col_idx < len(row) else ""
                cell = cell if cell is not None else ""  # 空值处理
                if element.wrap_cols and col_idx in element.wrap_cols:
                    cell = Paragraph(str(cell), cell_style)
                processed_row.append(cell)
            processed_data.append(processed_row)
            
        if not processed_data:
            return 0
            
        table = Table(processed_data, colWidths=element.col_widths,
                      rowHeights=element.row_heights)
        table.setStyle(element.table_styles)
        table.wrapOn(canvas, element.width, element.height or 1000)
        if not dry_run:
            table.drawOn(canvas, element.x, element.y - table._height)
        return table._height if dry_run else None

    def _draw_line(self, canvas, element):
        canvas.setStrokeColor(element.line_color)
        canvas.setLineWidth(element.line_width)
        if element.dash_pattern:
            canvas.setDash(element.dash_pattern)
        canvas.line(element.x, element.y, element.end_x, element.end_y)
        # 重置虚线设置
        if element.dash_pattern:
            canvas.setDash()

    def generate(self):
        canvas_obj = canvas.Canvas(self.output_path, pagesize=self.page_size)
        # 按页码分组元素并排序
        page_elements = {}
        for element in sorted(self.elements, key=lambda x: x.page_number):
            if element.page_number not in page_elements:
                page_elements[element.page_number] = []
            page_elements[element.page_number].append(element)
        for page_num in sorted(page_elements.keys()):
            if page_num > 1:
                canvas_obj.showPage()
            for element in page_elements[page_num]:
                if isinstance(element, TextElement):
                    self._draw_text(canvas_obj, element)
                elif isinstance(element, ImageElement):
                    self._draw_image(canvas_obj, element)
                elif isinstance(element, TableElement):
                    self._draw_table(canvas_obj, element)
                elif isinstance(element, LineElement):
                    self._draw_line(canvas_obj, element)
        canvas_obj.save()


#生成指定模板的报告
#这一部分仍然有着死数据问题，但至少把生成pdf的类剥离出来了（就是上面的那几个类）
class property_report:
    def __init__(self, out_file_path: str, property_name: str, pagesize=A4):
        self.index = ""  # 报告编号
        self.result = PDFGenerator(out_file_path)  # 生成的pdf对象
        self.pagenum = 0  # 总页数
        self.title = ""  # 报告标题
        self.subtitle = ""  # 报告副标题
        self.date = date.today().strftime("%Y年%m月%d日")  # 日期
        self.property_name = property_name  # 房产名名称
        self.width = pagesize[0] / cm
        self.height = pagesize[1] / cm  # 页面宽高（厘米）
        self.template = {
            "敬启者：": "",
            "主旨：": "",
            "__前言": {
                "估值委托、用途及日期": "",
                "市场价值定义": "",
                "估值假设": "",
                "评估方法": "",
                "资料来源": "",
                "业权查核": "",
                "现场勘查": "",
                "币值": "",
            },
            "评估物业": {
                "物业位置": ""
            },
            "区域位置": {
                "__城市": (),
                "人口，面积及行政区划": "",
                "邻近环境及建筑物": "",
                "交通条件": "",
            },
            "业权状况": {
                "__制度简介": (),
                "相关权证": "",
                "表格集": [pd.DataFrame()],
            },
            "物业概况": {
                "__": ""
            },
            "占用概况": {
                "__": ""
            },
            "评估基准": {
                "评估物业": "",
                "估值假设及特殊假设": ""
            },
            "估值结果": {
                "估值结果": "",
                "非出版物及注意事项": ""
            },
            "__附录": {},
            "目录 ": {
                "评估物业": 0,
                "区域位置": 0,
                "业权状况": 0,
                "物业概况": 0,
                "占用概况": 0,
                "评估基准": 0,
                "估值结果": 0,
            },
        }  # 房产估价模板

    def fill_template(self, value, key1=None, key2=None):
        """
        填充模板内容
        :param value: 填入的值
        :param key1: 第一级键
        :param key2: 第二级键
        """
        if key1 is None:
            if not isinstance(value, dict):
                raise ValueError("若无 key1，value 必须为字典类型")
            self.template = value
        elif key2 is None:
            self.template[key1] = value
        else:
            self.template[key1][key2] = value

    # 以下函数开始，体现模板各个参数，有些作为接口，有些写死在函数内部
    # 添加封面
    def set_cover(self, cover_img=None, title: str = None, subtitle: str = None):
        if title == None:
            self.title = "房地产评估估值报告"
        if subtitle == None:
            self.subtitle = self.property_name + "\n之市场价值评估"
        if cover_img != None:
            self.result.add_image(image_path=cover_img, page_number=1,
                                  x=self.width / 10, y=self.height / 3,
                                  width=self.width / 3, height=self.height / 4)
        self.result.add_text(text=self.title, x=self.width / 10, y=4 * self.height / 5,
                             font_name="SimHei", font_size=16, page_number=1, width=16 * 12)
        self.result.add_text(text=self.subtitle, x=self.width / 10, y=2 * self.height / 3,
                             font_name="SimHei", font_size=12, page_number=1, width=12 * 12)
        self.result.add_text(text=self.date, x=self.width / 10, y=self.height / 5,
                             font_name="SimHei", font_size=10, page_number=1, width=10 * 12)

    # 页眉页底文字(即重复出现的文字、图片)
    def set_up_down_label(self, logo_img=None, start_page=1, end_page=None, index: str = ""):
        self.index = index
        if end_page == None:
            end_page = self.pagenum
        assert start_page >= 1 and end_page <= self.pagenum, "页面数越界"
        font = "simkai"
        size = 10
        for i in range(start_page, end_page + 1):
            if logo_img is not None:
                self.result.add_image(image_path=logo_img, x=7 * self.width / 10, y=92 * self.height / 100,
                                      page_number=i, width=2 * self.width / 10, height=7 * self.height / 100)
            h1 = self.result.add_text(text=self.property_name, x=self.width / 10, y=9 * self.height / 10,
                                      page_number=i, width=19 * size / cm, font_name=font, font_size=size)
            h2 = self.result.add_text(text="估价时点:" + self.date, x=70 * self.width / 100, y=9 * self.height / 10,
                                      page_number=i, width=20 * size / cm, font_name=font, font_size=size)
            self.result.add_line(start_x=self.width / 10, start_y=89 * self.height / 100 + size / cm * 1.3,
                                 end_x=91 * self.width / 100, end_y=89 * self.height / 100 + size / cm * 1.3,
                                 line_width=0.05, page_number=i)
            self.result.add_line(start_x=self.width / 10, start_y=90 * self.height / 100 - max(h1, h2) / cm,
                                 end_x=91 * self.width / 100, end_y=90 * self.height / 100 - max(h1, h2) / cm,
                                 line_width=0.05, page_number=i)
            self.result.add_text(text=str("报告编号:" + self.index), font_name="SimHei", font_size=size,
                                 x=self.width / 10, y=self.height / 15, page_number=i)
            page_str = f"%d/%d" % (i, self.pagenum)
            str_length = sum([stringWidth(char, font, size) for char in page_str])
            self.result.add_text(text=str(page_str), font_name="SimHei", font_size=size,
                                 x=9 * self.width / 10 - str_length / cm, y=self.height / 15, page_number=i)
            self.result.add_line(start_x=self.width / 10, start_y=self.height / 15 + size / cm * 1.2,
                                 end_x=91 * self.width / 100, end_y=self.height / 15 + size / cm * 1.2,
                                 line_width=0.02, page_number=i)

    def template_to_l(self):
        """将模板字典转换为 PDF 元素列表"""
        page_n = 2  # 封面页之后开始
        start_x = self.width / 10
        start_y = 85 * self.height / 100
        y = start_y
        
        # 定义字号和布局常量
        title_size, sub2_size, content_size = 16, 12, 11
        subtitle_width, content_width = 6, 34
        min_y = 2 * self.height / 15
        content_page = 0

        for key in self.template:
            # 1. 直接文本渲染项
            if key in ["敬启者：", "主旨："]:
                if self.template[key]:
                    self.result.add_text(text=key + self.template[key], x=start_x, y=y,
                                         page_number=2, font_name="SimHei", font_size=sub2_size)
                    y -= sub2_size / cm * 2.2
                continue

            # 2. 附录渲染容器
            elif key == "__附录":
                for app_title, img_list in self.template[key].items():
                    self.result.add_text(text=str(app_title), x=self.width / 2 - len(app_title) / 2 * title_size / cm, y=y,
                                         page_number=page_n, font_size=title_size)
                    y -= title_size / cm * 1.3
                    self.template["目录"][app_title] = page_n
                    
                    for img in img_list:
                        if not img or not os.path.exists(img):
                            continue
                        y, page_n = self._draw_appendix_image(img, start_x, y, min_y, start_y, page_n)

                    y, page_n = start_y, page_n + 1
                continue

            # 3. 目录渲染容器
            elif key == "目录":
                self.result.add_text(text=key, x=start_x, y=y, page_number=content_page, 
                                     font_name="SimHei", font_size=title_size)
                y -= title_size / cm * 2.2
                
                for toc_key, page_val in self.template[key].items():
                    # 生成带点的目录行
                    dots = "." * (60 - len(toc_key) * 2)
                    toc_line = f"{toc_key}{dots}{page_val}"
                    h = self.result.add_text(text=toc_line,
                                           x=start_x + (subtitle_width + 2) * sub2_size / cm,
                                           y=y, page_number=content_page,
                                           width=content_width * content_size / cm,
                                           font_name="SimHei", font_size=content_size)
                    y -= (h + content_size * 3) / cm
                    if y <= min_y:
                        y, page_n = start_y, page_n + 1
                        content_page = page_n
                y, page_n = start_y, page_n + 1
                continue

            # 4. 业务数据渲染项
            else:
                if key == "评估物业":
                    content_page = page_n
                    page_n += 1
                
                if not self.template[key]: continue

                if not key.startswith('_'):
                    self.result.add_text(text=key, x=start_x, y=y, page_number=page_n, 
                                         font_name="SimHei", font_size=title_size)
                    y -= title_size / cm * 2.2

                for sub_key, val in self.template[key].items():
                    if not val: continue

                    if sub_key == "表格集":
                        y, page_n = self._draw_toc_tables(val, start_x, y, min_y, start_y, page_n, 
                                                        subtitle_width, sub2_size, content_width, content_size)
                    else:
                        y, page_n = self._draw_template_item(sub_key, val, start_x, y, min_y, start_y, 
                                                            page_n, subtitle_width, content_width, 
                                                            sub2_size, content_size)

                if not key.startswith('_'):
                    self.template["目录"][key] = page_n
                
                if y <= 2 * self.height / 3:
                    y, page_n = start_y, page_n + 1

        self.pagenum = page_n - 2

    def _draw_appendix_image(self, img_path, start_x, y, min_y, start_y, page_n):
        """附录图片专用绘制逻辑，含比例适配"""
        try:
            reader = ImageReader(img_path)
            img_w, img_h = reader.getSize()
            body_w = self.width - 2 * start_x
            
            # 检查剩余空间是否足够
            if (img_w / img_h) >= (self.width / (y - min_y + 1e-6)):
                w, h = body_w, body_w * img_h / img_w
            else:
                # 空间不足，开启新页核心逻辑
                y, page_n = start_y, page_n + 1
                if (img_w / img_h) >= (self.width / (y - min_y + 1e-6)):
                    w, h = body_w, body_w * img_h / img_w
                else:
                    h = y - min_y
                    w = h * img_w / img_h
                    
            self.result.add_image(img_path, page_n, self.width / 2 - w / 2, y - h, w, h)
            return y - h, page_n
        except Exception as e:
            print(f"绘制附录图片失败: {e}")
            return y, page_n

    def _draw_toc_tables(self, tables, start_x, y, min_y, start_y, page_n, sub_w, sub_size, con_w, con_size):
        """绘制模板中的表格集容器"""
        styles = [
            ('FONT', (0, 0), (-1, -1), 'SimHei', 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 2, black),
            ('FONT', (1, 0), (1, -1), 'SimSun', 10),
        ]
        
        target_x = start_x + (sub_w + 2) * sub_size / cm
        aW = con_w * con_size / cm
        
        for data in tables:
            if not data: continue
            if (y - min_y) < (self.height / 3):
                y, page_n = start_y, page_n + 1
                
            L = len(data[0]) if data and len(data) > 0 else 1
            h = self.result.add_table(data, page_n, target_x, y, aW, 
                                     wrap_cols=list(range(L)), table_styles=styles)
            y -= h
            if y < min_y:
                y, page_n = start_y, page_n + 1
                h = self.result.update_table(-1, data, page_n, target_x, y, aW,
                                            wrap_cols=list(range(L)), table_styles=styles)
                y -= h
        return y, page_n

    def _draw_template_item(self, key, val, start_x, y, min_y, start_y, page_n, sub_w, con_w, sub_size, con_size):
        """通用模板项绘制（支持键值对、元组引导项）"""
        # 解析文本组合
        is_underscore = key.startswith('_')
        if is_underscore:
            sub_text, con_text = (val[0], val[1]) if isinstance(val, tuple) else ("", str(val))
        else:
            sub_text, con_text = key, str(val)

        # 辅助计算
        sub_x, con_x = start_x, start_x + (sub_w + 2) * sub_size / cm
        sub_width, con_width = sub_w * sub_size / cm, con_w * con_size / cm
        
        # 渲染
        h_sub = self.result.add_text(sub_text, page_n, sub_x, y, sub_width, sub_size, font_name="SimHei") if sub_text else 0
        h_con = self.result.add_text(con_text, page_n, con_x, y, con_width, con_size, font_name="SimSun")
        
        y -= (max(h_sub, h_con) + con_size * 3) / cm
        
        # 越界处理
        if y <= min_y:
            y, page_n = start_y, page_n + 1
            if sub_text:
                self.result.update_text(-1 if not is_underscore else -2, sub_text, page_n, sub_x, y, 
                                      sub_width, sub_size, font_name="SimHei")
            self.result.update_text(-1, con_text, page_n, con_x, y, con_width, con_size, font_name="SimSun")
            y -= (con_size * 5) / cm
            
        return y, page_n

    # 类似 test 函数，纯调试用
    def model_report(self, cover_img=None, logo_img=None, client_name: str = "", property_index: str = "",
                     property_summary: str = "", report_index: str = "",
                     ocr_table: list = None, appendix: dict = None, city: tuple = ("", "", ""), environment: str = "",
                     traffic: str = "", property_size="",
                     property_price: int = 0, occupancy: str = "于估价时点，估价对象为空置状态"):
        if appendix is None:
            appendix = {}
        self.set_cover(cover_img)
        value = {
            "敬启者：": f"%s" % client_name,
            "主旨：": f"%s（“评估物业”）" % self.property_name,
            "__前言": {
                "估值委托、用途及日期": f"我们根据委托人的指示，对上述位于中华人民共和国（中国）之该物业进行市场价值评估（详情请见随函附奉之估值报告）。我们证实曾实地勘查该物业，作出有关查询，并搜集我们认为必要之进一步资料，以便向委托人呈报我们对该物业于%s（估价时点）之市场价值意见，供 委托人作参考用途。" % cn2an.transform(
                    self.date, "an2cn"),
                "市场价值定义": "在评估该物业时，我们已符合英国皇家特许测量师学会颁布的英国皇家特许测量师学会物业估值准则（二〇二〇年版）所载的规定。我们对该物业以特殊假设条件为基准之估值乃该物业的市场价值，市场价值的定义为「自愿买方与自愿卖方各自在知情、审慎及无胁迫的情况下，对物业作出适当推销后，于估值日透过公平交易将物业转手的估计金额」。",
                "估值假设": "除特殊标明外，我们的估值并不包括因特别条款或情况（如非典型融资、售后租回安排、由任何与销售相关人士授出的特别考虑因素或特许权或任何特别价值因素）所抬高或贬低的估计价格。我们在评估该物业时，已假设有关物业权益之可转让土地使用权已按象征性土地使用年费批出，而任何应付之地价亦已全数缴清。就物业之业权状况，我们乃依赖由 贵公司所提供之意见。于估值而言，我们假设承让人对物业享有良好业权。我们亦已假设有关物业权益之承让人或使用人可于获批之土地使用年期尚未届满之整段期间，对有关物业享有自由及不受干预之使用权或转让权。我们之估值并无考虑该物业所欠负之任何抵押、按揭或债项，亦无考虑在出售物业权益时可能发生之任何开支或税项。除另有说明外，我们假定该物业概无附带可能影响其价值之他项权利、限制及繁重支销。",
                "评估方法": "我们采用比较法对该物业之现状价值进行评估。\n比较法，即经参考有关市场上可比之成交案例及价格得出评估物业之价值的方法。",
                "资料来源": "我们对该物业进行估值时，乃依赖产权方提供有关物业业权之法定文件副本，惟我们并无查阅文件正本以核实所有权或是否有任何修订并未见於我们所取得的副本。所有有关文件仅用作参考。\n我们在颇大程度上依赖产权方提供之资料并接纳向我们提供关于规划许可或法定通告、地役权、年期、占用情况、规划方案、土地识别、地块面积、规划建筑面积及所有其它相关事项之意见。\n载于本估值报告书内之尺寸、量度及面积均以提供予我们之文件所列载资料作基准，故仅为约数。我们并无理由怀疑产权方提供予我们之资料之真实性及准确性。我们并获知所有相关之重要事实已提供予我们，并无任何遗漏。",
                "业权查核": "我们曾获提供有关该物业业权之法定文档副本，惟我们并无进行查册以确认该物业之业权，或查核有否任何未有记载在该等交予我们之文档之修订条款。",
                "现场勘查": "我们曾勘察该物业之内、外部。然而，我们并未对地块进行勘测，以断定土地条件及设施等是否适合任何未来发展之用。我们的估值以此等各方面均令人满意及建筑期内将不会产生非经常费用及延误为基准。同时，我们也未进行详细的实地丈量以核实该物业之地块面积，我们乃假设该等提供予我们之资料所示之面积乃属正确。",
                "币值": "本报告除特殊标明外，所有货币单位为中华人民共和国法定货币单位：人民币。除非特殊标明外，我们评估该物业之100%权益。",
            },
            "评估物业": {
                "物业位置": f"评估物业位于%s" % self.property_name
            },
            "区域位置": {
                "__城市": city[0:2],
                "人口，面积及行政区划": city[2],
                "邻近环境及建筑物": environment,
                "交通条件": traffic,
            },
            "业权状况": {
                "__制度简介": ("中华人民共和国土地使用制度",
                               "根据《中华人民共和国宪法》(一九八八年修订案)第十条，中国建立了土地使用权与土地所有权两权分离制度。自此，有偿取得之有限年期之土地使用权均可在中国转让、赠予、出租、抵押。市级地方政府可通过拍卖、招标或挂牌三种方式将有限年期之土地使用权国有出让给国内及国外机构。一般情况下，土地使用权国有出让金将按一次性支付，土地使用者在支付全部土地使用权国有出让金后，可领取【国有土地使用证】。土地使用者同时需要支付其它配套公用设施费用、开发费及拆迁补偿费用予原居民。物业建成后，当地房地产管理部门将颁发【房屋所有权证】或【不动产权证】，以证明物业的房屋所有权。"),
                "相关权证": f"根据{property_index}，相关内容摘录如下：",
                "表格集": ocr_table,
            },
            "物业概况": {
                "__": property_summary,
            },
            "占用概况": {
                "__": occupancy
            },
            "评估基准": {
                "评估物业": f"评估物业为{self.property_name}，总建筑面积为{property_size}。",
                "估值假设及特殊假设": "我们的评估基于如下假设：\n(一) 评估物业可在剩余土地使用期限内自由转让，而无需向政府缴纳土地国有出让金及其他费用；\n(二) 评估物业的土地国有出让金、动拆迁及安置补偿费、市政配套费用已全部支付完毕；\n(三) 评估物业的规划设计符合当地城市规划要求且已获得相关部门批准；\n(四) 评估物业可以自由出售给任何买家;"
            },
            "估值结果": {
                "估值结果": f"综上所述，我们的意见认为，于估值日期%s，" % cn2an.transform(self.date,
                                                                                       "an2cn") + f"在估价假设和限制条件下，评估物业的现状下市场价值为人民币%d元" % property_price + f"(大写人民币%s)" % cn2an.an2cn(
                    f"%d" % property_price, "rmb"),
                "非出版物及注意事项": "如未得到本公司的书面许可，本估值报告书的全文或任何部份内容或任何注释，均不能以任何形式刊载于任何档、通函或声明。\n最后，根据本公司的一贯做法，我们必须申明，本估值报告书仅供委托方使用，本公司不承担对任何第三方对本报告书的全文或任何部份内容的任何责任。"
            },
            "__附录": appendix,
            "目录": {
                "评估物业": 0,
                "区域位置": 0,
                "业权状况": 0,
                "物业概况": 0,
                "占用概况": 0,
                "评估基准": 0,
                "估值结果": 0,
            },
        }
        if appendix is not None:
            for key in appendix.keys():
                value["目录"][key] = 0
        
        self.fill_template(value)
        self.template_to_l()
        self.set_up_down_label(logo_img, index=report_index)
        self.result.generate()

    def save_report(self, uid: int, record: Record):
        # 优先使用 record 中上传的 logo，如果没有则使用默认 logo
        if record.report_logo:
             # report_logo 可能是路径或文件名，如果是文件名需拼接
             if os.path.isabs(record.report_logo) or "/" in record.report_logo or "\\" in record.report_logo:
                 logo_img = record.report_logo
             else:
                 logo_img = os.path.join("static/uploads", record.report_logo)
        else:
             logo_img = "report/logo_img.png"
             
        cover_img = record.field_img[0] if record.field_img else None
        
        # 优先使用 record 中的委托人姓名
        if record.client_name:
            client_name = record.client_name
        else:
            client_name = "{}（委托人）".format(uid)  # TODO:数据库里根据uid查找用户名

        # 优先使用 record 中的物业概况描述
        if record.property_overview:
            property_summary = record.property_overview
        else:
            property_summary = (
                f"估价对象位于「{record.house_location}」内，该社区于{record.house_year}年竣工。根据估价人员现场勘查及权利人提供之相关资料，"
                f"估价对象为{record.house_type}的户型。总建筑面积为{record.house_area}平方米。估价对象为{record.house_structure}。"
                f"于估价时点，估价对象为{record.house_decorating}。")
        
        # property_index = "【房地产权证】沪(2017)浦字不动产权第015342号"
        property_index = "【房地产权证】"
        print(record.production_ocr)
        ocr_table = []
        if record.production_ocr and os.path.exists(record.production_ocr):
            try:
                raw_ocr = OCR_Table().trans_to_df(record.production_ocr)
                if raw_ocr:
                    # 获取第一页数据
                    ocr_table = raw_ocr[0] if isinstance(raw_ocr, list) else []
                    # 遍历并清洗数据 (替换 None 为空字符)
                    if isinstance(ocr_table, list):
                        for i in range(len(ocr_table)):
                            if isinstance(ocr_table[i], (list, tuple)):
                                ocr_table[i] = [str(cell) if cell is not None else "" for cell in ocr_table[i]]
            except Exception as e:
                print(f"OCR表格转化失败: {str(e)}")
        appendix = {
            "附录一": [record.map] if record.map else [],
            "附录二": record.production_cert_img if record.production_cert_img else [],
            "附录三": record.field_img if record.field_img else []
        }
        
        # 获取城市信息 (防御逻辑)
        try:
            with MySQLManager() as mgr:
                city_introduction, city_detail = mgr.get_city_info(record.city)
        except Exception as e:
            print(f"获取城市信息出错: {e}")
            city_introduction, city_detail = None, None
            
        city = (record.city, 
                city_introduction or f"{record.city}市是中国重要的中心城市之一。", 
                city_detail or "区域内拥有完善的基础设施与良好的经济基础。")
        
        # 优先使用 record 中的环境描述
        if record.surrounding_environment:
            environment = record.surrounding_environment
        else:
            try:
                # environment_main 已经在文件顶部从 record.save_map 导入
                environment = environment_main(record.house_location, record.city)
            except:
                environment = f"{record.house_location}周边环境优美，配套设施齐全。"

        # 优先使用 record 中的交通描述
        if record.traffic_conditions:
            traffic = record.traffic_conditions
        else:
            traffic = "评估物业交通便利，周边路网干线丰富，公交和出租车均可到达。\n\n评估物业坐落图请见附录1"
            
        # 占用状况
        occupancy = record.occupancy_status if record.occupancy_status else "于估价时点，估价对象为空置状态"
        
        property_price = int(record.price * (record.house_area if record.house_area else 0))
        report_index = f"No.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.model_report(cover_img=cover_img, logo_img=logo_img, client_name=client_name,
                          property_summary=property_summary, property_index=property_index,
                          ocr_table=ocr_table, appendix=appendix, city=city, environment=environment,
                          traffic=traffic, property_price=property_price, property_size=str(record.house_area),
                          report_index=report_index, occupancy=occupancy)


# if __name__ == "__main__":
#     filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_report.pdf"
#     file_path = f"{REPORT_PATH}/{filename}"
#     u_id = 17
#     u_record = Record(u_id)
#     u_record.house_location = "兰谷路2777弄"
#     u_record.city = "上海"
#     u_record.house_area = 136.79
#     u_record.house_type = "2室1厅1厨2卫"
#     u_record.house_year = 2013
#     u_record.house_floor = "低楼层"
#     u_record.house_decorating = "简装"
#     u_record.green_rate = 0.3
#     u_record.price = 88268.3
#     u_record.map = "../static/maps/20250226143736.png"
#     u_record.production_cert_img = ["../static/uploads/20250227214853_cropped_image.png"]
#     u_record.production_ocr = "../static/ocr_tables/ocr_data_20250227_214856.xlsx"
#     u_record.field_img = ["../static/uploads/20250226143704_cropped_image.png",
#                           "../static/uploads/20250226185033_cropped_image.png",
#                           "../static/uploads/20250226185045_cropped_image.png"]
#
#     case = property_report(file_path, u_record.house_location)
#     case.save_report(u_id, u_record)
#     # if os.path.exists("../static/ocr_tables/ocr_data_20250227_213039.xlsx"):
#     #     print("文件存在")
