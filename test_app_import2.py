# -*- coding: utf-8 -*-
"""详细检查 app.py 的路由"""
import sys
import os

if sys.platform == "win32":
    import msvcrt
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("详细检查 app.py 路由")
print("=" * 60)

from app import app

print("\n所有路由列表:")
for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    print(f"   {rule.methods} {rule.rule}")

print("\n" + "=" * 60)
print("检查 v2 相关路由:")
print("=" * 60)

v2_routes = [rule for rule in app.url_map.iter_rules() if 'v2' in rule.rule or 'run_v2' in rule.rule]
for rule in v2_routes:
    print(f"   {rule.methods} {rule.rule}")
