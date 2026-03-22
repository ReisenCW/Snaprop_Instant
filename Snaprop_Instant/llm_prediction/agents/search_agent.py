from llm_prediction.agents.base_agent import BaseAgent
from llm_prediction.prompts import PROMPTS, SYSTEM_PROMPTS
import time
from llm_prediction.llm_utils import call_llm

class SearchAgent(BaseAgent):
    def __init__(self, config, model=None):
        super().__init__(config, model=model or config.FAST_MODEL)
    
    async def search(self, region: str, time_range: str) -> str:
        use_prompt = PROMPTS["search_related_info"].format(
            region=region, 
            time_range=time_range
        )

        if getattr(self.config, 'DEBUG', False):
            print(f"[SearchAgent] 正在执行联网搜索...")
        
        search_start = time.time()
        raw_info = self._call(use_prompt, system_prompt=SYSTEM_PROMPTS["search_expert"], search=True)
        search_duration = time.time() - search_start

        if getattr(self.config, 'DEBUG', False):
            print(f"[SearchAgent] 联网搜索完成，耗时: {search_duration:.2f}s")
        
        # 不再自动精简（已在 prompt 中要求输出精简）
        return raw_info

    async def get_actual(self, region: str, time_range: str) -> str:
        prompt = PROMPTS["get_actual_trend"].format(
            region=region, 
            time_range=time_range
        )
        return self._call(prompt, system_prompt=SYSTEM_PROMPTS["search_expert"], search=True)
