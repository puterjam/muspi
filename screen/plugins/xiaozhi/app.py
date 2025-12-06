# 基础导入（快速）
import json
import time
import requests
import paho.mqtt.client as mqtt
import threading
import queue
import socket
import subprocess

from screen.base import DisplayPlugin
from until.log import LOGGER
from until.keymap import get_keymap

from ui.emotion import RobotEmotion
from ui.textarea import TextArea
from ui.animation import Animation, Operator

# 导入本地工具函数
from .until import (
    get_mac_address,
    resample_audio,
    aes_ctr_encrypt,
    aes_ctr_decrypt,
    get_audio_capture_device
)

OTA_VERSION_URL = 'https://api.tenclass.net/xiaozhi/ota/'

USE_PULSE = False # 使用pulse音频，用于支持蓝牙音箱

# 设备采样率
DEVICE_RATE = 48000
# 目标采样率
TARGET_RATE = 16000
# 降采样比例
RESAMPLE_RATIO = TARGET_RATE / DEVICE_RATE
FRAME_SIZE = 960  # Opus 帧大小

EMOTION_FPS = 45.0
SLEEP_TIMEOUT = 3 * 60 # 3 minutes for sleep
CHATBOX_WIDTH = 62 # 聊天框宽度
ROBOT_OFFSET_X = 34

AUTO_CHATBOX = False

class MESSAGE:
    HELLO = {"type": "hello", "version": 3, "transport": "udp",
                        "audio_params": {"format": "opus", "sample_rate": TARGET_RATE, "channels": 1, "frame_duration": 60}}
    ABORT = {"type": "abort"}
    LISTEN = {"type": "listen", "state": "start", "mode": "manual"}
    STOP_LISTEN = {"type": "listen", "state": "stop"}

