#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整API测试脚本
测试所有7个微服务的API端点

作者: SmartCourseEngine Team
日期: 2026-03-07
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, List

# API网关地址
API_BASE_URL = "http://localhost:80"

async def test_endpoint(session: aiohttp.ClientSession, method: str, endpoint: str, 
                       data: Dict[str, Any] = None, expected_status: int = 200) -> Dict[str, Any]:
    """测试单个端点"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            async with session.get(url) as response:
                status = response.status
                text = await response.text()
        elif method == "POST":
            async with session.post(url, json=data) as response:
                status = response.status
                text = await response.text()
        else:
            return {"success": False, "error": f"不支持的HTTP方法: {method}"}
        
        try:
            result = json.loads(text) if text else {}
        except:
            result = {"raw_response": text[:200]}
        
        success = status == expected_status
        return {
            "success": success,
            "status": status,
            "result": result,
            "error": None if success else f"期望状态 {expected_status}, 实际状态 {status}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": 0,
            "result": None,
            "error": str(e)
        }

async def run_tests():
    """运行所有测试"""
    print("🧪 开始测试 SmartCourseEngine 完整API")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        tests = []
        
        # 1. 健康检查
        print("🔍 测试健康检查...")
        tests.append(("GET", "/health", None, 200))
        
        # 2. 课程管理API
        print("📚 测试课程管理API...")
        tests.append(("GET", "/api/v1/courses", None, 200))
        tests.append(("GET", "/api/v1/courses/1", None, 200))
        
        # 3. 课件生成API
        print("📝 测试课件生成API...")
        tests.append(("GET", "/api/v1/courses/1/generations", None, 200))
        
        # 4. 视频分析API
        print("🎥 测试视频分析API...")
        tests.append(("GET", "/api/v1/videos/analyses/test-id", None, 200))
        
        # 5. 知识管理API
        print("🧠 测试知识管理API...")
        tests.append(("GET", "/api/v1/knowledge/graph", None, 200))
        
        # 6. 搜索API
        print("🔎 测试搜索API...")
        tests.append(("GET", "/api/v1/search/suggestions?query=python", None, 200))
        
        # 7. 推荐API
        print("🎯 测试推荐API...")
        tests.append(("GET", "/api/v1/users/1/recommendations", None, 200))
        tests.append(("GET", "/api/v1/courses/1/related", None, 200))
        
        # 8. 通知API
        print("📨 测试通知API...")
        tests.append(("GET", "/api/v1/users/1/notifications", None, 200))
        
        # 9. 系统管理API
        print("⚙️  测试系统管理API...")
        tests.append(("GET", "/api/v1/system/status", None, 200))
        
        # 运行所有测试
        results = []
        for method, endpoint, data, expected_status in tests:
            print(f"  → 测试 {method} {endpoint}")
            result = await test_endpoint(session, method, endpoint, data, expected_status)
            results.append((endpoint, result))
            await asyncio.sleep(0.1)  # 避免请求过快
        
        # 输出结果
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        success_count = 0
        total_count = len(results)
        
        for endpoint, result in results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {endpoint}")
            
            if result["success"]:
                success_count += 1
            else:
                print(f"   错误: {result['error']}")
                if result.get("result"):
                    print(f"   响应: {json.dumps(result['result'], indent=2, ensure_ascii=False)[:200]}...")
        
        print("\n" + "=" * 60)
        success_rate = (success_count / total_count) * 100
        print(f"📈 测试完成: {success_count}/{total_count} 通过 ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 所有测试通过！系统运行正常。")
        elif success_rate >= 80:
            print("👍 大部分测试通过，系统基本可用。")
        else:
            print("⚠️  部分测试失败，需要检查服务状态。")
        
        # 显示服务访问信息
        print("\n" + "=" * 60)
        print("🌐 服务访问信息")
        print("=" * 60)
        print(f"API网关:      {API_BASE_URL}")
        print(f"API文档:      {API_BASE_URL}/docs")
        print("课件生成服务: http://localhost:8001")
        print("视频分析服务: http://localhost:8002")
        print("知识提取服务: http://localhost:8003")
        print("搜索服务:     http://localhost:8004")
        print("推荐服务:     http://localhost:8005")
        print("通知服务:     http://localhost:8006")

def main():
    """主函数"""
    print("🚀 SmartCourseEngine 完整API测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()