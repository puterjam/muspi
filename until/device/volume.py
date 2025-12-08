import subprocess
import re

from until.log import LOGGER

CARD = "default"
MIN_DB = -102.0
STEP = "1.0dB"

PCM_CONTROLS = []
DEVICE_TYPE = None  # 'pulse' or 'alsa'

def detect_pcm_controls():
    global PCM_CONTROLS, DEVICE_TYPE
    PCM_CONTROLS = []
    DEVICE_TYPE = None

    try:
        # Try PulseAudio first (for Pi 5)
        try:
            out = subprocess.check_output(["amixer", "-D", "pulse", "scontrols"]).decode()
            DEVICE_TYPE = "pulse"
            LOGGER.info("Detected PulseAudio")
        except subprocess.CalledProcessError:
            # Fallback to ALSA (for Pi 3B+)
            if CARD == "default":
                out = subprocess.check_output(["amixer", "scontrols"]).decode()
            else:
                out = subprocess.check_output(["amixer", "-c", CARD, "scontrols"]).decode()
            DEVICE_TYPE = "alsa"
            LOGGER.info("Detected ALSA")

        # find all controllers, including name and index
        controls = re.findall(r"'([^']*)',(\d+)", out)

        # filter controllers based on device type
        if DEVICE_TYPE == "pulse":
            # For PulseAudio (Pi 5), use Master control
            pcm_controls = [f"{name},{index}" for name, index in controls if name == "Master"]
        else:
            # For ALSA (Pi 3B+), use PCM controls
            pcm_controls = [f"{name},{index}" for name, index in controls if "PCM" in name]

        for control in pcm_controls:
            # check if each controller has Playback limit
            if DEVICE_TYPE == "pulse":
                info = subprocess.check_output(["amixer", "-D", "pulse", "sget", control]).decode()
            elif CARD == "default":
                info = subprocess.check_output(["amixer", "sget", control]).decode()
            else:
                info = subprocess.check_output(["amixer", "-c", CARD, "sget", control]).decode()

            if "Limits: Playback" in info:
                PCM_CONTROLS.append(control)
                LOGGER.info(f"find controller: {control}")
    
    except Exception as e:
        LOGGER.error("detect PCM controller failed:", e)

def db_to_volume(db):
    # convert dB value (-100 to 0) to 0-100 volume percentage
    return int((db - MIN_DB) * 100 / (0 - MIN_DB+4))

def get_current_volume(control):
    """
    获取当前音量

    Returns:
        tuple: (value, is_db)
               - value: dB值(ALSA) 或 百分比(PulseAudio)
               - is_db: True表示返回的是dB值，False表示返回的是百分比
    """
    try:
        if DEVICE_TYPE == "pulse":
            out = subprocess.check_output(["amixer", "-D", "pulse", "get", control]).decode()
        elif CARD == "default":
            out = subprocess.check_output(["amixer", "get", control]).decode()
        else:
            out = subprocess.check_output(["amixer", "-c", CARD, "get", control]).decode()

        # Try to match dB format first (ALSA)
        match = re.search(r'\[(\-?\d+\.\d+)dB\]', out)
        if match:
            db = float(match.group(1))
            volume = db_to_volume(db)
            LOGGER.info(f"[{control}] volume: {volume}% ({db}dB)")
            return (db, True)

        # If no dB format, try percentage format (PulseAudio)
        match = re.search(r'\[(\d+)%\]', out)
        if match:
            percent = int(match.group(1))
            LOGGER.info(f"[{control}] volume: {percent}%")
            return (percent, False)

    except Exception as e:
        LOGGER.error("Failed to get volume:", e)
    return None

def get_volume_percent():
    """
    获取当前音量百分比

    Returns:
        int: 音量百分比 (0-100)，获取失败返回 None
    """
    if not PCM_CONTROLS:
        return None

    # 获取第一个控制器的音量
    control = PCM_CONTROLS[0]
    result = get_current_volume(control)
    if result is None:
        return None

    value, is_db = result
    if is_db:
        # ALSA: 需要将 dB 转换为百分比
        return db_to_volume(value)
    else:
        # PulseAudio: 直接返回百分比
        return value


def adjust_volume(direction):
    """
    调整音量

    Args:
        direction: "up" 或 "down"

    Returns:
        int: 调整后的音量百分比，失败返回 None
    """
    # set volume for all detected PCM controllers
    if not PCM_CONTROLS:
        LOGGER.warning("No PCM controls detected")
        return None

    for control in PCM_CONTROLS:
        result = get_current_volume(control)
        if result is None:
            return None

        current_value, is_db = result

        # Check minimum volume for ALSA (dB mode)
        if is_db and direction == "down" and current_value <= MIN_DB:
            LOGGER.info(f"🔇 Already at minimum {MIN_DB}dB")
            return db_to_volume(current_value)

        try:
            if DEVICE_TYPE == "pulse":
                # For PulseAudio, use percentage adjustment (e.g., "5%+")
                delta = "5%+" if direction == "up" else "5%-"
                subprocess.run(["amixer", "-D", "pulse", "set", control, delta], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                # For ALSA, use dB adjustment
                delta = STEP + "+" if direction == "up" else STEP + "-"
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

    # 切换所有检测到的控制器的静音状态
    mute_status = None
    for control in PCM_CONTROLS:
        try:
            if DEVICE_TYPE == "pulse":
                result = subprocess.run(["amixer", "-D", "pulse", "set", control, "toggle"],
                                      capture_output=True, text=True)
            elif CARD == "default":
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

