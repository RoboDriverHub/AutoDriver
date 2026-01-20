# src/agent/state.py
from typing import TypedDict, Union, List, Annotated, Dict, Any
from langchain_core.messages import BaseMessage
import operator

# 完整的计算Agent状态定义，严格遵循官方设计原则：只存原始数据、结构化、扁平化
class CalcAgentState(TypedDict):
    # 消息列表：用户/AI/工具消息，operator.add 实现消息列表的自动追加（核心特性）
    messages: Annotated[List[BaseMessage], operator.add]
    # 解析后的用户输入（可选，工程化推荐，便于后续扩展）
    parsed_input: Union[dict, None]
    # LLM调用次数统计，双重兜底防None
    llm_calls: int

     # ========== ✅ 新增：ROS2自动化生成node.py 专属字段 (仅追加，不修改任何原有内容) ==========
    ros2_topic_list: List[str]          # 存储ros2 topic list执行结果的话题列表
    ros2_parsed_config: Dict[str, Any]  # 解析后的机器人完整配置字典(填充模板核心数据)
    generated_node_py: str              # 最终渲染好的node.py完整代码文本
    ros2_triggered: bool                # ROS2功能触发标记：True=生成代码，False=走原有逻辑