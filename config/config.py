# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# --- API Endpoint Configuration ---
# 从环境变量读取API URL（必须配置）
ROOSTOO_API_URL = os.getenv("ROOSTOO_API_URL")
if not ROOSTOO_API_URL:
    raise ValueError(
        "ROOSTOO_API_URL未在.env文件中设置。\n"
        "请在.env文件中设置: ROOSTOO_API_URL=https://mock-api.roostoo.com"
    )

BASE_URL = ROOSTOO_API_URL

# --- Request Configuration ---
# 根据文档，所有POST请求都需要这个Header。将其定义为常量可以避免重复书写和拼写错误。
POST_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

# 这是一个很好的实践：为所有网络请求设置一个默认的超时时间（单位：秒）。
# 这可以防止您的程序在网络状况不佳时无限期地等待。
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10

TRADE_INTERVAL_SECONDS = 61

# --- Security and Timing Configuration ---
# 文档中的 "Timing security" 部分提到，服务器会拒绝与服务器时间相差超过60秒的请求。
# 60 * 1000 毫秒 = 60000。将这个值配置在这里，比硬编码在代码中要好。
TIMESTAMP_VALIDITY_WINDOW_MS = 60 * 1000