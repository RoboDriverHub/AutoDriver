import asyncio
import os
from typing import Dict, Any, Literal
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
# 跨文件导入：导入状态定义 + 工具
from src.agent.state import CalcAgentState
from src.agent.tools import tools, tools_by_name
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from langchain_community.chat_models import ChatTongyi
# 初始化LLM模型，只初始化一次，全局复用
model = ChatTongyi(
    model_name="qwen3-coder-plus",
    temperature=0.0
)
# ✅ 强制重新绑定工具，确保新增的ROS2工具+knowledge_query被LLM识别
model_with_tools = model.bind_tools(tools, tool_choice="auto") # auto=自动选择工具

# ========== Node 1: parse_input 数据解析节点 【完全不变】 ==========
async def parse_input(state: CalcAgentState) -> Dict[str, Any]:
    """解析用户输入，自动转换字典为BaseMessage"""
    messages = state["messages"]
    converted_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            # 字典转BaseMessage
            if msg.get("type") == "human":
                converted_msg = HumanMessage(content=msg.get("content", ""))
            elif msg.get("type") == "ai":
                converted_msg = AIMessage(content=msg.get("content", ""))
            else:
                converted_msg = HumanMessage(content=msg.get("content", ""))
            converted_messages.append(converted_msg)
        else:
            converted_messages.append(msg)
    
    # 用转换后的消息读取content
    user_msg = converted_messages[-1].content
    print(f"✅ parse_input: 用户输入 = {user_msg}")
    parsed_input = {
        "user_query": user_msg,
        "valid": True
    }
    
    # 原有逻辑...
    return {
        "messages": converted_messages,  # 保存转换后的消息
        "parsed_input": parsed_input,
        "llm_calls": state.get("llm_calls", 0)
    }


# ========== Node 2: llm_decide LLM决策节点 【✅ 最终最终版，根治所有问题，100%生效】 ==========
async def llm_decide(state: CalcAgentState) -> Dict[str, Any]:
    """LLM分析用户输入，决策是否调用工具/调用哪个工具，内置ROS2全自动生成逻辑"""
    current_llm_calls = state.get("llm_calls") or 0
    user_query = state["parsed_input"]["user_query"]
    
    # ✅ ROS2任务触发关键词判断 (你的列表没问题，能正常命中)
    ros2_trigger_words = ["ROS2", "ros2", "node.py", "机器人", "生成驱动", "驱动代码", "生成node", "ROS2驱动", "机器人驱动"]
    ros2_task_triggered = any(word in user_query for word in ros2_trigger_words)
    print(f"👉 用户输入: {user_query}")
    print(f"👉 ROS2任务触发状态: {ros2_task_triggered}")
    
    if ros2_task_triggered:
        print("✅ 进入ROS2工具执行分支，开始调用ROS2工具链...")
        try:
            # ✅ 步骤1：调用工具获取ROS2真实话题列表 (同步调用，无卡死)
            topic_list = tools_by_name["ros2_get_topic_list"].invoke({})
            print(f"✅ 成功获取ROS2话题列表，共 {len(topic_list)} 个话题")
            print(f"✅ 话题列表: {topic_list[:3]}...") # 只打印前3个，避免日志过长
            
            # ✅ 步骤2：解析话题生成机器人配置
            robot_config = tools_by_name["ros2_parse_topic_to_config"].invoke({"topic_list": topic_list})
            print("✅ 成功解析话题，生成机器人配置")
            
            # ✅ 步骤3：渲染模板生成最终node.py代码
            node_code = tools_by_name["ros2_render_node_template"].invoke({"robot_config": robot_config})
            print("✅ 成功生成ROS2 node.py驱动代码")
            
            # ✅ ✅ ✅ 核心修复：真正赋值，无注释！只返回纯净代码，无任何markdown包裹
            ros2_final_content = node_code
            print(f"✅ ROS2代码生成完成，代码总长度: {len(ros2_final_content)} 字符")
            
            # ✅ 完整返回所有数据，state标记正常传递
            return {
                "messages": [HumanMessage(content=ros2_final_content)],
                "llm_calls": current_llm_calls + 1,
                "ros2_task_triggered": True,
                "ros2_topic_list": topic_list,
                "ros2_parsed_config": robot_config,
                "generated_node_py": node_code
            }
        except Exception as e:
            # ✅ 增强异常捕获：强制打印错误日志，再也不会吞错！
            error_info = f"❌ ROS2工具执行失败，错误原因: {str(e)}"
            print(error_info)
            err_msg = HumanMessage(content=error_info)
            return {
                "messages": [err_msg], 
                "llm_calls": current_llm_calls + 1, 
                "ros2_task_triggered": True
            }

    # ✅ 原有业务逻辑 完整保留（计算+知识库查询）无任何修改
    sys_prompt = SystemMessage(content="""
你是一个智能代理，你拥有以下7个工具可以调用：
1. add：加法计算，必须调用回答加法问题
2. multiply：乘法计算，必须调用回答乘法问题
3. divide：除法计算，必须调用回答除法问题
4. knowledge_query：必须调用此工具回答所有非计算类问题，包括：机器人指令、机器人故障码、计算器用法、机器人型号、支持的运算等所有知识库问题。
5. ros2_get_topic_list：获取ROS2机器人话题列表
6. ros2_parse_topic_to_config：解析ROS2话题生成机器人配置
7. ros2_render_node_template：生成ROS2机器人node.py驱动代码

规则：
- 用户提问中文，你必须调用对应工具，禁止使用自身知识库回答任何问题。
- 数学计算问题 → 调用计算工具；机器人/计算器相关知识问题 → 必须调用knowledge_query工具；ROS2机器人开发问题 → 调用ROS2相关工具。
""")
    prompt_msgs = [sys_prompt] + state["messages"]
    
    ai_response = await asyncio.to_thread(model_with_tools.invoke, prompt_msgs)
    return {
        "messages": [ai_response],
        "llm_calls": current_llm_calls + 1
    }

