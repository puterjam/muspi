import subprocess
import re
from until.log import LOGGER


def aes_ctr_encrypt(key, nonce, plaintext):
    # 延迟导入（只在使用时导入，避免阻塞启动）
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()

def aes_ctr_decrypt(key, nonce, ciphertext):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext

def get_mac_address():
    try:
        # 方法1: 直接读取系统文件 (最快最可靠)
        with open('/sys/class/net/eth0/address', 'r') as f:
            mac = f.read().strip()
            if mac:
                return mac
    except Exception:
        pass

    try:
        # 方法2: 使用 ip 命令 (通常都会安装)
        result = subprocess.run(['ip', 'link', 'show', 'eth0'], capture_output=True, text=True)
        if result.returncode == 0:
            # 使用正则表达式匹配MAC地址
            mac = re.search(r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', result.stdout)
            if mac:
                return mac.group(0)
    except Exception:
        pass

    return 'a8:47:cb:ec:aa:gf'  # 如果获取失败，返回默认值

def resample_audio(data, original_rate, target_rate):
    """将音频数据从原始采样率重采样到目标采样率"""
    # 延迟导入（只在使用时导入，避免阻塞启动）
    import numpy as np
    from scipy import signal

    # 将字节数据转换为 numpy 数组
    samples = np.frombuffer(data, dtype=np.int16)
    # 计算重采样后的样本数
    num_samples = int(len(samples) * target_rate / original_rate)
    # 重采样
    resampled = signal.resample(samples, num_samples)
    # 转换回 int16 并返回字节
    return resampled.astype(np.int16).tobytes()

def get_audio_capture_device():
    """检测可用的录音设备，返回设备名称如 'hw:3,0'"""
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            # 解析输出，查找第一个可用的录音设备
            # 格式: card 3: Device_1 [USB PnP Sound Device], device 0: USB Audio [USB Audio]
            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith('card'):
                    # 提取 card 和 device 编号
                    match = re.search(r'card (\d+):.*device (\d+):', line)
                    if match:
                        card = match.group(1)
                        device = match.group(2)
                        device_name = f'hw:{card},{device}'
                        LOGGER.info(f"Found audio capture device: {device_name}")
                        return device_name
    except Exception as e:
        LOGGER.warning(f"Failed to detect audio capture device: {e}")

    # 如果检测失败，返回默认值
    LOGGER.warning("Using default audio capture device: default")
    return 'default'
