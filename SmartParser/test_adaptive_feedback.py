#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adaptive Feedback 功能测试脚本
"""

import json
from pathlib import Path


def test_basic_import():
    """测试基本导入"""
    print("=== 测试模块导入 ===")
    from adaptive_feedback import (
        AdaptiveFeedbackEngine,
        TraineePerformance,
        WeakPointDiagnosis,
        RelearningRequest,
        StepScore,
        RelearningStatus,
        BANDAGING_EXAMPLE
    )
    print("✓ 模块导入成功")
    return True


def test_step_score():
    """测试步骤得分数据模型"""
    print("\n=== 测试 StepScore 模型 ===")
    from adaptive_feedback import StepScore, PASS_THRESHOLD
    
    # 测试及格分数
    passing_step = StepScore(
        step_id="step_1",
        step_name="测试步骤",
        score=75
    )
    assert passing_step.is_passing, "75分应该及格"
    print(f"  得分: {passing_step.score}, 及格: {passing_step.is_passing}")
    
    # 测试不及格分数
    failing_step = StepScore(
        step_id="step_2",
        step_name="测试步骤2",
        score=48
    )
    assert not failing_step.is_passing, "48分不应该及格"
    print(f"  得分: {failing_step.score}, 及格: {failing_step.is_passing}")
    
    print("✓ StepScore 模型测试通过")
    return True


def test_trainee_performance():
    """测试学员表现数据模型"""
    print("\n=== 测试 TraineePerformance 模型 ===")
    from adaptive_feedback import TraineePerformance, StepScore
    
    steps = [
        StepScore(step_id="s1", step_name="步骤1", score=85),
        StepScore(step_id="s2", step_name="步骤2", score=48),  # 薄弱点
        StepScore(step_id="s3", step_name="步骤3", score=72)
    ]
    
    perf = TraineePerformance(
        trainee_id="test_trainee",
        assessment_id="test_assessment",
        assessment_title="测试考核",
        course_id="test_course",
        step_scores=steps,
        total_score=68.3
    )
    
    weak_steps = perf.get_weak_steps()
    print(f"  总分: {perf.total_score}, 及格: {perf.is_passing}")
    print(f"  薄弱环节数: {len(weak_steps)}")
    
    assert len(weak_steps) == 1, "应该有1个薄弱环节"
    assert weak_steps[0].step_name == "步骤2", "薄弱环节应该是步骤2"
    
    print("✓ TraineePerformance 模型测试通过")
    return True


def test_engine_initialization():
    """测试引擎初始化"""
    print("\n=== 测试引擎初始化 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine
    
    engine = AdaptiveFeedbackEngine()
    
    # 检查输出目录
    assert engine.output_dir.exists(), "输出目录应该存在"
    print(f"  输出目录: {engine.output_dir}")
    
    print("✓ 引擎初始化测试通过")
    return True


def test_mock_data_fetching():
    """测试模拟数据获取"""
    print("\n=== 测试模拟数据获取 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine
    
    engine = AdaptiveFeedbackEngine()
    
    # 使用模拟数据
    performances = engine.fetch_trainee_scores(
        trainee_id="trainee_demo_001",
        course_id="childcare_first_aid"
    )
    
    assert len(performances) > 0, "应该获取到实训记录"
    print(f"  获取到 {len(performances)} 条记录")
    
    perf = performances[0]
    print(f"  评估标题: {perf.assessment_title}")
    print(f"  步骤数: {len(perf.step_scores)}")
    
    print("✓ 模拟数据获取测试通过")
    return True


def test_weak_point_diagnosis():
    """测试薄弱点诊断"""
    print("\n=== 测试薄弱点诊断 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine
    
    engine = AdaptiveFeedbackEngine()
    
    # 获取模拟数据
    performances = engine.fetch_trainee_scores(
        trainee_id="trainee_demo_001"
    )
    
    # 诊断薄弱点
    weak_points = engine.diagnose_weak_points(performances)
    
    assert len(weak_points) > 0, "应该发现薄弱点"
    print(f"  发现 {len(weak_points)} 个薄弱点")
    
    for wp in weak_points:
        print(f"    - {wp.step_name}: {wp.average_score}分 ({wp.severity})")
    
    # 检查紧急包扎环节
    bandaging_wp = next((wp for wp in weak_points if "包扎" in wp.step_name), None)
    assert bandaging_wp is not None, "应该识别出紧急包扎为薄弱点"
    
    print("✓ 薄弱点诊断测试通过")
    return True


def test_relearning_request():
    """测试重学申请创建"""
    print("\n=== 测试重学申请创建 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine, RelearningStatus
    
    engine = AdaptiveFeedbackEngine()
    
    # 获取数据并诊断
    performances = engine.fetch_trainee_scores("trainee_demo_001")
    weak_points = engine.diagnose_weak_points(performances)
    
    # 创建重学申请
    request = engine.create_relearning_request(
        trainee_id="trainee_demo_001",
        course_id="childcare_first_aid",
        assessment_id="assessment_mock_001",
        weak_points=weak_points
    )
    
    assert request is not None, "应该成功创建重学申请"
    assert request.status == RelearningStatus.PENDING, "状态应该是待处理"
    assert len(request.weak_points) == len(weak_points), "薄弱点数量应该一致"
    
    print(f"  请求ID: {request.request_id}")
    print(f"  状态: {request.status.value}")
    print(f"  薄弱点数: {len(request.weak_points)}")
    
    print("✓ 重学申请创建测试通过")
    return True


def test_material_generation():
    """测试材料生成"""
    print("\n=== 测试材料生成 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine
    
    engine = AdaptiveFeedbackEngine()
    
    # 完整流程
    performances = engine.fetch_trainee_scores("trainee_demo_001")
    weak_points = engine.diagnose_weak_points(performances)
    request = engine.create_relearning_request(
        trainee_id="trainee_demo_001",
        course_id="childcare_first_aid",
        assessment_id="assessment_mock_001",
        weak_points=weak_points
    )
    
    # 生成材料（不生成视频）
    result = engine.generate_reinforcement_material(
        request,
        generate_video=False
    )
    
    assert result["success"], "材料生成应该成功"
    print(f"  生成材料数: {len(result['materials'])}")
    
    if result["materials"]:
        for mat in result["materials"]:
            print(f"    - {mat['weak_point']}: {mat['filepath']}")
    
    print("✓ 材料生成测试通过")
    return True


def test_full_feedback_loop():
    """测试完整闭环"""
    print("\n=== 测试完整闭环 ===")
    from adaptive_feedback import AdaptiveFeedbackEngine
    
    engine = AdaptiveFeedbackEngine()
    
    result = engine.run_feedback_loop(
        trainee_id="trainee_demo_001",
        course_id="childcare_first_aid",
        generate_video=False
    )
    
    assert result["success"], "闭环执行应该成功"
    assert len(result["weak_points"]) > 0, "应该发现薄弱点"
    
    print(f"  薄弱点: {len(result['weak_points'])}")
    print(f"  生成材料: {len(result['generated_materials'])}")
    print(f"  成功: {result['success']}")
    
    print("✓ 完整闭环测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("          Adaptive Feedback 功能测试")
    print("=" * 60)
    
    tests = [
        ("模块导入", test_basic_import),
        ("StepScore 模型", test_step_score),
        ("TraineePerformance 模型", test_trainee_performance),
        ("引擎初始化", test_engine_initialization),
        ("模拟数据获取", test_mock_data_fetching),
        ("薄弱点诊断", test_weak_point_diagnosis),
        ("重学申请创建", test_relearning_request),
        ("材料生成", test_material_generation),
        ("完整闭环", test_full_feedback_loop),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name} 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r, _ in results if r)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ 通过" if result else f"✗ 失败: {error}"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
