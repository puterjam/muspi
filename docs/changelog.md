# 更新日志

## 最近更新 (2025-11-21)

### CD 播放器优化

- ✅ 修复 mpv socket 连接问题（避免 socat 连接拒绝错误）
- ✅ 修复重复播放问题（防止在 CD 读取时重复启动）
- ✅ 修复长时间空闲后 CD 重载问题
- ✅ 改进播放状态管理和错误处理
- ✅ 添加 ALSA 音频输出支持

### 音量条显示优化

- ✅ 改进音量条的视觉表现
- ✅ 修复 Overlay 层帧率问题
- ✅ 出现 Overlay 不改变底层帧率

### 键盘映射系统

- ✅ 分离 keymap 配置到独立文件 (`config/keymap.json`)
- ✅ 支持自定义按键映射
- ✅ 改进输入设备热插拔支持
- ✅ 添加按键映射文档

### 安装脚本改进

- ✅ 重命名 `install_dependencies.sh` 为 `install.sh`
- ✅ 添加精简安装模式（约 5 分钟）
- ✅ 添加完整安装模式（约 30-60 分钟）
- ✅ 动态生成插件配置
- ✅ 添加服务安装选项
- ✅ 添加彩色 ASCII logo

### 文档完善

- ✅ 添加插件开发规范文档
- ✅ 添加按键映射配置文档
- ✅ 完善 README 硬件清单
- ✅ 添加文档导航

## 历史更新

### AirPlay 2 支持

- ✅ 集成 shairport-sync
- ✅ 自动编译和配置
- ✅ AirPlay 插件实现
- ✅ 自动显示/隐藏逻辑

### WiFi 稳定性优化

- ✅ WiFi 防掉线优化
- ✅ 自动禁用省电模式
- ✅ 连接保活机制

### Python 3.13 迁移

- ✅ 迁移到 Python 3.13
- ✅ 用 `watchdog` 替换 `pyinotify`
- ✅ 解决 asyncore 兼容性问题

### 性能优化

- ✅ 使用 cd-discid 替代 libdiscid
- ✅ CD 识别速度提升
- ✅ 优化 Roon 和小智的重连机制

### 功能增强

- ✅ 添加 Overlay 层支持
- ✅ 兼容 TTS 的 stop 状态
- ✅ 完善安装脚本（自动编译依赖、配置服务）

### 小智 AI

- ✅ MAC 地址自动检测
- ✅ 网络接口优先级（wlan0 → eth0 → 其他）
- ✅ UUID fallback 方案

## 版本历史

详细的版本历史和提交记录请查看：

```bash
git log --oneline --graph --all
```