class xiaozhi(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "xiaozhi"
        super().__init__(manager, width, height)

        self.framerate = EMOTION_FPS #set framerate to EMOTION_FPS
        self.mqtt_info = {}
        self._receive_msg = {'session_id': None}
        self.is_listening = False
        self.is_speaking = False
        self.need_add_device = False

        self.local_sequence = 0
        self.tts_state = None

        self.udp_socket = None
        self.conn_state = False
        self.mqttc = None
        self.mac_addr = get_mac_address()

        # 检测录音设备
        self.audio_device = get_audio_capture_device()

        # 动画相关属性
        self.robot_offset_x = 0
        self.chatbox_offset_x = 0

        self.animations = {}  # 存储所有动画状态
        self.anim = Animation(0.3)

        self.sleep_time = time.time()
        self.is_sleeping = False

        self.robot = RobotEmotion()
        self.text_area = TextArea(font=self.font8,width=CHATBOX_WIDTH,height=height,line_spacing=4)

        # init keymap
        self.keymap = get_keymap()

        # init audio & mqtt
        # self.audio = pyaudio.PyAudio()
        self.send_audio_thread = threading.Thread()
        self.recv_audio_thread = threading.Thread()
        
        self.ota_thread = threading.Thread(target=self._get_ota_version, daemon=True)
        self.ota_thread.start()
        LOGGER.info("OTA version fetch started in background")

    def _get_ota_version(self):
        try:
            header = {
                'Device-Id': self.mac_addr,
                'Content-Type': 'application/json'
            }
            post_data = {"flash_size": 16777216, "minimum_free_heap_size": 8318916, "mac_address": f"{self.mac_addr}",
                    "chip_model_name": "esp32s3", "chip_info": {"model": 9, "cores": 2, "revision": 2, "features": 18},
                    "application": {"name": "Muspi", "version": "0.9.9", "compile_time": "Jan 22 2025T20:40:23Z",
                                    "idf_version": "v5.3.2-dirty",
                                    "elf_sha256": "22986216df095587c42f8aeb06b239781c68ad8df80321e260556da7fcf5f522"}}
            
            # LOGGER.info(f"request ota version with mac: \033[94m{self.mac_addr}\033[0m")
            
            response = requests.post(OTA_VERSION_URL, headers=header, data=json.dumps(post_data))
            LOGGER.debug(response.text)
            response_json = response.json()
            
            if 'mqtt' not in response_json:
                    LOGGER.error(f"OTA response missing 'mqtt'.")
                    return
                
            self.mqtt_info = response_json['mqtt']
            self._create_mqtt_client(self.mqtt_info)
        except Exception as e:
            LOGGER.error(f"Failed to get OTA version and setup MQTT: {e}")
           

    def _create_mqtt_client(self, mqtt_config):
        self.mqttc = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, 
                                 client_id=mqtt_config['client_id'])
        self.mqttc.username_pw_set(username=mqtt_config['username'], password=mqtt_config['password'])
        self.mqttc.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=mqtt.ssl.CERT_REQUIRED,
                  tls_version=mqtt.ssl.PROTOCOL_TLS, ciphers=None)
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_message = self._on_message
        self.mqttc.connect(host=mqtt_config['endpoint'], port=8883)
        self.mqttc.loop_start()
        
        # show welcome message
        self._open_chatbox()
        self.text_area.append_text("你好.")
        self.text_area.append_text("我是小派.")
        self.text_area.append_text("---")
        threading.Timer(
            3,
            lambda: self._close_chatbox()
        ).start()

    def _on_connect(self, client, userdata, flags, rs, pr):
        LOGGER.info(f"connect to mqtt server at {self.mqtt_info['endpoint']}")

    def _on_message(self, client, userdata, message):
        msg = json.loads(message.payload)
        LOGGER.info(f"recv: {msg}")
        self.sleep_time = time.time()  # reset sleep time
        
        if msg['type'] == 'hello':
            self._receive_msg = msg
            self.need_add_device = False
            self._connect_udp()
            
        if msg['type'] == 'llm':
            self.robot.set_emotion(msg['emotion'])
        # if msg['type'] == 'stt':
        if msg['type'] == 'tts':
            self.tts_state = msg['state']
            if self.tts_state == "sentence_start":
                self.is_speaking = True
                if AUTO_CHATBOX:
                    self._open_chatbox()
                self.text_area.append_text(msg['text'])
                
                if msg.get('text') and "请登录到控制面板添加设备，输入验证码" in msg['text']:
                    self._open_chatbox()
                    self.robot.set_emotion("thinking")
                    self.need_add_device = True
                    
            elif self.tts_state == "sentence_end" or self.tts_state == "stop":
                if self.need_add_device:
                    self.text_area.append_text("一会见:)")
                    self._receive_msg['session_id'] = None # 清空session_id
                    self._close_udp_conn()
                
                self.is_speaking = False
                self.robot.set_emotion("neutral")
                
        if msg['type'] == 'goodbye' and self.udp_socket and msg['session_id'] == self._receive_msg['session_id']:
            LOGGER.info("recv good bye msg")
            self.text_area.append_text("bye.")
            if AUTO_CHATBOX:
                self._close_chatbox()
            self._receive_msg['session_id'] = None
            self._close_udp_conn()

    def _connect_udp(self):
        if not self.udp_socket:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        LOGGER.info(f"connect to {self._receive_msg['udp']['server']}:{self._receive_msg['udp']['port']}")
        self.udp_socket.connect((self._receive_msg['udp']['server'], self._receive_msg['udp']['port']))
        self.conn_state = True
        self._start_audio_thread()
            
    def _start_audio_thread(self):
        if not self.send_audio_thread.is_alive():
            # 启动一个线程，用于发送音频数据
            self.send_audio_thread = threading.Thread(target=self._send_audio)
            self.send_audio_thread.start()
        else:
            LOGGER.info("send_audio_thread is alive")
            
        if not self.recv_audio_thread.is_alive():
            self.recv_audio_thread = threading.Thread(target=self._recv_audio)
            self.recv_audio_thread.start()
        else:
            LOGGER.info("recv_audio_thread is alive")

    # close udp connection
    def _close_udp_conn(self):
        self.conn_state = False # 关闭连接状态, 停止发送和接收音频数据
        if self.udp_socket:
            try:
                # 发送一个空数据包来唤醒 recvfrom
                self.udp_socket.sendto(b'', (self._receive_msg['udp']['server'], self._receive_msg['udp']['port']))
            except socket.error:
                pass
            finally:
                self.udp_socket.close()
                self.udp_socket = None
        
    def _push_mqtt_msg(self, message):
        LOGGER.info(f"send: {message}")
        self.mqttc.publish(self.mqtt_info['publish_topic'], json.dumps(message))
    
    def _on_listening(self):
        self.is_listening = True
        self.robot.set_emotion("listening")
        # 判断是否需要发送hello消息
        if self.conn_state is False or self._receive_msg['session_id'] is None:
            # 发送hello消息,建立udp连接
            self._push_mqtt_msg(MESSAGE.HELLO)
        if self.tts_state == "start" or self.tts_state == "entence_start":
            # 在播放状态下发送abort消息
            self._push_mqtt_msg(MESSAGE.ABORT)
        if self._receive_msg['session_id'] is not None:
            # 发送start listen消息
            self._push_mqtt_msg({**MESSAGE.LISTEN, 'session_id': self._receive_msg['session_id']})

    def _off_listening(self):
        self.is_listening = False
        self.robot.set_emotion("neutral")
        if self._receive_msg['session_id'] is not None:
            self._push_mqtt_msg({**MESSAGE.STOP_LISTEN, 'session_id': self._receive_msg['session_id']})

    def _send_audio(self):
        import opuslib

        key = self._receive_msg['udp']['key']
        nonce = self._receive_msg['udp']['nonce']
        server_ip = self._receive_msg['udp']['server']
        server_port = self._receive_msg['udp']['port']

        # 初始化Opus编码器
        encoder = opuslib.Encoder(TARGET_RATE, 1, opuslib.APPLICATION_AUDIO)
        
        try:
            # 使用arecord命令录制音频，使用设备采样率
            cmd = [
                'arecord',
                '-D', 'pulse' if USE_PULSE else self.audio_device,   # 使用检测到的音频设备
                '-f', 'S16_LE',  # 16位小端
                '-r', str(DEVICE_RATE),  # 使用设备采样率
                '-c', '1',       # 单声道
                '-t', 'raw',     # 裸PCM流
                '-q'             # 静默模式
            ]
            LOGGER.debug(f"arecord cmd: {cmd}")
            
            arecord = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            LOGGER.info(f"start recording with arecord, sample rate: {DEVICE_RATE}Hz")
            
            while self.conn_state:
                if self.is_listening:
                    try:
                        # 读取一帧音频数据
                        data = arecord.stdout.read(FRAME_SIZE * 2)  # 16位 = 2字节
                        if not data:
                            break
                            
                        # 降采样到目标采样率
                        resampled_data = resample_audio(data, DEVICE_RATE, TARGET_RATE)
                        encoded_data = encoder.encode(resampled_data, int(FRAME_SIZE * RESAMPLE_RATIO))
                        self.local_sequence += 1
                        new_nonce = nonce[0:4] + format(len(encoded_data), '04x') + nonce[8:24] + format(self.local_sequence, '08x')
                        # 加密数据，添加nonce
                        encrypt_encoded_data = aes_ctr_encrypt(bytes.fromhex(key), bytes.fromhex(new_nonce), bytes(encoded_data))
                        data = bytes.fromhex(new_nonce) + encrypt_encoded_data
                        
                        self.udp_socket.sendto(data, (server_ip, server_port))
                    except Exception as e:
                        LOGGER.error(f"read audio data err: {e}")
                        break
                else:
                    time.sleep(0.1)
        except Exception as e:
            LOGGER.error(f"send audio err: {e}")
        finally:
            LOGGER.info("send audio exit()")
            self.local_sequence = 0
            arecord.stdout.close()
            arecord.wait()
    
    def _recv_audio(self):
        import threading
        import opuslib

        key = self._receive_msg['udp']['key']
        # nonce = self._receive_msg['udp']['nonce']
        sample_rate = self._receive_msg['audio_params']['sample_rate']
        frame_duration = self._receive_msg['audio_params']['frame_duration']
        frame_num = int(sample_rate * (frame_duration / 1000 ))

        # LOGGER.debug(f"recv audio: sample_rate -> {sample_rate}, frame_duration -> {frame_duration}, frame_num -> {frame_num}")

        # 初始化Opus解码器
        decoder = opuslib.Decoder(fs=sample_rate, channels=1)
        # 使用更优化的aplay参数
        cmd = [
            'aplay',
            '-D', 'pulse' if USE_PULSE else 'default',   # 指定USB音频设备
            '-f', 'S16_LE',  # 16位小端
            '-r', str(sample_rate),   # 使用实际采样率
            '-c', '1',       # 单声道
            '-t', 'raw',     # 裸PCM流
            '-B', '100000',  # 增加缓冲区大小
            '-q'             # 静默模式
        ]
        LOGGER.debug(f"aplay cmd: {cmd}")
        spk = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        pcm_queue = queue.Queue(maxsize=100)  # 进一步增加队列大小
        self._audio_threads_running = True

        def recv_decode_thread():
            while self.conn_state and self._audio_threads_running:
                try:
                    if self.udp_socket is None:
                        break
                    data, server = self.udp_socket.recvfrom(4096)
                    if len(data) < 16:
                        LOGGER.error(f"recv audio data err: {len(data)}")
                        continue
                    received_nonce = data[:16]
                    encrypted_audio = data[16:]
                    decrypted = aes_ctr_decrypt(
                        bytes.fromhex(key),
                        received_nonce,
                        encrypted_audio
                    )
                    decoded = decoder.decode(decrypted, frame_num, decode_fec=False)
                    try:
                        pcm_queue.put_nowait(decoded)  # 使用非阻塞方式
                    except queue.Full:
                        # 队列满时，丢弃最旧的数据
                        try:
                            pcm_queue.get_nowait()
                            pcm_queue.put_nowait(decoded)
                        except queue.Full:
                            pass
                except Exception as e:
                    LOGGER.error(f"recv/decode audio err: {e}")
                    break

        def play_thread():
            cache = bytearray()
            cache_size = 1024  # 进一步减小缓存大小
            while self.conn_state and self._audio_threads_running:
                try:
                    decoded = pcm_queue.get_nowait()  # 使用非阻塞方式
                except queue.Empty:
                    # 队列为空时，使用静音填充
                    decoded = b'\x00' * (frame_num * 2)
                    time.sleep(0.01)  # 短暂休眠，避免CPU占用过高
                
                cache += decoded
                if len(cache) >= cache_size:
                    try:
                        spk.stdin.write(cache)
                        spk.stdin.flush()
                        cache.clear()
                    except Exception as e:
                        if hasattr(e, 'errno') and e.errno == -9988:
                            LOGGER.info("audio stream closed, playback thread exit.")
                        else:
                            LOGGER.warning(f"audio playback err: {e}")
                        break
        try:
            t1 = threading.Thread(target=recv_decode_thread, daemon=True)
            t2 = threading.Thread(target=play_thread, daemon=True)
            t1.start()
            t2.start()
            # 主线程等待子线程结束
            while self.conn_state and self._audio_threads_running and (t1.is_alive() or t2.is_alive()):
                t1.join(timeout=0.1)
                t2.join(timeout=0.1)
        except Exception as e:
            LOGGER.error(f"audio thread err: {e}")
        finally:
            self._audio_threads_running = False
            LOGGER.info("recv audio exit()")
            # spk.stop_stream()
            # spk.close()
            spk.stdin.close()
            spk.wait()
            

    def switch_chatbox(self):
        if self.chatbox_offset_x == 0:
            self._open_chatbox()
        else:
            self._close_chatbox()
    
    #def start(self, id, obj, attr, target, duration=None):
    def _open_chatbox(self):
        self.anim.start('robot_offset_x',obj=self,attr='robot_offset_x',target=-ROBOT_OFFSET_X,operator=Operator.ease_out_bounce)
        self.anim.start('chatbox_offset_x',obj=self,attr='chatbox_offset_x',target=-CHATBOX_WIDTH,operator=Operator.ease_out_bounce)
            
    def _close_chatbox(self):
        self.anim.start('robot_offset_x',obj=self,attr='robot_offset_x',target=0,operator=Operator.ease_out_bounce)
        self.anim.start('chatbox_offset_x',obj=self,attr='chatbox_offset_x',target=0,operator=Operator.ease_out_bounce)
   
    def render(self):
        draw = self.canvas
        current_time = time.time()
        
        if current_time - self.sleep_time > SLEEP_TIMEOUT:
            self._sleep()
        
        # 更新所有动画
        self.anim.update()
        
        robot = self.robot.update()
        # 计算居中位置
        x = (self.width - robot.width) // 2 + self.robot_offset_x
        y = (self.height - robot.height) // 2
        draw.bitmap((x, y), robot, fill=255)
        
        chatbox = self.text_area.render()
        x = self.width + round(self.chatbox_offset_x)  # 放在机器人右边
        y = (self.height - chatbox.height) // 2
        draw.bitmap((x, y), chatbox, fill=255)
        
    def _wakeup(self):
        if self.is_sleeping:
            self.sleep_time = time.time() #reset sleep time
            self.is_sleeping = False
            self.robot.set_emotion("angry")
            
            # 设置表情切换计时器
            threading.Timer(
                3,
                lambda: self.robot.set_emotion("neutral")
            ).start()
            
        
    def _sleep(self):
        if not self.is_sleeping:
            self.is_sleeping = True
            self.robot.set_emotion("sleepy")
            self._close_chatbox()
        
    # 按键回调
    def key_callback(self, evt):
        # 获取全局功能按键
        key_select = self.keymap.action_select  # 语音输入
        key_cancel = self.keymap.action_cancel  # 切换聊天框

        self._wakeup()
        if evt.value == 1:  # key down
            # select 键 = 开始语音输入
            if self.keymap.match(key_select):
                self._on_listening()

            # cancel 键 = 切换聊天框显示
            if self.keymap.match(key_cancel):
                self.switch_chatbox()

        if evt.value == 0:  # key up
            # select 键释放 = 停止语音输入
            if self.keymap.match(key_select):
                self._off_listening()
                     
    # 设置激活状态
    def set_active(self, value):
        super().set_active(value)
        if value:
            self.manager.key_listener.on(self.key_callback)
            self._wakeup()
            # self._create_mqtt_client(self.mqtt_info)
        else:
            self.manager.key_listener.off(self.key_callback)
            # if self.mqttc:
            #     self.mqttc.loop_stop()
            #     self.mqttc = None