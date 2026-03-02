#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试脚本
==========

测试SmartCourseEngine API网关的功能。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_health_check():
    """测试健康检查端点"""
    print("测试健康检查端点...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://localhost:8000/health') as response:
                data = await response.json()
                print(f"状态码: {response.status}")
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
        except Exception as e:
            print(f"健康检查失败: {e}")
            return False

async def test_root_endpoint():
    """测试根端点"""
    print("\n测试根端点...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://localhost:8000/') as response:
                data = await response.json()
                print(f"状态码: {response.status}")
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
        except Exception as e:
            print(f"根端点测试失败: {e}")
            return False

async def test_docs_endpoint():
    """测试文档端点"""
    print("\n测试文档端点...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://localhost:8000/docs') as response:
                print(f"状态码: {response.status}")
                print(f"内容类型: {response.headers.get('Content-Type')}")
                return response.status == 200
        except Exception as e:
            print(f"文档端点测试失败: {e}")
            return False

async def test_openapi_endpoint():
    """测试OpenAPI端点"""
    print("\n测试OpenAPI端点...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://localhost:8000/openapi.json') as response:
                data = await response.json()
                print(f"状态码: {response.status}")
                print(f"OpenAPI版本: {data.get('openapi')}")
                print(f"API标题: {data.get('info', {}).get('title')}")
                print(f"路径数量: {len(data.get('paths', {}))}")
                return response.status == 200
        except Exception as e:
            print(f"OpenAPI端点测试失败: {e}")
            return False

async def test_courses_api():
    """测试课程API"""
    print("\n测试课程API...")
    
    async with aiohttp.ClientSession() as session:
        # 测试列出课程
        try:
            async with session.get('http://localhost:8000/api/v1/courses') as response:
                data = await response.json()
                print(f"列出课程 - 状态码: {response.status}")
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
        except Exception as e:
            print(f"列出课程失败: {e}")
            return False

async def test_search_api():
    """测试搜索API"""
    print("\n测试搜索API...")
    
    async with aiohttp.ClientSession() as session:
        try:
            params = {'query': 'Python', 'limit': 5}
            async with session.get('http://localhost:8000/api/v1/knowledge/search', params=params) as response:
                data = await response.json()
                print(f"搜索API - 状态码: {response.status}")
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
        except Exception as e:
            print(f"搜索API测试失败: {e}")
            return False

async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("SmartCourseEngine API 测试")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 60)
    
    test_results = {}
    
    # 运行测试
    test_results['health_check'] = await test_health_check()
    test_results['root_endpoint'] = await test_root_endpoint()
    test_results['docs_endpoint'] = await test_docs_endpoint()
    test_results['openapi_endpoint'] = await test_openapi_endpoint()
    test_results['courses_api'] = await test_courses_api()
    test_results['search_api'] = await test_search_api()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
    
    print("=" * 60)
    print(f"总计: {passed_tests}/{total_tests} 个测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过!")
    elif passed_tests >= total_tests // 2:
        print("⚠️  部分测试通过，核心功能可用")
    else:
        print("❌ 测试失败较多，请检查服务状态")
    
    return passed_tests == total_tests

async def main():
    """主函数"""
    try:
        success = await run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"测试运行失败: {e}")
        return 1

if __name__ == "__main__":
    # 运行异步测试
    exit_code = asyncio.run(main())
    exit(exit_code)