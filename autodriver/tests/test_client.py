import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from langchain_core.messages import HumanMessage
from src.agent.graph import graph

# # 测试输入：支持【数学计算】+【知识库查询】+【ROS2 node.py生成】 三能力全覆盖
# async def test_calc_rag_agent():
#     # ========== 测试1：原有计算能力 (不变，你的核心功能) ==========
#     print("===== 测试1：数学计算 - Add 3 and 4 =====")
#     inputs_calc = {
#         "messages": [HumanMessage(content="Add 3 and 4")],
#         "parsed_input": None,
#         "llm_calls": 0,
#         "ros2_task_triggered": False,
#         "ros2_topic_list": [],
#         "ros2_parsed_config": {},
#         "generated_node_py": ""
#     }
#     async for event in graph.astream(inputs_calc):
#         for node_name, output in event.items():
#             print(f"✅ {node_name}")
#             print(f"内容: {output}\n")
    
#     # ========== 测试2：新增RAG知识库能力 (机器人指令查询) ==========
#     print("===== 测试2：知识库查询 - 机器人前进指令是什么？ =====")
#     inputs_rag = {
#         "messages": [HumanMessage(content="机器人前进指令是什么？")],
#         "parsed_input": None,
#         "llm_calls": 0,
#         "ros2_task_triggered": False,
#         "ros2_topic_list": [],
#         "ros2_parsed_config": {},
#         "generated_node_py": ""
#     }
#     async for event in graph.astream(inputs_rag):
#         for node_name, output in event.items():
#             print(f"✅ {node_name}")
#             print(f"内容: {output}\n")

#     # ========== ✅ 测试3：新增 ROS2 机器人node.py 自动生成测试 (核心新增) ==========
#     print("===== 测试3：ROS2生成 - 根据我的机器人，生成适配的node.py文件 =====")
#     inputs_ros2 = {
#         "messages": [HumanMessage(content="根据我目前的机器人情况，用ros2开发模式输出适合本机器人的node.py")],
#         "parsed_input": None,
#         "llm_calls": 0,
#         "ros2_task_triggered": False,
#         "ros2_topic_list": [],
#         "ros2_parsed_config": {},
#         "generated_node_py": ""
#     }
#     async for event in graph.astream(inputs_ros2):
#         for node_name, output in event.items():
#             print(f"✅ {node_name}")
#             print(f"内容: {output}\n")

# ========== 单独测试ROS2生成 (推荐，方便调试，可选运行) ==========
async def test_ros2_only():
    """单独测试ROS2 node.py生成功能"""
    print("===== 单独测试：ROS2 node.py 生成 独立测试 =====")
    inputs_ros2_only = {
        "messages": [HumanMessage(content="生成我的ROS2机器人对应的node.py驱动代码")],
        "llm_calls": 0
    }
    
    # 执行流程并捕获结果
    result = None
    async for event in graph.astream(inputs_ros2_only):
        # 打印流程节点，确认是否走到end_ros2
        for node, data in event.items():
            print(f"✅ {node}")
            if node == "llm_decide":
                result = data  # 保存ROS2生成的结果
    
    # 输出最终结果
    if result and result.get("generated_node_py"):
        print("✅ 最终生成结果:")
        print(result["generated_node_py"])  # 打印前500字符
    else:
        print("❌ 未生成ROS2代码")

if __name__ == "__main__":
    # # 运行全部测试：计算+知识库+ROS2
    # asyncio.run(test_calc_rag_agent())
    
    # 如果只想单独测试ROS2生成，注释上面一行，打开下面一行
    asyncio.run(test_ros2_only())