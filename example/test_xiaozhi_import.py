#!/usr/bin/env python3
"""
测试 xiaozhi 插件的导入速度（优化后）
"""

import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("测试 xiaozhi 插件导入速度（lazy import 优化后）")
print("=" * 60)
print()

start = time.time()
try:
    import screen.plugins.xiaozhi.app
    elapsed = time.time() - start
    print(f"✅ 导入成功: {elapsed:.3f}s")

    if elapsed < 1.0:
        print("🎉 优化成功！导入速度 < 1 秒")
    elif elapsed < 2.0:
        print("✅ 良好！导入速度在 1-2 秒之间")
    else:
        print("⚠️  仍然较慢，可能需要进一步优化")

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ 导入失败 ({elapsed:.3f}s): {e}")

print()
print("=" * 60)
print("对比：")
print("  优化前: 5+ 秒")
print(f"  优化后: {elapsed:.3f} 秒")
print(f"  提速: {(5.0 - elapsed) / 5.0 * 100:.1f}%")
print("=" * 60)
