#!/usr/bin/env python3
"""
对比手动帧率控制 vs framerate_regulator
"""

import time
from luma.core.sprite_system import framerate_regulator
from drive.luma_ssd1305 import ssd1305
from PIL import Image, ImageDraw


# ============================================
# 方法1: 手动帧率控制（当前 manager.py 的方式）
# ============================================
def manual_framerate_control(device, target_fps=30):
    """
    手动控制帧率

    优点：
    - 简单直接
    - 完全可控
    - 无额外依赖

    缺点：
    - 需要手动计算和管理时间
    - 帧率不够精确（受系统调度影响）
    - 代码略显冗余
    """
    print(f"手动控制帧率: {target_fps} FPS")

    frame_time = 1.0 / target_fps
    frame_times = []

    for i in range(100):
        frame_start = time.time()

        # === 渲染代码 ===
        image = Image.new("1", (device.width, device.height), 0)
        draw = ImageDraw.Draw(image)
        x = i % device.width
        draw.rectangle((x, 10, x+10, 20), outline=255, fill=255)
        device.display(image)
        # === 渲染结束 ===

        # 手动帧率控制
        elapsed = time.time() - frame_start
        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)

        # 记录实际帧时间
        actual_frame_time = time.time() - frame_start
        frame_times.append(actual_frame_time)

    # 分析帧率稳定性
    avg_fps = 1.0 / (sum(frame_times) / len(frame_times))
    variance = sum(abs(ft - frame_time) for ft in frame_times) / len(frame_times)

    print(f"  目标 FPS: {target_fps}")
    print(f"  实际平均 FPS: {avg_fps:.2f}")
    print(f"  帧时间方差: {variance*1000:.2f}ms")
    print()


# ============================================
# 方法2: 使用 framerate_regulator
# ============================================
def using_framerate_regulator(device, target_fps=30):
    """
    使用 luma 的 framerate_regulator

    优点：
    - 代码更简洁
    - 自动时间管理
    - 更精确的帧率控制
    - 提供统计信息（平均FPS等）
    - 上下文管理器，自动处理进入/退出

    缺点：
    - 增加一个依赖
    - 稍微降低灵活性（但够用）
    """
    print(f"使用 framerate_regulator: {target_fps} FPS")

    regulator = framerate_regulator(fps=target_fps)

    for i in range(100):
        # 使用上下文管理器，自动控制帧率
        with regulator:
            # === 渲染代码 ===
            image = Image.new("1", (device.width, device.height), 0)
            draw = ImageDraw.Draw(image)
            x = i % device.width
            draw.rectangle((x, 10, x+10, 20), outline=255, fill=255)
            device.display(image)
            # === 渲染结束 ===

        # regulator 自动处理了时间计算和 sleep

    # framerate_regulator 提供统计信息
    print(f"  目标 FPS: {target_fps}")
    print(f"  实际平均 FPS: {regulator.average_transit_time():.2f}")
    print()


# ============================================
# 代码对比
# ============================================
def code_comparison():
    """代码量对比"""

    print("\n" + "="*50)
    print("代码对比")
    print("="*50)

    print("\n【手动控制】需要的代码:")
    print("""
    frame_time = 1.0 / target_fps

    while True:
        frame_start = time.time()

        # 渲染代码
        render()

        # 手动计算和睡眠
        elapsed = time.time() - frame_start
        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)
    """)

    print("\n【framerate_regulator】需要的代码:")
    print("""
    regulator = framerate_regulator(fps=30)

    while True:
        with regulator:
            # 渲染代码
            render()
        # 自动处理帧率控制
    """)

    print("\n减少了 3 行代码，更清晰！")


# ============================================
# 性能对比
# ============================================
def performance_test(device):
    """测试性能差异"""
    print("\n" + "="*50)
    print("性能测试")
    print("="*50)
    print()

    # 测试不同帧率
    for fps in [10, 30, 60]:
        print(f"--- 测试 {fps} FPS ---")
        manual_framerate_control(device, fps)
        using_framerate_regulator(device, fps)


# ============================================
# framerate_regulator 的额外功能
# ============================================
def regulator_extra_features():
    """展示 framerate_regulator 的额外功能"""
    print("\n" + "="*50)
    print("framerate_regulator 额外功能")
    print("="*50)
    print()

    regulator = framerate_regulator(fps=30, max_sleep_ms=100)

    print("可配置参数：")
    print("  - fps: 目标帧率")
    print("  - max_sleep_ms: 最大睡眠时间（防止卡死）")
    print()

    print("提供的方法：")
    print("  - average_transit_time(): 平均帧时间")
    print("  - effective_FPS(): 实际有效 FPS")
    print()

    # 模拟几帧
    for i in range(10):
        with regulator:
            time.sleep(0.01)  # 模拟渲染

    print(f"运行 10 帧后:")
    print(f"  平均帧时间: {regulator.average_transit_time():.4f}s")
    print(f"  有效 FPS: ~{1.0/regulator.average_transit_time():.1f}")


def main():
    device = ssd1305(rotate=2)

    print("帧率控制对比测试")
    print("="*50)

    try:
        # 1. 代码对比
        code_comparison()

        # 2. 性能测试
        performance_test(device)

        # 3. 额外功能
        regulator_extra_features()

        print("\n" + "="*50)
        print("结论")
        print("="*50)
        print("""
对于 manager.py：

【保持手动控制】如果：
  ✓ 你需要动态改变帧率
  ✓ 你需要基于条件跳过帧
  ✓ 你已经写好了，工作正常
  ✓ 你不想增加依赖

【使用 framerate_regulator】如果：
  ✓ 你想简化代码
  ✓ 你需要更精确的帧率
  ✓ 你想要内置的性能统计
  ✓ 你的帧率是固定的

建议：manager.py 保持当前方式，但可以在特定插件中使用
      framerate_regulator（比如游戏插件需要固定 60 FPS）
        """)

    except KeyboardInterrupt:
        print("\n测试中断")
    finally:
        device.clear()


if __name__ == "__main__":
    main()
