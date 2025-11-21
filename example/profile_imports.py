#!/usr/bin/env python3
"""
分析 xiaozhi 插件的导入速度
找出哪个导入最慢
"""

import time
import sys

def time_import(module_name):
    """测量导入时间"""
    start = time.time()
    try:
        __import__(module_name)
        elapsed = time.time() - start
        print(f"✓ {module_name:30s} {elapsed:.3f}s")
        return elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ {module_name:30s} {elapsed:.3f}s - {e}")
        return elapsed

print("=" * 60)
print("分析 xiaozhi 插件的导入依赖")
print("=" * 60)
print()

# xiaozhi 的所有导入
imports = [
    "json",
    "time",
    "requests",
    "paho.mqtt.client",
    "threading",
    "queue",
    "opuslib",          # 可能慢
    "socket",
    "numpy",            # 可能慢
    "subprocess",
    "re",
    "scipy.signal",     # 可能慢
    "cryptography.hazmat.primitives.ciphers",  # 可能慢
    "cryptography.hazmat.backends",
]

print("测量各个导入的时间:")
print()

times = {}
for module in imports:
    times[module] = time_import(module)

print()
print("=" * 60)
print("导入时间排序 (慢 → 快)")
print("=" * 60)

sorted_times = sorted(times.items(), key=lambda x: x[1], reverse=True)
for module, t in sorted_times:
    if t > 0.5:
        status = "⚠️ 很慢"
    elif t > 0.1:
        status = "⏱️ 较慢"
    else:
        status = "✅ 快"
    print(f"{status} {module:40s} {t:.3f}s")

print()
print("=" * 60)
print("总结")
print("=" * 60)
total = sum(times.values())
print(f"总导入时间: {total:.3f}s")
print()

# 找出慢的导入
slow_imports = [(m, t) for m, t in times.items() if t > 0.5]
if slow_imports:
    print("⚠️ 慢的导入（>0.5s）:")
    for module, t in slow_imports:
        print(f"  - {module}: {t:.3f}s")
    print()
    print("优化建议:")
    print("  1. 延迟导入（lazy import）")
    print("  2. 只在需要时导入")
    print("  3. 使用更轻量的替代库")
else:
    print("✅ 所有导入都很快！")

print()
print("=" * 60)
print("测试完整模块导入")
print("=" * 60)
print()

start = time.time()
try:
    import screen.plugins.xiaozhi
    elapsed = time.time() - start
    print(f"完整模块导入: {elapsed:.3f}s")
except Exception as e:
    elapsed = time.time() - start
    print(f"导入失败 ({elapsed:.3f}s): {e}")
