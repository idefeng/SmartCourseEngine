#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动后端服务脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

print("=" * 60)
print("启动 SmartCourseEngine 后端服务")
print("=" * 60)

# 检查数据库
db_path = project_root / "data" / "smartcourse.db"
if not db_path.exists():
    print("⚠️  警告: 数据库文件不存在")
    print("正在初始化数据库...")
    
    # 导入并运行数据库初始化
    try:
        from init_simple import main as init_db
        init_db()
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)
else:
    print(f"✅ 数据库文件存在: {db_path}")

# 检查Python路径
print("\nPython路径:")
for path in sys.path[:5]:
    print(f"  {path}")

# 检查模块导入
print("\n检查模块导入...")
try:
    from shared import api_response, auth
    print("✅ shared模块导入成功")
except ImportError as e:
    print(f"❌ shared模块导入失败: {e}")
    sys.exit(1)

try:
    # 直接导入auth_routes模块
    import importlib.util
    auth_routes_path = project_root / "api-gateway" / "auth_routes.py"
    if auth_routes_path.exists():
        spec = importlib.util.spec_from_file_location("auth_routes", auth_routes_path)
        auth_routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_routes)
        print("✅ 认证路由导入成功")
    else:
        print("⚠️  认证路由文件不存在")
except Exception as e:
    print(f"⚠️  认证路由导入失败: {e}")

try:
    from shared import websocket
    print("✅ WebSocket模块导入成功")
except ImportError as e:
    print(f"⚠️  WebSocket模块导入失败: {e}")

try:
    from shared import file_upload
    print("✅ 文件上传模块导入成功")
except ImportError as e:
    print(f"⚠️  文件上传模块导入失败: {e}")

print("\n" + "=" * 60)
print("启动API网关...")
print("=" * 60)

# 导入并启动API网关
try:
    # 直接运行main_unified.py
    main_unified_path = project_root / "api-gateway" / "main_unified.py"
    if main_unified_path.exists():
        print(f"启动API网关: {main_unified_path}")
        
        # 添加api-gateway目录到Python路径
        sys.path.insert(0, str(project_root / "api-gateway"))
        
        # 执行main_unified.py
        exec(open(main_unified_path).read())
    else:
        print(f"❌ API网关文件不存在: {main_unified_path}")
except KeyboardInterrupt:
    print("\n👋 服务已停止")
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()