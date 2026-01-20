# src/agent/graph.py 完整替换后代码 (复制粘贴覆盖即可)
from langgraph.graph import StateGraph, START, END
from src.agent.state import CalcAgentState
from src.agent.nodes import parse_input, llm_decide, execute_tool, llm_summarize
from typing import Dict, Any, Literal

# ✅✅✅ 修改1：路由函数新增判断，ROS2任务直接返回 "end_ros2"
def should_continue(state: CalcAgentState) -> Literal["execute_tool", "llm_summarize", "end_ros2"]:
    last_msg = state["messages"][-1]
    # 优先判断：如果是ROS2任务，直接返回结束标记
    if state.get("ros2_task_triggered", False):
        return "end_ros2"
    # 原有逻辑不变
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "execute_tool"
    return "llm_summarize"

# 1. 创建图对象
workflow = StateGraph(CalcAgentState)

# 2. 添加节点
workflow.add_node("parse_input", parse_input)
workflow.add_node("llm_decide", llm_decide)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("llm_summarize", llm_summarize)

# 3. 固定链路
workflow.add_edge(START, "parse_input")
workflow.add_edge("parse_input", "llm_decide")
workflow.add_edge("execute_tool", "llm_decide")

# ✅✅✅ 修改2：路由映射新增 "end_ros2": END
workflow.add_conditional_edges(
    source="llm_decide",
    path=should_continue,
    path_map={
        "execute_tool": "execute_tool",
        "llm_summarize": "llm_summarize",
        "end_ros2": END  # ROS2任务直达结束，永不走llm_summarize
    }
)

# 原有结束链路保留
workflow.add_edge("llm_summarize", END)

# 编译
graph = workflow.compile()

