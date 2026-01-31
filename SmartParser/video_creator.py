#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成器 (Video Creator)
==========================

调用数字人 API 将教学脚本转化为视频。
支持 HeyGen 和 D-ID API。

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Rich 美化输出
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

console = Console()

# ============================================================================
# API 配置 - 请在此处配置您的 API 密钥
# ============================================================================

# HeyGen API (推荐)
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "your-heygen-api-key-here")
HEYGEN_API_BASE = "https://api.heygen.com/v2"

# D-ID API (备选)
DID_API_KEY = os.getenv("DID_API_KEY", "your-did-api-key-here")
DID_API_BASE = "https://api.d-id.com"

# 默认配置
DEFAULT_AVATAR_ID = os.getenv("DEFAULT_AVATAR_ID", "Kristin_public_2_20240108")
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID", "zh-CN-XiaoxiaoNeural")

# 文本长度限制 (字符数)
MAX_TEXT_LENGTH = 1500  # HeyGen 单次请求限制


# ============================================================================
# 视频创建器 - HeyGen 实现
# ============================================================================
class HeyGenVideoCreator:
    """
    HeyGen 视频创建器
    
    使用 HeyGen API 将文本转换为数字人视频。
    """
    
    def __init__(
        self,
        api_key: str = HEYGEN_API_KEY,
        avatar_id: str = DEFAULT_AVATAR_ID,
        voice_id: str = DEFAULT_VOICE_ID
    ):
        """
        初始化 HeyGen 视频创建器
        
        Args:
            api_key: HeyGen API 密钥
            avatar_id: 数字人形象 ID
            voice_id: 语音 ID
        """
        self.api_key = api_key
        self.avatar_id = avatar_id
        self.voice_id = voice_id
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def create_video(self, text: str, title: str = "video") -> Optional[str]:
        """
        创建视频
        
        Args:
            text: 讲解文本
            title: 视频标题
            
        Returns:
            视频任务 ID，失败返回 None
        """
        url = f"{HEYGEN_API_BASE}/video/generate"
        
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": self.avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": text,
                    "voice_id": self.voice_id
                }
            }],
            "dimension": {
                "width": 1280,
                "height": 720
            },
            "title": title
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            video_id = data.get("data", {}).get("video_id")
            
            if video_id:
                console.print(f"[green]✓[/green] 视频任务已创建: {video_id}")
                return video_id
            else:
                console.print(f"[red]✗[/red] 创建失败: {data}")
                return None
                
        except requests.exceptions.Timeout as e:
            console.print(f"[red]✗[/red] API 请求超时: {e}")
            console.print(f"[yellow]提示:[/yellow] HeyGen API 响应较慢,请稍后重试")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] API 请求失败: {e}")
            # 输出详细的错误信息
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    console.print(f"[red]错误详情:[/red] {error_data}")
                except:
                    console.print(f"[red]响应内容:[/red] {e.response.text}")
                console.print(f"[yellow]请求 URL:[/yellow] {url}")
                console.print(f"[yellow]请求头:[/yellow] {self.headers}")
                console.print(f"[yellow]请求体:[/yellow] {payload}")
            return None
    
    def check_status(self, video_id: str) -> Tuple[str, Optional[str]]:
        """
        检查视频生成状态
        
        Args:
            video_id: 视频任务 ID
            
        Returns:
            (状态, 视频URL)
        """
        url = f"{HEYGEN_API_BASE}/video_status.get?video_id={video_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            status = data.get("data", {}).get("status", "unknown")
            video_url = data.get("data", {}).get("video_url")
            
            return status, video_url
            
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]⚠[/yellow] 状态查询失败: {e}")
            return "error", None
    
    def wait_for_completion(
        self,
        video_id: str,
        interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Optional[str]:
        """
        等待视频生成完成
        
        Args:
            video_id: 视频任务 ID
            interval: 轮询间隔（秒）
            timeout: 超时时间（秒）
            progress_callback: 进度回调函数
            
        Returns:
            视频 URL，超时返回 None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status, video_url = self.check_status(video_id)
            
            elapsed = int(time.time() - start_time)
            
            if progress_callback:
                progress_callback(status, elapsed)
            
            if status == "completed":
                console.print(f"[green]✓[/green] 视频生成完成！")
                return video_url
            elif status == "failed":
                console.print(f"[red]✗[/red] 视频生成失败")
                return None
            elif status == "processing":
                console.print(f"[dim]进度: {status} ({elapsed}s)[/dim]")
            
            time.sleep(interval)
        
        console.print(f"[red]✗[/red] 生成超时")
        return None
    
    def download_video(self, video_url: str, output_path: str) -> bool:
        """
        下载视频文件
        
        Args:
            video_url: 视频 URL
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            console.print(f"[green]✓[/green] 视频已保存: {output_path}")
            return True
            
        except Exception as e:
            console.print(f"[red]✗[/red] 下载失败: {e}")
            return False


# ============================================================================
# 视频创建器 - D-ID 实现
# ============================================================================
class DIDVideoCreator:
    """
    D-ID 视频创建器
    
    使用 D-ID API 将文本转换为数字人视频。
    """
    
    def __init__(
        self,
        api_key: str = DID_API_KEY,
        avatar_id: str = "amy-jcwCkr1grs"
    ):
        """初始化 D-ID 视频创建器"""
        self.api_key = api_key
        self.avatar_id = avatar_id
        self.headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, text: str, title: str = "video") -> Optional[str]:
        """创建视频"""
        url = f"{DID_API_BASE}/talks"
        
        payload = {
            "source_url": f"https://d-id-public-bucket.s3.us-west-2.amazonaws.com/alice.jpg",
            "script": {
                "type": "text",
                "input": text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "zh-CN-XiaoxiaoNeural"
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            talk_id = data.get("id")
            
            if talk_id:
                console.print(f"[green]✓[/green] D-ID 任务已创建: {talk_id}")
                return talk_id
            return None
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗[/red] D-ID API 请求失败: {e}")
            return None
    
    def check_status(self, talk_id: str) -> Tuple[str, Optional[str]]:
        """检查视频状态"""
        url = f"{DID_API_BASE}/talks/{talk_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            status = data.get("status", "unknown")
            video_url = data.get("result_url")
            
            return status, video_url
            
        except requests.exceptions.RequestException as e:
            return "error", None
    
    def wait_for_completion(
        self,
        talk_id: str,
        interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Optional[str]:
        """等待视频生成完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status, video_url = self.check_status(talk_id)
            
            elapsed = int(time.time() - start_time)
            
            if progress_callback:
                progress_callback(status, elapsed)
            
            if status == "done":
                return video_url
            elif status == "error":
                return None
            
            time.sleep(interval)
        
        return None
    
    def download_video(self, video_url: str, output_path: str) -> bool:
        """下载视频"""
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            console.print(f"[red]✗[/red] 下载失败: {e}")
            return False


# ============================================================================
# 通用视频创建器
# ============================================================================
class VideoCreator:
    """
    通用视频创建器
    
    自动选择可用的 API 并处理脚本拆分。
    """
    
    def __init__(self, provider: str = "heygen", api_key: str = None, avatar_id: str = None, voice_id: str = None):
        """
        初始化视频创建器
        
        Args:
            provider: API 提供商 ("heygen" 或 "did")
            api_key: API 密钥 (如果不提供,将从环境变量读取)
            avatar_id: 数字人形象 ID (可选)
            voice_id: 语音 ID (可选)
        """
        self.provider = provider.lower()
        
        if self.provider == "heygen":
            # 动态获取 API 密钥
            resolved_key = api_key or os.getenv("HEYGEN_API_KEY", HEYGEN_API_KEY)
            resolved_avatar = avatar_id or DEFAULT_AVATAR_ID
            resolved_voice = voice_id or DEFAULT_VOICE_ID
            self.creator = HeyGenVideoCreator(
                api_key=resolved_key,
                avatar_id=resolved_avatar,
                voice_id=resolved_voice
            )
        else:
            resolved_key = api_key or os.getenv("DID_API_KEY", DID_API_KEY)
            self.creator = DIDVideoCreator(api_key=resolved_key)
        
        # 输出目录
        self.output_dir = Path(__file__).parent / "output_videos"
        self.output_dir.mkdir(exist_ok=True)
    
    def split_text(self, text: str, max_length: int = MAX_TEXT_LENGTH) -> List[str]:
        """
        智能拆分文本
        
        按句号拆分长文本，确保每段不超过限制。
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            拆分后的文本列表
        """
        if len(text) <= max_length:
            return [text]
        
        # 按句号拆分
        sentences = re.split(r'([。！？.!?])', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # 添加标点
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        console.print(f"[blue]→[/blue] 文本已拆分为 {len(chunks)} 个片段")
        return chunks
    
    def create_video_from_script(
        self,
        script: str,
        title: str = "课程视频",
        progress_callback=None
    ) -> List[str]:
        """
        从脚本创建视频
        
        Args:
            script: 讲解脚本
            title: 视频标题
            progress_callback: 进度回调 (status, elapsed, part, total)
            
        Returns:
            生成的视频文件路径列表
        """
        # 检查 API Key
        if self.provider == "heygen":
            if not self.creator.api_key or self.creator.api_key == "your-heygen-api-key-here":
                console.print("[red]✗ 错误：未配置 HEYGEN_API_KEY[/red]")
                console.print("[yellow]提示:[/yellow] 请在初始化 VideoCreator 时传入 api_key 参数")
                return []
        elif self.provider == "did":
            if not self.creator.api_key or self.creator.api_key == "your-did-api-key-here":
                console.print("[red]✗ 错误：未配置 DID_API_KEY[/red]")
                console.print("[yellow]提示:[/yellow] 请在初始化 VideoCreator 时传入 api_key 参数")
                return []
        
        # 清理脚本（移除画面建议标注）
        clean_script = re.sub(r'【画面建议】[^【]*', '', script)
        clean_script = re.sub(r'\n{3,}', '\n\n', clean_script)
        
        # 拆分文本
        chunks = self.split_text(clean_script)
        
        video_paths = []
        
        console.print(Panel(f"开始生成视频: {title}", style="blue"))
        
        for i, chunk in enumerate(chunks):
            part_num = i + 1
            console.print(f"\n[blue]→[/blue] 处理片段 {part_num}/{len(chunks)}")
            
            # 创建视频任务
            video_id = self.creator.create_video(chunk, f"{title}_Part{part_num}")
            
            if not video_id:
                console.print(f"[yellow]⚠[/yellow] 片段 {part_num} 创建失败，跳过")
                continue
            
            # 定义进度回调包装
            def wrapped_callback(status, elapsed):
                if progress_callback:
                    progress_callback(status, elapsed, part_num, len(chunks))
            
            # 等待完成
            video_url = self.creator.wait_for_completion(
                video_id,
                interval=10,
                progress_callback=wrapped_callback
            )
            
            if video_url:
                # 生成文件名
                safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
                
                if len(chunks) > 1:
                    filename = f"{safe_title}_Part{part_num}.mp4"
                else:
                    filename = f"{safe_title}.mp4"
                
                output_path = self.output_dir / filename
                
                # 下载视频
                if self.creator.download_video(video_url, str(output_path)):
                    video_paths.append(str(output_path))
        
        return video_paths
    
    def create_from_courseware(
        self,
        courseware: Dict,
        progress_callback=None
    ) -> List[str]:
        """
        从课件数据生成视频
        
        Args:
            courseware: content_generator 生成的课件数据
            progress_callback: 进度回调
            
        Returns:
            生成的视频文件路径列表
        """
        topic = courseware.get("topic", "课程视频")
        
        # 优先使用 audio_scripts，如果没有则使用 scripts
        scripts = courseware.get("audio_scripts", [])
        if not scripts:
            scripts = courseware.get("scripts", [])
            console.print("[dim]使用 scripts 作为视频脚本源[/dim]")
        
        if not scripts:
            console.print("[yellow]⚠ 课件中没有可用的脚本[/yellow]")
            console.print(f"[dim]课件数据键: {list(courseware.keys())}[/dim]")
            return []
        
        console.print(f"[green]✓[/green] 找到 {len(scripts)} 个脚本片段")
        
        # 合并所有脚本
        full_script = "\n\n".join([
            f"【{s.get('section', '')}】\n{s.get('content', '')}"
            for s in scripts if s.get('content')
        ])
        
        if not full_script.strip():
            console.print("[yellow]⚠ 脚本内容为空[/yellow]")
            return []
        
        console.print(f"[dim]脚本总长度: {len(full_script)} 字符[/dim]")
        
        return self.create_video_from_script(
            full_script,
            title=topic,
            progress_callback=progress_callback
        )


# ============================================================================
# CLI 入口
# ============================================================================
def main():
    """主入口函数"""
    console.print(Panel("""
╔═══════════════════════════════════════════════════════════╗
║          Video Creator - 数字人视频生成器                 ║
║                                                           ║
║  将教学脚本自动转化为数字人讲解视频                       ║
╚═══════════════════════════════════════════════════════════╝
    """, style="blue"))
    
    # 检查 API Key
    if HEYGEN_API_KEY == "your-heygen-api-key-here":
        console.print("[yellow]⚠ 提示：未配置 HEYGEN_API_KEY[/yellow]")
        console.print("[dim]请设置环境变量: $env:HEYGEN_API_KEY = 'your-key'[/dim]")
        console.print("[dim]或使用 D-ID: $env:DID_API_KEY = 'your-key'[/dim]\n")
    
    # 示例使用
    from rich.prompt import Prompt
    
    # 获取输入
    script_text = Prompt.ask(
        "[bold blue]请输入讲解脚本（或输入文件路径）[/bold blue]",
        default="这是一段测试文本，用于演示视频生成功能。"
    )
    
    # 检查是否是文件路径
    script_path = Path(script_text)
    if script_path.exists() and script_path.suffix == ".md":
        script_text = script_path.read_text(encoding='utf-8')
        console.print(f"[green]✓[/green] 已加载文件: {script_path.name}")
    
    title = Prompt.ask("[bold blue]视频标题[/bold blue]", default="测试视频")
    
    # 创建视频
    creator = VideoCreator(provider="heygen")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("生成视频中...", total=None)
        
        def update_progress(status, elapsed, part=1, total=1):
            progress.update(task, description=f"[{part}/{total}] {status} ({elapsed}s)")
        
        videos = creator.create_video_from_script(
            script_text,
            title=title,
            progress_callback=update_progress
        )
    
    if videos:
        console.print("\n[green]✓ 视频生成完成！[/green]")
        for v in videos:
            console.print(f"  → {v}")
    else:
        console.print("\n[yellow]⚠ 未生成任何视频[/yellow]")


if __name__ == "__main__":
    main()
