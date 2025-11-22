import subprocess
import re

from until.log import LOGGER

CARD = "default"
MIN_DB = -102.0
STEP = "1.0dB"

PCM_CONTROLS = []

def detect_pcm_controls():
    global PCM_CONTROLS
    PCM_CONTROLS = []
    try:
        if CARD == "default":
            out = subprocess.check_output(["amixer", "scontrols"]).decode()
        else:
            out = subprocess.check_output(["amixer", "-c", CARD, "scontrols"]).decode()
        
        # find all controllers, including name and index
        controls = re.findall(r"'([^']*)',(\d+)", out)
        
        # filter out controllers containing PCM
        pcm_controls = [f"{name},{index}" for name, index in controls if "PCM" in name]

        for control in pcm_controls:
            # check if each PCM controller has Playback limit
            if CARD == "default":
                info = subprocess.check_output(["amixer", "sget", control]).decode()
            else:
                info = subprocess.check_output(["amixer", "-c", CARD, "sget", control]).decode()
            
            if "Limits: Playback" in info:
                PCM_CONTROLS.append(control)
                LOGGER.info(f"find PCM controller: {control}")
    
    except Exception as e:
        LOGGER.error("detect PCM controller failed:", e)

def db_to_volume(db):
    # convert dB value (-100 to 0) to 0-100 volume percentage
    return int((db - MIN_DB) * 100 / (0 - MIN_DB+4))

def get_current_db(control):
    try:
        if CARD == "default":
            out = subprocess.check_output(["amixer", "get", control]).decode()
        else:
            out = subprocess.check_output(["amixer", "-c", CARD, "get", control]).decode()

        match = re.search(r'\[(\-?\d+\.\d+)dB\]', out)
        if match:
            db = float(match.group(1))
            volume = db_to_volume(db)
            LOGGER.info(f"[{control}] volume: {volume}% ({db}dB)")
            return db
    except Exception as e:
        LOGGER.error("Failed to get dB:", e)
    return None

def get_volume_percent():
    """
    获取当前音量百分比

    Returns:
        int: 音量百分比 (0-100)，获取失败返回 None
    """
    if not PCM_CONTROLS:
        return None

    # 获取第一个 PCM 控制器的音量
    control = PCM_CONTROLS[0]
    current_db = get_current_db(control)
    if current_db is None:
        return None

    return db_to_volume(current_db)


def adjust_volume(direction):
    """
    调整音量

    Args:
        direction: "up" 或 "down"

    Returns:
        int: 调整后的音量百分比，失败返回 None
    """
    # set volume for all detected PCM controllers
    for control in PCM_CONTROLS:
        current_db = get_current_db(control)
        if current_db is None:
            return None
        if direction == "down" and current_db <= MIN_DB:
            LOGGER.info(f"🔇 Already at minimum {MIN_DB}dB")
            return db_to_volume(current_db)

        delta = STEP + "+" if direction == "up" else STEP + "-"

        try:
            if CARD == "default":
                subprocess.run(["amixer", "set", control, delta], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                subprocess.run(["amixer", "-c", CARD, "set", control, delta], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            LOGGER.error(f"set {control} volume failed:", e)
            return None

    # 返回调整后的音量百分比
    return get_volume_percent()

def toggle_mute():
    """
    切换静音状态

    Returns:
        bool: 当前静音状态 (True=静音, False=取消静音)，失败返回 None
    """
    if not PCM_CONTROLS:
        LOGGER.warning("No PCM controls detected")
        return None

    # 切换所有检测到的 PCM 控制器的静音状态
    mute_status = None
    for control in PCM_CONTROLS:
        try:
            if CARD == "default":
                result = subprocess.run(["amixer", "set", control, "toggle"],
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(["amixer", "-c", CARD, "set", control, "toggle"],
                                      capture_output=True, text=True)

            # 解析静音状态 [on] 或 [off]
            if mute_status is None and result.stdout:
                # 查找 [on] 或 [off] 标记
                if "[off]" in result.stdout:
                    mute_status = True  # off = 静音
                elif "[on]" in result.stdout:
                    mute_status = False  # on = 取消静音

        except Exception as e:
            LOGGER.error(f"Toggle mute for {control} failed: {e}")
            return None

    if mute_status is not None:
        LOGGER.info(f"🔇 Mute: {mute_status}")

    return mute_status

