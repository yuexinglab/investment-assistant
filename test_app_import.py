# -*- coding: utf-8 -*-
"""测试 app.py 能否正常导入"""
import sys
import os

# Windows 下设置 UTF-8 输出
if sys.platform == "win32":
    import msvcrt
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("测试 app.py 能否正常导入")
print("=" * 60)

try:
    # 导入 app
    from app import app
    print("app.py 导入成功!")
    print(f"Flask app name: {app.name}")
    
    # 检查关键路由是否存在
    routes_to_check = [
        "/project/<project_id>/run_v2",
        "/project/<project_id>/result_v2_page",
        "/project/<project_id>/upload_meeting",
    ]
    
    print("\n检查关键路由:")
    app_rules = [rule.endpoint for rule in app.url_map.iter_rules()]
    for route in routes_to_check:
        found = any(route.replace("<project_id>", "") in r for r in app_rules)
        print(f"   {route}: {'存在' if found else '不存在'}")
    
    print("\n全部检查通过!")
    
except Exception as e:
    print(f"导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
