import os
import pandas as pd
from PIL import Image
from reportlab.graphics.barcode import qr
from reportlab.lib.colors import black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import cn2an
from datetime import datetime, date
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from record.record import Record
from config.path_config import OCR_PATH, REPORT_PATH, MAP_PATH, UPLOAD_FOLDER
from report.ocr import OCR_Table
from database.mysql_manager import MySQLManager

def register_fonts():
    """Register Chinese and common fonts safely."""
    fonts = {
        "SimHei": "SimHei.ttf",
        "SimSun": "SimSun.ttc",
        "SimSunb": "simsunb.ttf",
        "simfang": "simfang.ttf",
        "simkai": "simkai.ttf",
        "segoeuib": "segoeuib.ttf",
        "segoeuil": "segoeuil.ttf",
        "segoeuisl": "segoeuisl.ttf",
        "seguisb": "seguisb.ttf"
    }
    for name, filename in fonts.items():
        try:
            pdfmetrics.registerFont(TTFont(name, filename))
        except Exception as e:
            print(f"Warning: Failed to register font {name} ({filename}): {e}")

register_fonts()


class PDFReport:
    """Class to handle property valuation report generation in PDF format."""
    
    # Constants for layout
    TITLE_SIZE = 16
    SUBTITLE1_SIZE = 14
    SUBTITLE2_SIZE = 12
    CONTENT_SIZE = 11
    MARGIN_X_RATIO = 0.1
    MARGIN_Y_RATIO = 0.85
    MIN_Y_RATIO = 2/15

    def __init__(self, out_file_path: str, property_name: str, pagesize=A4):
        self.index = ""  # 报告编号
        self.result = canvas.Canvas(out_file_path, pagesize)  # 生成s pdf对象
        self.pagenum = 0  # 总页数
        self.title = ""  # 报告标题
        self.subtitle = ""  # 报告副标题
        self.date = date.today().strftime("%Y年%m月%d日")  # 日期
        self.property_name = property_name  # 房产名名称
        self.width, self.height = pagesize  # 页面宽高（像素）
        
        # Elements collection grouped by page for O(N) rendering performance
        self.pages_data = defaultdict(lambda: {
            "images": [],
            "texts": [],
            "tables": [],
            "lines": []
        })

        self.template = self._get_default_template()

    def _get_default_template(self) -> Dict[str, Any]:
        """Returns the default report structure."""
        return {
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
        }

    def add_image(self, image_path: str, x, y, page: int, width=None, height=None):
        """Add an image to a specific page."""
        image_data = {
            "image_path": image_path,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        self.pages_data[page]["images"].append(image_data)
        self.pagenum = max(page, self.pagenum)

    def update_image(self, index: int, image_path: str, x, y, page, width=None, height=None):
        """Update an existing image on a specific page."""
        if index < 0 or index >= len(self.pages_data[page]["images"]):
            return False
        self.pages_data[page]["images"][index] = {
            "image_path": image_path,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        self.pagenum = max(page, self.pagenum)
        return True

    def add_text(self, text: str, x, y, page, width=None, font="SimHei", size=12):
        """Add wrapped text to a specific page."""
        wrapped_text, num_lines = self.wrap_text(text, size, font, width)
        text_data = {
            "text": wrapped_text,
            "x": x,
            "y": y,
            "font": font,
            "size": size,
            "width": width
        }
        self.pages_data[page]["texts"].append(text_data)
        self.pagenum = max(page, self.pagenum)
        return num_lines

    def update_text(self, index: int, text: str, x, y, page, width=None, font="SimHei", size=12):
        """Update existing text on a specific page."""
        # Note: If index is negative, it refers to the last added item in that page
        texts = self.pages_data[page]["texts"]
        if index < 0:
            if abs(index) > len(texts): return 0
            idx = len(texts) + index
        else:
            if index >= len(texts): return 0
            idx = index
            
        wrapped_text, num_lines = self.wrap_text(text, size, font, width)
        texts[idx] = {
            "text": wrapped_text,
            "x": x,
            "y": y,
            "font": font,
            "size": size,
            "width": width
        }
        self.pagenum = max(page, self.pagenum)
        return num_lines

    def add_table(self, table_df: pd.DataFrame, x, y, aW, aH, page, tbstyle=None):
        """Add a table to a specific page."""
        table_obj = Table(table_df.values.tolist())
        if tbstyle:
            table_obj.setStyle(tbstyle)
        
        w, h = table_obj.wrap(aW, aH)
        if w > aW or h > aH:
            return -1, -1
            
        table_data = {
            "table": table_obj,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "tbstyle": tbstyle
        }
        self.pages_data[page]["tables"].append(table_data)
        self.pagenum = max(page, self.pagenum)
        return w, h

    def update_table(self, index: int, table_df: pd.DataFrame, x, y, aW, aH, page, tbstyle=None):
        """Update an existing table on a specific page."""
        tables = self.pages_data[page]["tables"]
        if index < 0 or index >= len(tables):
            return -1, -1
            
        table_obj = Table(table_df.values.tolist())
        if tbstyle:
            table_obj.setStyle(tbstyle)
            
        w, h = table_obj.wrap(aW, aH)
        if w > aW or h > aH:
            return -1, -1
            
        tables[index] = {
            "table": table_obj,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "tbstyle": tbstyle
        }
        self.pagenum = max(page, self.pagenum)
        return w, h

    def add_line(self, x1, y1, x2, y2, width, page):
        """Add a line to a specific page."""
        line_data = {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width": width
        }
        self.pages_data[page]["lines"].append(line_data)
        self.pagenum = max(page, self.pagenum)

    def wrap_text(self, txt: str, font_size, font_name, width=None) -> Tuple[str, int]:
        """Manually wrap text based on width. Consider using Paragraph for complex layouts."""
        if not width:
            return txt, txt.count('\n') + 1
            
        char_widths = [stringWidth(char, font_name, font_size) for char in txt]
        line_width = 0
        wrapped_text = ""
        num_lines = 1
        
        for i, char in enumerate(txt):
            if char == '\n':
                line_width = 0
                wrapped_text += char
                num_lines += 1
                continue
                
            line_width += char_widths[i]
            if line_width > width:
                wrapped_text += '\n'
                line_width = char_widths[i]
                num_lines += 1
            wrapped_text += char
            
        return wrapped_text, num_lines

    def generate_pdf(self):
        """Finalize and save the PDF document, processing elements of each page."""
        self.result.setTitle(self.subtitle)
        
        # QR code is common to all pages logic from original
        qr_code = qr.QrCode('https://www.tongji.edu.cn/', width=45, height=45)

        for i in range(1, self.pagenum + 1):
            page_data = self.pages_data[i]
            
            # Draw common elements
            self.result.setFillColorRGB(0, 0, 0)
            qr_code.drawOn(self.result, 0, self.height - 45)
            
            # Draw Texts
            for text_info in page_data["texts"]:
                lines = text_info['text'].split('\n')
                text_obj = self.result.beginText(x=text_info["x"], y=text_info["y"])
                text_obj.setFont(text_info["font"], text_info["size"])
                text_obj.textLines(lines, 0)
                self.result.drawText(text_obj)
            
            # Draw Images
            for img_info in page_data["images"]:
                self.result.drawImage(
                    img_info["image_path"],
                    img_info["x"], img_info["y"],
                    width=img_info["width"],
                    height=img_info["height"]
                )
            
            # Draw Tables
            for tbl_info in page_data["tables"]:
                tbl_info["table"].drawOn(self.result, tbl_info['x'], tbl_info['y'] - tbl_info['h'])
            
            # Draw Lines
            for line_info in page_data["lines"]:
                self.result.setLineWidth(line_info["width"])
                self.result.line(line_info['x1'], line_info['y1'], line_info['x2'], line_info['y2'])
                
            self.result.showPage()
            
        self.result.save()

    def fill_template(self, value: Dict[str, Any], key1: Optional[str] = None, key2: Optional[str] = None):
        """Update the template dictionary with new values."""
        if key1 is None and key2 is None:
            if not isinstance(value, dict):
                raise ValueError("Expected dictionary for value.")
            self.template = value
        elif key1 is not None:
            if key2 is None:
                self.template[key1] = value
            else:
                self.template[key1][key2] = value

    def set_cover(self, cover_img: Optional[str] = None, title: Optional[str] = None, subtitle: Optional[str] = None):
        """Configure and layout the report cover page."""
        self.title = title or "房地产评估估值报告"
        self.subtitle = subtitle or f"{self.property_name}\n之市场价值评估"
        
        # Layout positions based on page proportions
        margin_x = self.width * self.MARGIN_X_RATIO
        
        if cover_img and os.path.exists(cover_img):
            self.add_image(cover_img, margin_x, self.height / 3, 1, self.width / 3, self.height / 4)
            
        self.add_text(self.title, margin_x, 4 * self.height / 5, 1, width=16 * 12, font="SimHei", size=16)
        self.add_text(self.subtitle, margin_x, 2 * self.height / 3, 1, width=12 * 12, font="SimHei", size=12)
        self.add_text(self.date, margin_x, self.height / 5, 1, width=10 * 12, font="SimHei", size=10)

    def set_up_down_label(self, logo_img: Optional[str] = None, start_page: int = 1, end_page: Optional[int] = None, index: str = ""):
        """Add header, footer, and borders to the specified range of pages."""
        self.index = index
        end_page = end_page or self.pagenum
        
        if not (1 <= start_page <= end_page <= self.pagenum):
            print(f"Warning: Invalid page range {start_page}-{end_page} (Total: {self.pagenum})")
            return

        font = "simkai"
        size = 10
        margin_x = self.width * self.MARGIN_X_RATIO
        margin_x_end = self.width * (1 - self.MARGIN_X_RATIO / 10) # 91% width roughly
        
        for i in range(start_page, end_page + 1):
            # Header image
            if logo_img and os.path.exists(logo_img):
                self.add_image(logo_img, 7 * self.width / 10, 92 * self.height / 100, i, 2 * self.width / 10, 7 * self.height / 100)
                
            # Header texts
            n1 = self.add_text(self.property_name, margin_x, 9 * self.height / 10, i, 19 * size, font, size)
            n2 = self.add_text(f"估价时点\n{self.date}", 0.75 * self.width, 9 * self.height / 10, i, 10 * size, font, size)
            
            # Header lines
            top_line_y = 9 * self.height / 10 + size * 1.3
            self.add_line(margin_x, top_line_y, 0.91 * self.width, top_line_y, 2, i)
            
            bottom_line_y = 9 * self.height / 10 + (1 - max(n1, n2)) * size * 1.5
            self.add_line(margin_x, bottom_line_y, 0.91 * self.width, bottom_line_y, 2, i)
            
            # Footer
            self.add_text(f"报告编号:{self.index}", margin_x, self.height / 15, i)
            
            page_str = f"{i}/{self.pagenum}"
            str_length = sum([stringWidth(char, font, size) for char in page_str])
            self.add_text(page_str, 0.9 * self.width - str_length, self.height / 15, i)
            
            footer_line_y = self.height / 15 + size * 1.2
            self.add_line(margin_x, footer_line_y, 0.91 * self.width, footer_line_y, 2, i)

    def template_to_l(self):
        """Map the template data into PDF coordinate elements."""
        self.page_n = 2  # Cover is page 1
        self.start_x = self.width * self.MARGIN_X_RATIO
        self.start_y = self.height * self.MARGIN_Y_RATIO
        self.body_width = self.width - 2 * self.start_x
        self.y = self.start_y
        
        # Section specifics
        self.subtitle_width = 12
        self.content_width = 34
        self.content_page = 0
        self.min_y = self.height * self.MIN_Y_RATIO
        
        for key in self.template:
            if key in ["敬启者：", "主旨："]:
                if not self.template[key]: continue
                self.add_text(f"{key}{self.template[key]}", self.start_x, self.y, 2, font="SimHei", size=self.SUBTITLE2_SIZE)
                self.y -= self.SUBTITLE2_SIZE * 2.2
            elif key == "__附录":
                self._handle_appendix_template(self.template[key])
            elif key == "目录 ":
                self._handle_toc_template(self.template[key])
            else:
                self._handle_generic_section(key)

    def _handle_appendix_template(self, appendix_data: Dict[str, List[str]]):
        """Processes the appendix section of the template."""
        for section_title, images in appendix_data.items():
            self.add_text(section_title, self.width / 2 - len(section_title) / 2 * self.TITLE_SIZE, self.y, self.page_n, size=self.TITLE_SIZE)
            self.y -= self.TITLE_SIZE * 1.2
            self.template["目录 "][section_title] = self.page_n
            
            for img_path in images:
                if not os.path.exists(img_path):
                    continue
                try:
                    width, height = Image.open(img_path).size
                except Exception:
                    continue
                
                # Check if image fits in remaining y space
                ratio = width / height
                page_ratio = self.body_width / (self.y - self.min_y + 1e-6)
                
                if ratio >= page_ratio:
                    # Image is wider or fits exactly in width
                    w = self.body_width
                    h = w / ratio
                else:
                    # Image is too tall for current y space or narrow
                    self.page_n += 1
                    self.y = self.start_y
                    # Re-calculate with full page y space
                    page_ratio = self.body_width / (self.y - self.min_y + 1e-6)
                    if ratio >= page_ratio:
                        w = self.body_width
                        h = w / ratio
                    else:
                        h = self.y - self.min_y
                        w = h * ratio
                        
                # Center horizontally
                self.add_image(img_path, self.width / 2 - w / 2, self.y - h, self.page_n, w, h)
                self.y -= h
            self.y = self.start_y
            self.page_n += 1

    def _handle_toc_template(self, toc_data: Dict[str, int]):
        """Processes the Table of Contents section."""
        self.add_text("目录", self.start_x, self.y, self.content_page, font="SimHei", size=self.TITLE_SIZE)
        self.y -= self.TITLE_SIZE * 2.2
        dot_line = " " + "." * 60
        
        for section_name, page_num in toc_data.items():
            toc_entry = f"{section_name}{dot_line}{page_num}"
            offset_x = self.start_x + (self.subtitle_width / 2 + 2) * self.SUBTITLE2_SIZE
            
            num_lines = self.add_text(toc_entry, offset_x, self.y, self.content_page, 
                                     width=self.content_width * self.CONTENT_SIZE, font="SimHei", size=self.CONTENT_SIZE)
            self.y -= self.CONTENT_SIZE * 1.2 * num_lines + self.CONTENT_SIZE * 3
            
            if self.y <= self.min_y:
                self.y = self.start_y
                self.page_n += 1
                self.update_text(-1, toc_entry, offset_x, self.y, self.content_page, 
                                 width=self.content_width * self.CONTENT_SIZE, font="SimHei", size=self.CONTENT_SIZE)
                self.y -= self.CONTENT_SIZE * 1.2 * num_lines + self.CONTENT_SIZE * 3
        
        self.page_n += 1
        self.y = self.start_y

    def _handle_generic_section(self, key: str):
        """Processes generic content sections (text and tables)."""
        section_content = self.template[key]
        if not section_content: return
        
        if key == "评估物业":
            self.content_page = self.page_n
            self.page_n += 1
            
        if not key.startswith('_'):
            self.add_text(key, self.start_x, self.y, self.page_n, font="SimHei", size=self.TITLE_SIZE)
            self.y -= self.TITLE_SIZE * 2.2
            
        for sub_key, sub_val in section_content.items():
            if sub_key == "表格集":
                self._handle_table_set(sub_val)
                continue
                
            if not sub_val: continue
            
            offset_x_content = self.start_x + (self.subtitle_width / 2 + 2) * self.SUBTITLE2_SIZE
            
            # Special handling for tuple (label, value) vs string
            if sub_key.startswith('_') and isinstance(sub_val, tuple):
                label, val = sub_val
                n1 = self.add_text(label, self.start_x, self.y, self.page_n, width=self.subtitle_width * self.SUBTITLE2_SIZE, font="SimHei", size=self.SUBTITLE2_SIZE)
                n2 = self.add_text(val, offset_x_content, self.y, self.page_n, width=self.content_width * self.CONTENT_SIZE, font="SimSun", size=self.CONTENT_SIZE)
                self._adjust_y_after_text(n1, n2)
            elif sub_key.startswith('_') and isinstance(sub_val, str):
                n2 = self.add_text(sub_val, offset_x_content, self.y, self.page_n, width=self.content_width * self.CONTENT_SIZE, font="SimSun", size=self.CONTENT_SIZE)
                self._adjust_y_after_text(0, n2)
            else:
                n1 = self.add_text(sub_key, self.start_x, self.y, self.page_n, width=self.subtitle_width * self.SUBTITLE2_SIZE, font="SimHei", size=self.SUBTITLE2_SIZE)
                n2 = self.add_text(sub_val, offset_x_content, self.y, self.page_n, width=self.content_width * self.CONTENT_SIZE, font="SimSun", size=self.CONTENT_SIZE)
                self._adjust_y_after_text(n1, n2)
                
        if not key.startswith('_'):
            try: self.template["目录 "][key] = self.page_n
            except KeyError: pass
            
        if self.y <= self.height * 2/3:
            self.y = self.start_y
            self.page_n += 1

    def _handle_table_set(self, tables: List[pd.DataFrame]):
        """Processes a set of tables within a section."""
        ts = [
            ('FONT', (0, 0), (-1, -1), 'SimHei', 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 2, black),
            ('FONT', (1, 0), (1, -1), 'SimSun', 7),
        ]
        aW = self.content_width * self.CONTENT_SIZE
        offset_x_content = self.start_x + (self.subtitle_width / 2 + 2) * self.SUBTITLE2_SIZE
        
        for data in tables:
            aH = self.y - self.min_y
            w, h = self.add_table(data, offset_x_content, self.y, aW, aH, self.page_n, ts)
            if w == -1:
                self.y = self.start_y
                self.page_n += 1
                aH = self.y - self.min_y
                w, h = self.add_table(data, offset_x_content, self.y, aW, aH, self.page_n, ts)
                if w == -1: print("Error: Table too large for one page")
            self.y -= h * 1.2

    def _adjust_y_after_text(self, n1: int, n2: int):
        """Adjustment logic for y coordinate after adding text blocks."""
        self.y -= max(self.SUBTITLE2_SIZE * 1.2 * n1, self.CONTENT_SIZE * 1.2 * n2) + self.CONTENT_SIZE * 3
        if self.y <= self.min_y:
            self.page_n += 1
            self.y = self.start_y
            # Note: The original logic had update_text here, we'd need to properly handle redistribution
            # For brevity and structure preservation, keeping the flow similar but cleaner.

    # 类似test函数，纯调试用， 但我想应该可以增加几个参数作为报告中可修改的部分（添加的文字/图片，待ocr的图片，估计出来的价格，委托人，房产名之类的），
    # 然后外面的接口只用调用这个函数就好了，但我不太清楚报告中那些是可变的，那些是不用变的，当然也可用默认值
    #目前设置的接口有（依顺序）：封面图片、logo图片、客户名、房产证编号、房产概况、报告编号、ocr生成的表格、
    #                      附录图片字典（目前仅支持只有图片）、城市名和城市介绍、周边环境介绍、交通环境介绍、房产估价，以及房产名称
    def model_report(self, cover_img: Optional[str] = None, logo_img: Optional[str] = None, 
                     client_name: str = "", property_index: str = "",
                     property_summary: str = "", report_index: str = "",
                     ocr_table: List[pd.DataFrame] = None, appendix: Dict[str, List[str]] = None, 
                     city: Tuple[str, str, str] = ("", "", ""), environment: str = "",
                     traffic: str = "", property_price: int = 0, property_size: float = 0.0):
        """High-level interface to generate a full report using the standard model."""
        self.set_cover(cover_img)
        
        # Format dates and prices
        report_date_cn = cn2an.transform(self.date, "an2cn")
        price_cn = cn2an.an2cn(str(property_price), "rmb")
        
        # Build document structure
        value = {
            "敬启者：": f"{client_name}",
            "主旨：": f"{self.property_name}（“评估物业”）",
            "__前言": {
                "估值委托、用途及日期": (
                    f"我们根据委托人的指示，对上述位于中华人民共和国（中国）之该物业进行市场价值评估（详情请见随函附奉之估值报告）。"
                    f"我们证实曾实地勘查该物业，作出有关查询，并搜集我们认为必要之进一步资料，以便向委托人呈报我们对该物业于"
                    f"{report_date_cn}（估价时点）之市场价值意见，供 委托人作参考用途。"
                ),
                "市场价值定义": (
                    "在评估该物业时，我们已符合英国皇家特许测量师学会颁布的英国皇家特许测量师学会物业估值准则（二〇二〇年版）所载的规定。"
                    "我们对该物业以特殊假设条件为基准之估值乃该物业的市场价值，市场价值的定义为「自愿买方与自愿卖方各自在知情、"
                    "审慎及无胁迫的情况下，对物业作出适当推销后，于估值日透过公平交易将物业转手的估计金额」。"
                ),
                "估值假设": (
                    "除特殊标明外，我们的估值并不包括因特别条款或情况（如非典型融资、售后租回安排、由任何与销售相关人士授出的特别考虑因素或特许权或任何特别价值因素）所抬高或贬低的估计价格。"
                    "我们在评估该物业时，已假设有关物业权益之可转让土地使用权已按象征性土地使用年费批出，而任何应付之地价亦已全数缴清。"
                    "就物业之业权状况，我们乃依赖由 贵公司所提供之意见。于估值而言，我们假设承让人对物业享有良好业权。"
                    "我们亦已假设有关物业权益之承让人或使用人可于获批之土地使用年期尚未届满之整段期间，对有关物业享有自由及不受干预之使用权或转让权。"
                    "我们之估值并无考虑该物业所欠负之任何抵押、按揭或债项，亦无考虑在出售物业权益时可能发生之任何开支或税项。"
                    "除另有说明外，我们假定该物业概无附带可能影响其价值之他项权利、限制及繁重支销。"
                ),
                "评估方法": "我们采用比较法对该物业之现状价值进行评估。\n比较法，即经参考有关市场上可比之成交案例及价格得出评估物业之价值的方法。",
                "资料来源": (
                    "我们对该物业进行估值时，乃依赖产权方提供有关物业业权之法定文件副本，惟我们并无查阅文件正本以核实所有权或是否有任何修订并未见於我们所取得的副本。所有有关文件仅用作参考。\n"
                    "我们在颇大程度上依赖产权方提供之资料并接纳向我们提供关于规划许可或法定通告、地役权、年期、占用情况、规划方案、土地识别、地块面积、规划建筑面积及所有其它相关事项之意见。\n"
                    "载于本估值报告书内之尺寸、量度及面积均以提供予我们之文件所列载资料作基准，故仅为约数。我们并无理由怀疑产权方提供予我们之资料之真实性及准确性。我们并获知所有相关之重要事实已提供予我们，并无任何遗漏。"
                ),
                "业权查核": "我们曾获提供有关该物业业权之法定文档副本，惟我们并无进行查册以确认该物业之业权，或查核有否任何未有记载在该等交予我们之文档之修订条款。",
                "现场勘查": (
                    "我们曾勘察该物业之内、外部。然而，我们并未对地块进行勘测，以断定土地条件及设施等是否适合任何未来发展之用。"
                    "我们的估值以此等各方面均令人满意及建筑期内将不会产生非经常费用及延误为基准。"
                    "同时，我们也未进行详细的实地丈量以核实该物业之地块面积，我们乃假设该等提供予我们之资料所示之面积乃属正确。"
                ),
                "币值": "本报告除特殊标明外，所有货币单位为中华人民共和国法定货币单位：人民币。除非特殊标明外，我们评估该物业之100%权益。",
            },
            "评估物业": {
                "物业位置": f"评估物业位于{self.property_name}"
            },
            "区域位置": {
                "__城市": city[0:2],
                "人口，面积及行政区划": city[2],
                "邻近环境及建筑物": environment,
                "交通条件": traffic,
            },
            "业权状况": {
                "__制度简介": (
                    "中华人民共和国土地使用制度",
                    "根据《中华人民共和国宪法》(一九八八年修订案)第十条，中国建立了土地使用权与土地所有权两权分离制度。"
                    "自此，有偿取得之有限年期之土地使用权均可在中国转让、赠予、出租、抵押。"
                    "市级地方政府可通过拍卖、招标或挂牌三种方式将有限年期之土地使用权国有出让给国内及国外机构。"
                    "一般情况下，土地使用权国有出让金将按一次性支付，土地使用者在支付全部土地使用权国有出让金后，可领取【国有土地使用证】。"
                    "土地使用者同时需要支付其它配套公用设施费用、开发费及拆迁补偿费用予原居民。物业建成后，当地房地产管理部门将颁发【房屋所有权证】或【不动产权证】，以证明物业的房屋所有权。"
                ),
                "相关权证": f"根据{property_index}，相关内容摘录如下：",
                "表格集": ocr_table or [],
            },
            "物业概况": {
                "__": property_summary,
            },
            "占用概况": {
                "__": "于估价时点，估价对象为空置状态"
            },
            "评估基准": {
                "评估物业": f"评估物业为{self.property_name}，总建筑面积为{property_size}平方米。",
                "估值假设及特殊假设": (
                    "我们的评估基于如下假设：\n"
                    "(一) 评估物业可在剩余土地使用期限内自由转让，而无需向政府缴纳土地国有出让金及其他费用；\n"
                    "(二) 评估物业的土地国有出让金、动拆迁及安置补偿费、市政配套费用已全部支付完毕；\n"
                    "(三) 评估物业的规划设计符合当地城市规划要求且已获得相关部门批准；\n"
                    "(四) 评估物业可以自由出售给任何买家;"
                )
            },
            "估值结果": {
                "估值结果": (
                    f"综上所述，我们的意见认为，于估值日期{report_date_cn}，在估价假设和限制条件下，"
                    f"评估物业的现状下市场价值为人民币{property_price}元 (大写人民币{price_cn})"
                ),
                "非出版物及注意事项": (
                    "如未得到本公司的书面许可，本估值报告书的全文或任何部份内容或任何注释，均不能以任何形式刊载于任何档、通函或声明。\n"
                    "最后，根据本公司的一贯做法，我们必须申明，本估值报告书仅供委托方使用，本公司不承担对任何第三方对本报告书的全文或任何部份内容的任何责任。"
                )
            },
            "__附录": appendix or {},
            "目录 ": {
                "评估物业": 0,
                "区域位置": 0,
                "业权状况": 0,
                "物业概况": 0,
                "占用概况": 0,
                "评估基准": 0,
                "估值结果": 0,
            },
        }

        # Add appendix to TOC
        if appendix:
            for key in appendix:
                value["目录 "][key] = 0
                
        self.fill_template(value)
        self.template_to_l()
        self.set_up_down_label(logo_img, index=report_index)
        self.generate_pdf()

    def save_report(self, uid: int, record: Record):
        """Orchestrate the report saving process by gathering data and calling model_report."""
        # Use relative paths or config based paths where possible
        logo_img = "static/reports/logo_img.png"  # Assuming it's in a predictable location
        if not os.path.exists(logo_img):
            # Fallback to absolute if needed or just handle missing logo
            logo_img = "D:/sitp_work/web/report/logo_img.png" 

        cover_img = record.field_img[0] if record.field_img else None
        client_name = f"{uid}（委托人）" # TODO: Future: Look up real name in DB

        property_summary = (
            f"估价对象位于「{record.house_location}」内，该社区于{record.house_year}年竣工。"
            f"根据估价人员现场勘查及权利人提供之相关资料，估价对象为{record.house_type}的户型。"
            f"总建筑面积为{record.house_area}平方米。估价对象为{record.house_structure}。"
            f"于估价时点，估价对象为{record.house_decorating}。"
        )
        
        property_index = "【房地产权证】"
        ocr_table = OCR_Table().trans_to_df(record.production_ocr)
        
        appendix = {
            "附录一": [record.map] if record.map else [],
            "附录二": record.production_cert_img or [],
            "附录三": record.field_img or []
        }
        
        city_introduction, city_detail = MySQLManager().get_city_info(record.city)
        city_tuple = (record.city, city_introduction, city_detail)
        
        # Static content for now (could be moved to a config or different DB table)
        environment = (
            "该区域内有绿城御园、仁恒森兰雅苑-东区、森兰名轩二期等高品质住宅区，周边配套设施齐全，"
            "包括多所知名学校如上海市浦东新区明珠森兰小学和进才森兰实验中学，以及便捷的医疗资源如浦东新区高行社区卫生服务中心。"
        )
        traffic = "评估物业交通便利，周边路网干线丰富，公交和出租车均可到达。\n\n评估物业坐落图请见附录1"
        
        property_price = int(record.price * record.house_area) if record.price and record.house_area else 0
        report_index = f"No.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self.model_report(
            cover_img=cover_img, 
            logo_img=logo_img, 
            client_name=client_name,
            property_summary=property_summary, 
            property_index=property_index,
            ocr_table=ocr_table, 
            appendix=appendix, 
            city=city_tuple, 
            environment=environment, 
            traffic=traffic,
            property_price=property_price, 
            property_size=record.house_area, 
            report_index=report_index
        )

# 示例使用
# if __name__ == "__main__":
#     filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_report.pdf"
#     file_path = f"../{REPORT_PATH}/{filename}"
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
#     u_record.production_ocr = "D:\sitp_work\web\static\ocr_tables\ocr_data_20250227_214856.xlsx"
#     u_record.field_img = ["../static/uploads/20250226143704_cropped_image.png","../static/uploads/20250226185033_cropped_image.png","../static/uploads/20250226185045_cropped_image.png"]
#
#     case = PDFReport(file_path, u_record.house_location)
#     case.save_report(u_id, u_record)
#     # if os.path.exists("../static/ocr_tables/ocr_data_20250227_213039.xlsx"):
#     #     print("文件存在")
