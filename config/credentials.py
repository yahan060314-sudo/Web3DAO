# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# 获取当前文件所在的目录
# 这能确保无论从哪里运行主程序，都能正确找到.env文件
# .env文件应该在项目根目录，即 trading_bot/ 的上一级
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_root, '.env')

# 从.env文件加载环境变量
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("Successfully loaded environment variables from .env file.")
else:
    print("Warning: .env file not found. Will try to read from system environment variables.")
    # --- Roostoo API Credentials ---
    # 直接从操作系统的环境变量中读取 API Key 和 Secret Key。
    # 这是最安全、最标准的服务器端实践。
    API_KEY = os.getenv('ROOSTOO_API_KEY')
    SECRET_KEY = os.getenv('ROOSTOO_SECRET_KEY')

# --- 关键安全检查 ---
# 检查密钥是否成功加载。如果没有设置环境变量，os.getenv() 会返回 None。
# 如果密钥不存在，程序将打印错误信息并退出，以防止后续操作失败。
if not API_KEY or not SECRET_KEY:
    raise ValueError(
        "Roostoo API Key or Secret Key not set!\n"
        "Please ensure the .env file exists in the project root directory and contains 'ROOSTOO_API_KEY' and 'ROOSTOO_SECRET_KEY'."
    )