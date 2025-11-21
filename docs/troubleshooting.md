# 故障排除

本文档提供常见问题的解决方案和调试方法。

## 目录

- [AirPlay / shairport-sync 问题](#airplay--shairport-sync-问题)
- [RoonBridge 连接问题](#roonbridge-连接问题)
- [CD 播放器问题](#cd-播放器问题)
- [显示屏问题](#显示屏问题)
- [输入设备问题](#输入设备问题)
- [音频输出问题](#音频输出问题)
- [系统服务问题](#系统服务问题)
- [网络连接问题](#网络连接问题)

---

## AirPlay / shairport-sync 问题

### 问题：找不到 AirPlay 设备

**检查 shairport-sync 状态：**
```bash
sudo systemctl status shairport-sync
```

**重启 shairport-sync：**
```bash
sudo systemctl restart shairport-sync
```

**查看 shairport-sync 日志：**
```bash
journalctl -u shairport-sync -f
```

### 问题：AirPlay 连接后无声音

**检查音频输出配置：**

编辑配置文件：
```bash
sudo nano /etc/shairport-sync.conf
```

确认音频输出设备配置正确：
```conf
alsa = {
    output_device = "hw:0";  // 根据实际硬件调整
};
```

**查看可用音频设备：**
```bash
aplay -l
```

### 问题：编译 shairport-sync 失败

**检查依赖：**
```bash
sudo apt-get install --reinstall build-essential git xmltoman \
    autoconf automake libtool libpopt-dev libconfig-dev \
    libasound2-dev avahi-daemon libavahi-client-dev libssl-dev \
    libsoxr-dev libplist-dev libsodium-dev libavutil-dev \
    libavcodec-dev libavformat-dev uuid-dev libgcrypt-dev xxd
```

**重新编译：**
```bash
cd /tmp
git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync
autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr \
    --with-avahi --with-ssl=openssl --with-systemd --with-airplay-2
make
sudo make install
```

---

## RoonBridge 连接问题

### 问题：Roon 应用中看不到 RoonBridge

**确认网络连接：**
- 树莓派和 Roon Core 必须在同一网络
- 检查防火墙设置

**检查 RoonBridge 服务：**
```bash
systemctl status roonbridge
```

**重启 RoonBridge：**
```bash
sudo systemctl restart roonbridge
```

### 问题：RoonBridge 未安装

**手动安装 RoonBridge（64位系统）：**
```bash
curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv8.sh
chmod +x roonbridge-installer-linuxarmv8.sh
sudo ./roonbridge-installer-linuxarmv8.sh
```

**32位系统请使用：**
```bash
curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv7hf.sh
chmod +x roonbridge-installer-linuxarmv7hf.sh
sudo ./roonbridge-installer-linuxarmv7hf.sh
```

**配置 RoonBridge：**

在 Roon 应用中：
1. 进入 Settings → Audio
2. 找到你的 RoonBridge 设备
3. 点击 Enable
4. 配置音频输出设置

---

## CD 播放器问题

### 问题：CD 无法识别

**检查 CD 驱动器：**
```bash
lsblk
```

应该能看到 `/dev/sr0` 或类似设备。

**测试 CD 读取：**
```bash
cd-discid /dev/cdrom
```

**检查权限：**
```bash
sudo usermod -a -G cdrom $USER
```

重新登录后生效。

### 问题：CD 播放无声音

**检查 mpv 音频输出：**
```bash
mpv cdda:// --ao=alsa
```

**查看 mpv 日志：**
```bash
tail -f ~/.config/mpv/mpv.log
```

### 问题：mpv socket 连接失败

这个问题已在最新版本修复。如果仍然遇到，请：

1. 确认 mpv 已安装：
```bash
mpv --version
```

2. 检查 socket 文件：
```bash
ls -l /tmp/mpv_socket
```

3. 手动清理 socket：
```bash
rm /tmp/mpv_socket
```

---

## 显示屏问题

### 问题：OLED 显示屏无显示

**检查 SPI 接口：**
```bash
ls /dev/spidev*
```

应该能看到 `/dev/spidev0.0` 或类似设备。

**启用 SPI：**
```bash
sudo raspi-config
```
进入 `Interface Options` → `SPI` → `Enable`

**检查硬件连接：**
- 确认 OLED HAT 正确插在树莓派 GPIO 上
- 检查接触是否良好

**测试 SPI 通信：**
```bash
./venv/bin/python -c "from drive.SSD1305 import SSD1305; oled = SSD1305(); print('OK')"
```

### 问题：显示内容异常

**检查显示屏配置：**

编辑 `drive/config.py`，确认参数正确：
```python
OLED_WIDTH = 128
OLED_HEIGHT = 64
SPI_DEVICE = 0
SPI_BUS = 0
```

**重启程序：**
```bash
sudo systemctl restart muspi
```

---

## 输入设备问题

### 问题：按键不响应

**列出输入设备：**
```bash
ls /dev/input/event*
```

**测试输入设备：**
```bash
sudo apt-get install evtest
sudo evtest
```
选择设备后按键，查看是否有输出。

**检查权限：**
```bash
sudo usermod -a -G input $USER
```
重新登录后生效。

### 问题：按键映射不正确

**查看当前按键配置：**
```bash
cat config/keymap.json
```

**测试按键映射：**
```bash
./venv/bin/python until/keymap.py
```

**修改按键映射：**

编辑 `config/keymap.json`，参考 [按键映射配置文档](keymap.md)。

### 问题：蓝牙手柄无法连接

**配对蓝牙设备：**
```bash
bluetoothctl
scan on
pair XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
```

**设置自动重连：**
```bash
sudo nano /etc/bluetooth/main.conf
```
添加：
```conf
[Policy]
AutoEnable=true
```

---

## 音频输出问题

### 问题：没有声音输出

**检查音量：**
```bash
alsamixer
```
按 `M` 取消静音，使用方向键调节音量。

**查看音频设备：**
```bash
aplay -l
```

**测试音频输出：**
```bash
speaker-test -t wav -c 2
```

### 问题：音质差或有杂音

**使用 DAC：**

如果使用外置 DAC，确保：
1. DAC 驱动已正确安装
2. 在 `alsamixer` 中选择正确的输出设备
3. 禁用树莓派板载音频

**调整音频配置：**
```bash
sudo nano /boot/config.txt
```
禁用板载音频：
```conf
#dtparam=audio=on
```

启用 I2S DAC（根据实际 DAC 型号）：
```conf
dtoverlay=hifiberry-dac
```

重启后生效：
```bash
sudo reboot
```

---

## 系统服务问题

### 问题：Muspi 服务无法启动

**查看服务状态：**
```bash
sudo systemctl status muspi
```

**查看详细日志：**
```bash
sudo journalctl -u muspi -f
```

**手动启动测试：**
```bash
cd /home/pi/workspace/muspi
./venv/bin/python main.py
```

观察错误信息。

### 问题：开机不自动启动

**启用服务：**
```bash
sudo systemctl enable muspi
```

**检查服务配置：**
```bash
cat /etc/systemd/system/muspi.service
```

**重新安装服务：**
```bash
./install.sh --service
```

---

## 网络连接问题

### 问题：WiFi 经常断开

**禁用 WiFi 省电模式：**
```bash
sudo iw dev wlan0 set power_save off
```

**永久禁用省电模式：**

编辑 `/etc/rc.local`（在 `exit 0` 之前添加）：
```bash
sudo nano /etc/rc.local
```
添加：
```bash
/sbin/iw dev wlan0 set power_save off
```

**检查 WiFi 信号强度：**
```bash
iwconfig wlan0
```

### 问题：无法连接到小智 AI

**检查网络连接：**
```bash
ping api.tenclass.net
```

**查看小智日志：**
```bash
tail -f ~/.muspi/xiaozhi.log
```

**检查 MAC 地址：**
```bash
ip link show wlan0 | grep ether
```

---

## 调试技巧

### 查看实时日志

```bash
# 系统服务日志
sudo journalctl -u muspi -f

# 应用程序日志
tail -f ~/.muspi/*.log
```

### 增加日志详细程度

编辑 `until/log.py`，修改日志级别：
```python
logging.basicConfig(level=logging.DEBUG)  # 改为 DEBUG
```

### 性能监控

```bash
# CPU 和内存使用
htop

# 进程监控
ps aux | grep python

# 系统资源
vmstat 1
```

### 网络调试

```bash
# 查看网络连接
netstat -tulpn

# 抓包分析
sudo tcpdump -i wlan0 -w capture.pcap
```

---

## 获取帮助

如果以上方法无法解决问题，请：

1. **查看文档**：
   - [插件开发规范](plugins.md)
   - [按键映射配置](keymap.md)
   - [项目结构说明](structure.md)

2. **提交 Issue**：
   - GitHub: https://github.com/puterjam/muspi/issues
   - 提供详细的错误信息、日志和系统环境

3. **社区讨论**：
   - 在 GitHub Discussions 中寻求帮助
   - 分享你的使用经验

## 常见错误代码

| 错误 | 原因 | 解决方案 |
|-----|------|---------|
| `Permission denied` | 权限不足 | 添加用户到相应组或使用 sudo |
| `No such device` | 设备未连接 | 检查硬件连接和驱动 |
| `Connection refused` | 服务未启动 | 启动相应服务 |
| `Module not found` | 依赖未安装 | 运行 `./install.sh` |
| `SPI device not found` | SPI 未启用 | 运行 `sudo raspi-config` 启用 SPI |

## 系统环境检查清单

- [ ] SPI 接口已启用
- [ ] 用户在 `input`、`cdrom`、`audio` 组中
- [ ] Python 3.11+ 已安装
- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装
- [ ] 硬件连接正确
- [ ] 配置文件正确
- [ ] 网络连接正常
