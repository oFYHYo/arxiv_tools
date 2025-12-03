import os
import sys
import subprocess
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler
import schedule

# ================= 配置区域 =================
# 路径配置
PROJECT_DIR = "/root/software/zawu/arxiv_tools"
PYTHON_PATH = "/root/anaconda3/envs/labagent/bin/python"
ARXIV_FOLDER = "/mnt/e/Software/Obsidian/data_paper/arxiv"
SCRIPT_NAME = "arxiv_update.py"

# 参数配置
CATEGORY = "chem-ph,quant-ph"
AI_PROVIDER = "gemini"

# 日志配置
LOG_FILE = "/root/software/zawu/arxiv_tools/log/arxiv_daily_fetch.log"
RUN_TIME = "10:00"  # 设定每天运行的时间 (24小时制)

# API Keys (如果需要从环境变量加载，保持 os.environ.get，或者直接填入字符串)
# os.environ["GOOGLE_API_KEY"] = "你的KEY" 
# ===========================================

def setup_logger():
    """配置日志，包含自动轮转功能 (类似原脚本的日志大小检查)"""
    logger = logging.getLogger("ArxivFetcher")
    logger.setLevel(logging.INFO)

    # 10MB = 10 * 1024 * 1024 bytes, 保留最近 5 个备份
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 同时也输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

def job():
    """执行核心任务"""
    logger.info("========================================")
    logger.info("Starting ArXiv Daily Fetch Task")
    
    # 1. 计算日期 (对应 shell: date -d '-1 days' +%Y.%m.%d)
    target_date = (datetime.datetime.now() - datetime.timedelta(days=0)).strftime("%Y.%m.%d")
    # target_date_1 = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y.%m.%d")
    # target_date_2 = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y.%m.%d")
    # target_date_3 = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y.%m.%d")
    logger.info(f"Fetching papers for date: {target_date}")

    # 2. 检查项目目录
    if not os.path.exists(PROJECT_DIR):
        logger.error(f"Directory not found: {PROJECT_DIR}")
        return

    # 3. 构建命令
    # 对应: $PYTHON_PATH arxiv_update.py --time ...
    cmd = [
        PYTHON_PATH,
        SCRIPT_NAME,
        "--time", target_date,
        "--categroy", CATEGORY, # 注意：原脚本里拼写是 --categroy，如果那是笔误请修正为 --category
        "--ai_summary",
        "--ai_provider", AI_PROVIDER,
        "--arxiv_folder", ARXIV_FOLDER
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")

    try:
        # 4. 执行命令
        # cwd=PROJECT_DIR 等同于 cd $PROJECT_DIR
        # capture_output=True 将 stdout/stderr 捕获，而不是直接打印
        result = subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False # 不自动抛出异常，手动判断 returncode
        )

        # 记录命令的标准输出
        if result.stdout:
            logger.info(f"[Script Output]:\n{result.stdout}")
        
        # 记录命令的错误输出
        if result.stderr:
            logger.warning(f"[Script Error/Log]:\n{result.stderr}")

        # 5. 检查结果
        if result.returncode == 0:
            logger.info(f"SUCCESS: Papers fetched successfully for {target_date}")
        else:
            logger.error(f"ERROR: Script failed with return code {result.returncode}")

    except Exception as e:
        logger.error(f"EXCEPTION: An error occurred while running the subprocess: {str(e)}")

    logger.info("Task completed.")
    logger.info("========================================")

def main():
    logger.info(f"Scheduler started. Task will run daily at {RUN_TIME}")
    
    # 立即运行一次以测试 (如果不想立即运行，请注释掉下面这行)
    job()

    # 设定定时任务
    schedule.every().day.at(RUN_TIME).do(job)

    while True:
        schedule.run_pending()
        time.sleep(60) # 每分钟检查一次

if __name__ == "__main__":
    main()