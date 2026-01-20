# # src/agent/rag.py
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

# ========== 1. 初始化【纯CPU/无依赖】嵌入模型 (无任何CUDA相关，秒加载) ==========
embeddings = FakeEmbeddings(size=384)

# ========== 2. 你的知识库内容（可直接追加机器人指令/计算器规则） ==========
knowledge_base = [
    # 计算器相关知识库
    "本计算器支持加法add、减法subtract、乘法multiply、除法divide四种运算",
    "加法函数：add(a,b)，参数a和b是整数，返回两数之和",
    "乘法函数：multiply(a,b)，参数a和b是整数，返回两数之积",
    "除法函数：divide(a,b)，参数a是被除数，b是除数，返回浮点型商，除数不能为0",
    # 机器人指令知识库（后续扩展直接加这里）
    "机器人前进指令：move_forward(distance)，distance为前进距离(cm)",
    "机器人左转指令：turn_left(angle)，angle为左转角度(°)",
    "机器人紧急停止指令：stop_robot()，无参数，立即停止所有动作",
    "机器人支持的型号：A1、B2、C3，均兼容基础运动指令",
    "机器人故障码E01：电机卡死，解决方案：重启机器人并清除前方障碍物"
]

# ========== 3. 文本分片 + 初始化向量数据库 ==========
text_splitter = CharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20,
    separator="\n"
)
docs = [Document(page_content=text) for text in knowledge_base]
split_docs = text_splitter.split_documents(docs)
vector_db = FAISS.from_documents(split_docs, embeddings)

# src/agent/rag.py 只改这个函数，其他不变
def retrieve_context(question: str, top_k: int = 2) -> str: # top_k=2 更精准
    retriever = vector_db.as_retriever(k=top_k)
    relevant_docs = retriever.invoke(question)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    return context # 直接返回纯文本，无多余拼接