# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# --- API Endpoint Configuration ---
# 支持通过环境变量配置API URL，默认使用mock API（用于测试）
# 生产环境请设置 ROOSTOO_API_URL 为真实API地址
# 默认使用 mock API: https://mock-api.roostoo.com
# 例如：ROOSTOO_API_URL=https://api.roostoo.com (真实API)
BASE_URL = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")

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