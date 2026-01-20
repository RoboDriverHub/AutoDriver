from langchain.tools import tool
import subprocess
import re
import json
# ✅ 补齐所有缺失的类型注解导入 根治NameError
from typing import List, Dict, Any, Optional

# 加法工具 - 带规范文档注释，通过LangGraph严格校验
@tool
def add(a: int, b: int) -> int:
    """Add two integers.
    Args:
        a: First integer to add
        b: Second integer to add
    Returns:
        The sum of a and b
    """
    return a + b

# 乘法工具
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers.
    Args:
        a: First integer to multiply
        b: Second integer to multiply
    Returns:
        The product of a and b
    """
    return a * b

# 除法工具
@tool
def divide(a: int, b: int) -> float:
    """Divide two numbers.
    Args:
        a: Dividend (number to be divided)
        b: Divisor (number to divide by)
    Returns:
        The quotient of a divided by b
    """
    return a / b

# ========== 知识库查询工具 ==========
@tool
def knowledge_query(query: str) -> str:
    """必须调用此工具回答所有知识库相关问题，包括：机器人指令、机器人故障码、计算器支持的运算、机器人型号等。
    Args:
        query: 用户的中文自然语言问题，比如：机器人前进指令是什么？计算器支持哪些运算？
    """
    from src.agent.rag import retrieve_context
    context = retrieve_context(query)
    return context

# ========== ROS2 自动化生成 node.py 核心工具 ==========
def _exec_ros2_cmd(cmd: str) -> str:
    """私有函数：执行ROS2系统命令 + 异常捕获，稳定可靠"""
    try:
        result = subprocess.run(
            cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8
        )
        if result.returncode != 0:
            return f"CMD_ERROR: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "CMD_ERROR: ROS2命令执行超时，检查ROS2环境/机器人连接"
    except Exception as e:
        return f"CMD_ERROR: {str(e)}"

# ========== tools.py 中 ros2_get_topic_list 上方新增缓存变量
# 新增缓存变量，提速
topic_list_cache = None

@tool
def ros2_get_topic_list() -> List[str]:
    """【ROS2专属】获取当前机器人所有ROS2话题列表，执行命令: ros2 topic list"""
    global topic_list_cache
    if topic_list_cache is not None:
        print("✅ 使用缓存的ROS2话题列表")
        return topic_list_cache
    print("✅ 执行系统命令: ros2 topic list")
    cmd_res = _exec_ros2_cmd("ros2 topic list")
    if cmd_res.startswith("CMD_ERROR"):
        print(f"❌ ROS2命令执行失败: {cmd_res}")
        return [cmd_res]
    topic_list_cache = [topic.strip() for topic in cmd_res.split("\n") if topic.strip()]
    return topic_list_cache

@tool
def ros2_parse_topic_to_config(topic_list: List[str]) -> Dict[str, Any]:
    """【ROS2专属核心】根据ROS2话题列表自动分类解析，生成适配GALAXEALITE模板的配置字典"""
    robot_config = {
        "publish_topics": {"left_arm": "", "right_arm": "", "left_gripper": "", "right_gripper": "", "torso": ""},
        "follow_feedback_topics": {"left_arm": "", "right_arm": "", "left_gripper": "", "right_gripper": "", "torso": ""},
        "main_cmd_topics": {"joint_left": "", "joint_right": "", "joint_torso": "", "pose_left": "", "pose_right": "", "pose_torso": "", "gripper_left": "", "gripper_right": ""},
        "camera_topics": {"top_left": "", "top_right": "", "wrist_left": "", "wrist_right": ""},
        "camera_size": {"top_left": (1280,720), "top_right": (1280,720), "wrist_left": (640,360), "wrist_right": (640,360)},
        "joint_dim": {"left_arm":6, "right_arm":6, "gripper":1, "torso":3, "torso_cut":-1},
        "control_hz":30
    }
    pub_rules = [(r"target_joint_state_arm_left","publish_topics.left_arm"),(r"target_joint_state_arm_right","publish_topics.right_arm"),(r"target_position_gripper_left","publish_topics.left_gripper"),(r"target_position_gripper_right","publish_topics.right_gripper"),(r"target_joint_state_torso","publish_topics.torso")]
    follow_rules = [(r"feedback_arm_left","follow_feedback_topics.left_arm"),(r"feedback_arm_right","follow_feedback_topics.right_arm"),(r"feedback_gripper_left","follow_feedback_topics.left_gripper"),(r"feedback_gripper_right","follow_feedback_topics.right_gripper"),(r"feedback_torso","follow_feedback_topics.torso")]
    main_rules = [(r"target_joint_state_arm_left","main_cmd_topics.joint_left"),(r"target_joint_state_arm_right","main_cmd_topics.joint_right"),(r"target_joint_state_torso","main_cmd_topics.joint_torso"),(r"target_pose_arm_left","main_cmd_topics.pose_left"),(r"target_pose_arm_right","main_cmd_topics.pose_right"),(r"target_pose_torso","main_cmd_topics.pose_torso"),(r"target_position_gripper_left","main_cmd_topics.gripper_left"),(r"target_position_gripper_right","main_cmd_topics.gripper_right")]
    camera_rules = [(r"camera_head/left.*compressed","camera_topics.top_left"),(r"camera_head/right.*compressed","camera_topics.top_right"),(r"camera_wrist_left.*compressed","camera_topics.wrist_left"),(r"camera_wrist_right.*compressed","camera_topics.wrist_right")]
    all_rules = pub_rules + follow_rules + main_rules + camera_rules
    for pattern, conf_key in all_rules:
        for topic in topic_list:
            if re.search(pattern, topic):
                k1, k2 = conf_key.split(".")
                robot_config[k1][k2] = topic
                break
    return robot_config

@tool
def ros2_render_node_template(robot_config: Dict[str, Any]) -> str:
    """【ROS2专属最终】读取模板文件生成完整node.py代码"""
    template_path = "data/ros2/template/galaxea/node_template.py"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        config_str = f"ROBOT_CONFIG = {json.dumps(robot_config, indent=4, ensure_ascii=False)}"
        final_code = re.sub(r"ROBOT_CONFIG = \{[\s\S]*?\}", config_str, template_content, count=1)
        return final_code
    except FileNotFoundError:
        return f"文件不存在错误: {template_path}，请确认模板文件路径正确！"
    except Exception as e:
        return f"模板渲染错误: {str(e)}"

# ========== 工具列表 ==========
tools = [add, multiply, divide, knowledge_query, ros2_get_topic_list, ros2_parse_topic_to_config, ros2_render_node_template]
tools_by_name = {t.name: t for t in tools}
print(f"✅ 已加载工具列表: {list(tools_by_name.keys())}")