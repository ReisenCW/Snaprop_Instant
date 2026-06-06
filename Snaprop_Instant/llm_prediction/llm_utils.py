from openai import OpenAI
import os
import logging
from typing import Generator, Union

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

_client = None

def _get_client():
    """获取或创建 DeepSeek OpenAI 兼容客户端"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return _client


def call_llm(model: str, prompt: str, system_prompt: str = None, search: bool = False, stream: bool = False, max_tokens: int = None) -> Union[str, Generator[str, None, None]]:
    """
    封装 LLM 调用（DeepSeek OpenAI 兼容 API），支持 System Role、流式输出和字数限制。

    Args:
        model: 模型名称 (如 "deepseek-v4-pro")
        prompt: 用户提示词内容
        system_prompt: 系统人格定义
        search: 是否启用联网搜索（DeepSeek 暂不支持，忽略）
        stream: 是否启用流式输出
        max_tokens: 最大生成 token 数
    """
    client = _get_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    call_params = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if max_tokens:
        call_params["max_tokens"] = max_tokens

    try:
        if not stream:
            response = client.chat.completions.create(**call_params)
            return response.choices[0].message.content
        else:
            def stream_generator():
                response = client.chat.completions.create(**call_params)
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            return stream_generator()

    except Exception as e:
        logging.error(f"Exception during LLM call: {e}")
        return ""
