"""
QQ问卷星报名助手 - 应用入口

启动方法: python main.py
初始化 ProfileManager, ConfigManager, MainWindow
"""
import sys
import os

# 确保项目根目录在sys.path中（兼容打包后的路径）
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from profiles.manager import ProfileManager
from storage.config_manager import ConfigManager
from ui.main_window import MainWindow
from utils.logger import setup_logger, get_logger


def main():
    """应用主入口"""
    # 确保 Playwright 能找到浏览器（打包后不会在临时目录找）
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        ms_playwright = os.path.join(user_profile, "AppData", "Local", "ms-playwright")
        if os.path.isdir(ms_playwright):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright

    # 初始化日志
    logger = setup_logger()
    logger.info("QQ问卷星报名助手 启动中...")

    # 初始化应用
    app = QApplication(sys.argv)
    app.setApplicationName("QQSurveyAssistant")
    app.setOrganizationName("QQSurveyAssistant")
    app.setStyle("Fusion")

    # 初始化模块
    logger.info("加载配置...")
    config_manager = ConfigManager()

    logger.info("加载预设信息...")
    profile_manager = ProfileManager()

    # 创建主窗口（无需 group_manager）
    logger.info("初始化界面...")
    window = MainWindow(profile_manager, config_manager)
    window.show()

    logger.info("应用启动完成")
    exit_code = app.exec()

    logger.info(f"应用退出 (code={exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
