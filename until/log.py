import logging
import os

class CustomFormatter(logging.Formatter):
    """自定义格式化器,显示模块路径的最后两级"""
    def format(self, record):
        # 获取完整路径
        pathname = record.pathname
        # 只有路径中包含 /app 时才显示两级
        if '/app' in pathname:
            parts = pathname.split(os.sep)
            if len(parts) >= 2:
                record.custom_module = f"{parts[-2]}.{record.module}"
            else:
                record.custom_module = record.module
        else:
            record.custom_module = record.module
        return super().format(record)

LOG_FORMAT = CustomFormatter(
    "%(asctime)-15s %(levelname)-3s \033[36m%(custom_module)s\033[0m -- %(message)s"
)

LOGGER = logging.getLogger("MuspiDisplay")
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setFormatter(LOG_FORMAT)
LOGGER.addHandler(CONSOLE_HANDLER)
LOGGER.setLevel(logging.INFO)