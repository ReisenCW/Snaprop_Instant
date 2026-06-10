"""
本模块包含 DeepSeek 管理类（使用 OpenAI 兼容 API）
"""
import json
from openai import OpenAI
from llm.prompt import Prompt
from config.qianwen_config import model_name, model_api_key

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class QianwenManager():
    """
    LLM 管理类（通过 OpenAI 兼容 API 调用 DeepSeek）
    """

    def __init__(self):
        self._model = model_name
        self._api_key = model_api_key
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=DEEPSEEK_BASE_URL,
        )

    def disconnect_llm(self):
        return

    def interact_qwen(self, prompt: str, request: str):
        messages = [{'role': 'system', 'content': prompt}]
        if request:
            messages.append({'role': 'user', 'content': request})

        reply = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return reply.choices[0].message.content

    def classify_message(self, message: str):
        return self.interact_qwen(prompt=Prompt.PROMPT_CLASSIFY_MESSAGE, request=message)

    def respond_null(self, message: str):
        return self.interact_qwen(prompt=Prompt.PROMPT_RESPOND_NULL, request=message)

    def respond_info(self, message: str, inputs: list[str]):
        prompt = Prompt.PROMPT_RESPOND_INFO.format(lists=",".join(inputs))
        return self.interact_qwen(prompt=prompt, request=message)

    def respond_value(self, missing_values: list[str]):
        prompt = Prompt.PROMPT_RESPOND_VALUE.format(lists=",".join(missing_values))
        return self.interact_qwen(prompt=prompt, request="")

    def respond_table(self, message: str, inputs: list[str]):
        prompt = Prompt.PROMPT_RESPOND_TABLE.format(lists=",".join(inputs))
        return self.interact_qwen(prompt=prompt, request=message)

    def get_near_loc(self, message: str):
        return self.interact_qwen(prompt=Prompt.PROMPT_NEAR_LOC, request=message)

    def get_environment(self, near_places: list[str], hospital: list[str], school: list[str]):
        prompt = Prompt.PROMPT_NEAR_LOC_SHORT.format(near_places=",".join(near_places), hospital=",".join(hospital),
                                                     school=",".join(school))
        return self.interact_qwen(prompt=prompt, request="")

    def generate_listing_description(self, property_info: dict, style: str = "professional"):
        """使用 LLM 生成房源挂牌描述

        Args:
            property_info: 房源信息字典，包含 address, area, house_type, floor, fitment,
                          direction, year, green_rate 等字段
            style: 描述风格 - "professional"(专业客观), "warm"(生活温馨), "investment"(投资分析)

        Returns:
            生成的描述文本
        """
        prompt = Prompt.PROMPT_LISTING_DESCRIPTION.get(
            style, Prompt.PROMPT_LISTING_DESCRIPTION["professional"]
        )
        # 构建待描述信息
        info_text = (
            f"小区/地址：{property_info.get('address', '未知')}\n"
            f"面积：{property_info.get('area', '未知')}平方米\n"
            f"户型：{property_info.get('house_type', '未知')}\n"
            f"楼层：{property_info.get('floor', '未知')}\n"
            f"装修：{property_info.get('fitment', '未知')}\n"
            f"朝向：{property_info.get('direction', '未知')}\n"
            f"建成年份：{property_info.get('year', '未知')}\n"
            f"绿化率：{property_info.get('green_rate', '未知')}\n"
            f"结构：{property_info.get('structure', '未知')}"
        )
        result = self.interact_qwen(prompt=prompt, request=info_text)
        return result.strip() if result else ""

    def batch_extract_fields(self, ocr_text: str):
        """使用 LLM 从 OCR 文本中提取所有房产字段

        Args:
            ocr_text: OCR 识别的原始文本内容

        Returns:
            dict: 提取的字段字典，如果解析失败返回空字典
        """
        result = self.interact_qwen(
            prompt=Prompt.PROMPT_BATCH_EXTRACT,
            request=ocr_text
        )
        if not result:
            return {}
        try:
            # 清理可能的 markdown 代码块标记
            text = result.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                text = "\n".join(lines)
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON 对象
            import re
            match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}

    def resolve_district(self, address: str):
        """使用 LLM 判断上海地址所属行政区"""
        prompt = (
            "你是一个上海地理专家。请判断以下地址属于哪个上海行政区。"
            "只回答区名，不要任何解释。可选区：黄浦、静安、徐汇、长宁、浦东、虹口、杨浦、普陀、闵行、宝山、嘉定、松江、青浦、奉贤、金山、崇明。"
            "如果无法确定，回答\"全市\"。"
        )
        result = self.interact_qwen(prompt=prompt, request=address)
        return result.strip() if result else "全市"
