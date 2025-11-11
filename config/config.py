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

# --- Trading Strategy Configuration ---
# 信心度阈值配置（根据风险等级）
CONFIDENCE_THRESHOLD_CONSERVATIVE = int(os.getenv("CONFIDENCE_THRESHOLD_CONSERVATIVE", "85"))
CONFIDENCE_THRESHOLD_MODERATE = int(os.getenv("CONFIDENCE_THRESHOLD_MODERATE", "70"))
CONFIDENCE_THRESHOLD_AGGRESSIVE = int(os.getenv("CONFIDENCE_THRESHOLD_AGGRESSIVE", "60"))

# 仓位大小控制（根据风险等级和信心度）
# 基础仓位大小（占可用资金的比例）
BASE_POSITION_SIZE_RATIO_CONSERVATIVE = float(os.getenv("BASE_POSITION_SIZE_RATIO_CONSERVATIVE", "0.02"))  # 2%
BASE_POSITION_SIZE_RATIO_MODERATE = float(os.getenv("BASE_POSITION_SIZE_RATIO_MODERATE", "0.05"))  # 5%
BASE_POSITION_SIZE_RATIO_AGGRESSIVE = float(os.getenv("BASE_POSITION_SIZE_RATIO_AGGRESSIVE", "0.10"))  # 10%

# 最大仓位大小（占可用资金的比例）- 设置更保守的上限，因为货币市场变数大
MAX_POSITION_SIZE_RATIO_CONSERVATIVE = float(os.getenv("MAX_POSITION_SIZE_RATIO_CONSERVATIVE", "0.03"))  # 3%（降低到3%）
MAX_POSITION_SIZE_RATIO_MODERATE = float(os.getenv("MAX_POSITION_SIZE_RATIO_MODERATE", "0.08"))  # 8%（降低到8%）
MAX_POSITION_SIZE_RATIO_AGGRESSIVE = float(os.getenv("MAX_POSITION_SIZE_RATIO_AGGRESSIVE", "0.15"))  # 15%（降低到15%，即使激进策略也不超过15%）

# 绝对仓位上限（无论信心度多高，单笔交易不超过此金额或比例）
# 这是一个硬性上限，防止在极端信心度下过度交易
ABSOLUTE_MAX_POSITION_SIZE_RATIO = float(os.getenv("ABSOLUTE_MAX_POSITION_SIZE_RATIO", "0.10"))  # 10% - 绝对上限，无论任何情况都不超过
ABSOLUTE_MAX_POSITION_SIZE_USD = float(os.getenv("ABSOLUTE_MAX_POSITION_SIZE_USD", "2000.0"))  # 2000 USD - 绝对上限金额

# 最小仓位大小（USD）
MIN_POSITION_SIZE_USD = float(os.getenv("MIN_POSITION_SIZE_USD", "100.0"))

# 信心度对仓位大小的调整系数（信心度越高，可以适当增加仓位）
# 公式：实际仓位 = 基础仓位 * (1 + (confidence - threshold) / 100 * confidence_multiplier)
CONFIDENCE_POSITION_MULTIPLIER_CONSERVATIVE = float(os.getenv("CONFIDENCE_POSITION_MULTIPLIER_CONSERVATIVE", "0.5"))  # 保守策略，信心度影响较小
CONFIDENCE_POSITION_MULTIPLIER_MODERATE = float(os.getenv("CONFIDENCE_POSITION_MULTIPLIER_MODERATE", "0.8"))  # 中等策略
CONFIDENCE_POSITION_MULTIPLIER_AGGRESSIVE = float(os.getenv("CONFIDENCE_POSITION_MULTIPLIER_AGGRESSIVE", "1.2"))  # 激进策略，信心度影响较大

# --- Security and Timing Configuration ---
# 文档中的 "Timing security" 部分提到，服务器会拒绝与服务器时间相差超过60秒的请求。
# 60 * 1000 毫秒 = 60000。将这个值配置在这里，比硬编码在代码中要好。
TIMESTAMP_VALIDITY_WINDOW_MS = 60 * 1000