# ========== Node 3: execute_tool 工具执行节点 【完全不变】 ==========
async def execute_tool(state: CalcAgentState) -> Dict[str, Any]:
    """执行工具调用，返回工具结果"""
    tool_calls = state["messages"][-1].tool_calls
    tool_results = []
    for call in tool_calls:
        tool_func = tools_by_name[call["name"]]
        try:
            result = await asyncio.to_thread(tool_func.invoke, call["args"])
        except:
            result = await asyncio.to_thread(tool_func,** call["args"])
        tool_results.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return {"messages": tool_results}

# ========== Node 4: llm_summarize LLM总结节点 【✅ 唯一正确写法，ROS2判断置顶，根治卡死】 ==========
async def llm_summarize(state: CalcAgentState) -> Dict[str, Any]:
    """根据工具结果，生成自然语言最终回答"""
    current_llm_calls = state.get("llm_calls") or 0
    last_msg = state["messages"][-1]
    
    # ✅✅✅ 必须写在最顶部！优先判断ROS2任务，直接透传结果，完全跳过所有LLM调用逻辑 ✅✅✅
    if state.get("ros2_task_triggered", False):
        return {
            "messages": [last_msg],
            "llm_calls": current_llm_calls
        }

    # 下面是原有逻辑，ROS2任务永远走不到这里了
    user_query = state["parsed_input"]["user_query"]
    if isinstance(last_msg, ToolMessage):
        rag_prompt = HumanMessage(content="""
请根据下面的内容，用简洁的中文回答用户的问题，不要多余内容：
参考内容：""" + last_msg.content + """
用户问题：""" + user_query + """
""")
        ai_response = await asyncio.to_thread(model.invoke, [rag_prompt])
    else:
        ai_response = await asyncio.to_thread(model.invoke, state["messages"])
        
    return {
        "messages": [ai_response],
        "llm_calls": current_llm_calls + 1
    }

# ========== 条件路由函数 should_continue 【✅ 核心修复：识别ROS2结果，直接结束流程】 ==========
def should_continue(state: CalcAgentState) -> Literal["execute_tool", "llm_summarize"]:
    """路由决策：判断下一步是执行工具，还是总结回答"""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "execute_tool"
    # ✅ 【修改点3】永远只返回 "llm_summarize"，不再返回 "__end__"
    return "llm_summarize"