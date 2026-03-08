#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课件生成服务 (Course Generator Service)
端口: 8001

基于AI的智能课件生成服务，支持：
1. 基于知识点的课件自动生成
2. 多格式输出（PPT、PDF、Markdown）
3. 模板化课件设计
4. 个性化内容适配

作者: SmartCourseEngine Team
日期: 2026-03-07
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

# ============================================================================
# 配置和路径设置
# ============================================================================

# 获取项目根目录
project_root = Path(__file__).parent.parent
shared_path = project_root / "shared"

# 添加路径到sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(shared_path))

print(f"项目根目录: {project_root}")
print(f"共享模块路径: {shared_path}")

# ============================================================================
# 导入共享模块
# ============================================================================

try:
    from shared.api_response import (
        ApiResponse,
        success_response,
        error_response,
        ErrorCode,
    )
    from shared.config import get_settings
    from shared.database import get_db, DatabaseManager
    from shared.models import Course, KnowledgePoint, User
    from shared.auth import get_current_user
    API_RESPONSE_ENABLED = True
    print("✅ 共享模块导入成功")
except ImportError as e:
    print(f"⚠️  共享模块导入失败: {e}")
    API_RESPONSE_ENABLED = False
    
    # 创建简化版本
    class ErrorCode:
        UNKNOWN_ERROR = ("0000", "未知错误")
        VALIDATION_ERROR = ("0001", "参数验证失败")
        DATABASE_ERROR = ("0002", "数据库错误")
        RESOURCE_NOT_FOUND = ("0005", "资源不存在")
        GENERATION_FAILED = ("8001", "课件生成失败")
        TEMPLATE_NOT_FOUND = ("8002", "模板不存在")
    
    def success_response(data: Any = None, message: str = "操作成功"):
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def error_response(
        error_code: ErrorCode,
        message: str = "操作失败",
        details: Dict[str, Any] = None
    ):
        return {
            "success": False,
            "message": message,
            "error_code": error_code[0],
            "error_message": error_code[1],
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# 数据模型
# ============================================================================

class CourseGenerationRequest(BaseModel):
    """课件生成请求"""
    course_id: int = Field(..., description="课程ID")
    template_id: Optional[Any] = Field(None, description="模板ID (int 或 string)")
    format: str = Field("ppt", description="输出格式: ppt, pdf, markdown")
    output_format: Optional[str] = Field(None, description="输出格式别名")
    knowledge_points: Optional[List[Dict[str, Any]]] = Field(None, description="知识点列表")
    include_video_summary: bool = Field(True, description="是否包含视频摘要")
    include_knowledge_graph: bool = Field(True, description="是否包含知识图谱")
    include_exercises: bool = Field(False, description="是否包含练习题")
    custom_prompt: Optional[str] = Field(None, description="自定义生成提示")

    def get_format(self) -> str:
        return self.output_format or self.format

class Template(BaseModel):
    """课件模板"""
    id: int
    name: str
    description: str
    style: str  # professional, academic, creative, minimal
    sections: List[str]  # 包含的章节
    created_at: datetime
    updated_at: datetime

class GeneratedCourse(BaseModel):
    """生成的课件"""
    id: int
    course_id: int
    template_id: Optional[int]
    format: str
    file_path: str
    file_size: int
    generation_time: float  # 生成耗时（秒）
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: Optional[datetime]

# ============================================================================
# 服务配置
# ============================================================================

settings = get_settings()
SERVICE_NAME = "course-generator"
SERVICE_PORT = 8001

# ============================================================================
# 生命周期管理
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"🚀 启动 {SERVICE_NAME} 服务，端口: {SERVICE_PORT}")
    
    # 启动时初始化
    print("📦 初始化课件生成服务...")
    
    # 创建必要的目录
    os.makedirs("generated_courses", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # 加载默认模板
    await load_default_templates()
    
    yield
    
    # 关闭时清理
    print(f"👋 关闭 {SERVICE_NAME} 服务")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="课件生成服务",
    description="基于AI的智能课件生成服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 模板管理
# ============================================================================

TEMPLATES: Dict[int, Template] = {}

async def load_default_templates():
    """加载默认模板"""
    default_templates = [
        {
            "id": 1,
            "name": "专业演示模板",
            "description": "适用于商业演示的专业模板",
            "style": "professional",
            "sections": ["封面", "目录", "课程介绍", "知识点讲解", "案例分析", "总结", "Q&A"]
        },
        {
            "id": 2,
            "name": "学术教学模板",
            "description": "适用于学术教学的详细模板",
            "style": "academic",
            "sections": ["封面", "教学目标", "课程大纲", "理论讲解", "实例分析", "练习题", "参考文献"]
        },
        {
            "id": 3,
            "name": "创意设计模板",
            "description": "具有创意设计的现代模板",
            "style": "creative",
            "sections": ["创意封面", "课程亮点", "视觉化内容", "互动环节", "总结回顾"]
        },
        {
            "id": 4,
            "name": "简洁大纲模板",
            "description": "简洁的内容大纲模板",
            "style": "minimal",
            "sections": ["标题", "核心内容", "关键要点", "行动建议"]
        }
    ]
    
    for template_data in default_templates:
        template = Template(
            **template_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        TEMPLATES[template.id] = template
    
    print(f"📄 加载了 {len(TEMPLATES)} 个默认模板")

# ============================================================================
# 课件生成逻辑
# ============================================================================

async def generate_course_content(course_id: int, template: Template, format: str) -> Dict[str, Any]:
    """生成课件内容"""
    # 这里应该调用AI模型生成内容
    # 暂时返回模拟数据
    
    return {
        "title": f"课程 {course_id} 的课件",
        "sections": template.sections,
        "content": {
            "cover": f"课程 {course_id} - {template.name}",
            "toc": template.sections,
            "introduction": "这是课程的介绍部分...",
            "main_content": "这是课程的主要内容...",
            "summary": "这是课程的总结部分...",
            "exercises": ["练习题1", "练习题2", "练习题3"] if template.id == 2 else []
        }
    }

async def create_ppt_file(content: Dict[str, Any], output_path: str) -> str:
    """创建PPT文件（模拟）"""
    # 这里应该使用python-pptx等库创建PPT
    # 暂时创建模拟文件
    with open(output_path, "w") as f:
        json.dump(content, f, indent=2, default=str)
    
    return output_path

async def create_pdf_file(content: Dict[str, Any], output_path: str) -> str:
    """创建PDF文件（模拟）"""
    # 这里应该使用reportlab等库创建PDF
    # 暂时创建模拟文件
    with open(output_path, "w") as f:
        json.dump(content, f, indent=2, default=str)
    
    return output_path

async def create_markdown_file(content: Dict[str, Any], output_path: str) -> str:
    """创建Markdown文件（模拟）"""
    # 创建Markdown内容
    md_content = f"# {content['title']}\n\n"
    
    for section in content["sections"]:
        md_content += f"## {section}\n\n"
        if section in content["content"]:
            md_content += f"{content['content'][section]}\n\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return output_path

async def generate_course_worker(generation_id: int, request: CourseGenerationRequest):
    """后台生成课件的工作线程"""
    try:
        print(f"🔄 开始生成课件，ID: {generation_id}")
        
        # 获取模板
        template = TEMPLATES.get(request.template_id or 1)
        if not template:
            template = TEMPLATES[1]  # 使用默认模板
        
        # 生成内容
        content = await generate_course_content(request.course_id, template, request.format)
        
        # 创建输出文件
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"course_{request.course_id}_{timestamp}"
        
        if request.format == "ppt":
            output_path = f"generated_courses/{filename}.json"  # 模拟PPT
            await create_ppt_file(content, output_path)
        elif request.format == "pdf":
            output_path = f"generated_courses/{filename}.json"  # 模拟PDF
            await create_pdf_file(content, output_path)
        else:  # markdown
            output_path = f"generated_courses/{filename}.md"
            await create_markdown_file(content, output_path)
        
        # 获取文件大小
        file_size = os.path.getsize(output_path)
        
        print(f"✅ 课件生成完成: {output_path} ({file_size} bytes)")
        
        # 这里应该将生成结果保存到数据库
        # 暂时返回成功消息
        
    except Exception as e:
        print(f"❌ 课件生成失败: {e}")

# ============================================================================
# API端点
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return success_response({
        "service": SERVICE_NAME,
        "status": "healthy",
        "port": SERVICE_PORT,
        "timestamp": datetime.utcnow().isoformat(),
        "templates_loaded": len(TEMPLATES)
    })

@app.get("/")
async def root():
    """根端点"""
    return success_response({
        "service": SERVICE_NAME,
        "description": "基于AI的智能课件生成服务",
        "version": "1.0.0",
        "endpoints": [
            "/health - 健康检查",
            "/docs - API文档",
            "/templates - 获取模板列表",
            "/generate - 生成课件",
            "/generated/{id} - 获取生成结果"
        ]
    })

@app.get("/templates")
async def get_templates():
    """获取所有模板"""
    templates_list = [template.dict() for template in TEMPLATES.values()]
    return success_response(templates_list, "模板列表获取成功")

@app.get("/templates/{template_id}")
async def get_template(template_id: int):
    """获取特定模板"""
    template = TEMPLATES.get(template_id)
    if not template:
        return error_response(ErrorCode.TEMPLATE_NOT_FOUND, f"模板 {template_id} 不存在")
    
    return success_response(template.dict(), "模板获取成功")

@app.post("/generate", tags=["生成"])
@app.post("/api/v1/courses/{course_id}/generate", tags=["生成"])
async def generate_course(
    request: CourseGenerationRequest,
    background_tasks: BackgroundTasks,
    course_id: Optional[int] = None
):
    """
    生成课件
    支持 POST /generate (ID在Body中) 或 POST /api/v1/courses/{course_id}/generate (ID在路径中)
    """
    try:
        # 确定实际的course_id
        target_course_id = course_id if course_id is not None else request.course_id
        
        # 验证课程是否存在（这里应该查询数据库）
        # 暂时模拟验证
        
        # 生成唯一ID
        generation_id = int(datetime.utcnow().timestamp() * 1000)
        
        # 在后台执行生成任务
        background_tasks.add_task(generate_course_worker, generation_id, request)
        
        return success_response({
            "generation_id": generation_id,
            "course_id": target_course_id,
            "status": "processing",
            "message": "课件生成任务已开始",
            "estimated_time": 30
        }, "课件生成任务已提交")
        
    except Exception as e:
        return error_response(ErrorCode.GENERATION_FAILED, f"课件生成失败: {str(e)}")

@app.get("/generated/{generation_id}")
async def get_generation_result(generation_id: int):
    """获取生成结果（模拟）"""
    # 这里应该从数据库查询生成结果
    # 暂时返回模拟数据
    
    return success_response({
        "generation_id": generation_id,
        "status": "completed",
        "course_id": 1,
        "format": "markdown",
        "file_url": f"/generated_courses/course_1_{generation_id}.md",
        "file_size": 2048,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }, "生成结果获取成功")

@app.get("/courses/{course_id}/generations")
async def get_course_generations(course_id: int):
    """获取课程的所有生成记录（模拟）"""
    # 这里应该从数据库查询
    # 暂时返回模拟数据
    
    generations = [
        {
            "id": 1,
            "course_id": course_id,
            "template_id": 1,
            "format": "markdown",
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }
    ]
    
    return success_response(generations, "生成记录获取成功")

# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 启动 {SERVICE_NAME} 服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info"
    )