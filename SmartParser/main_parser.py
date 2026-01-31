#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartParser - 多模态教学材料智能解析器
=======================================

该程序能够自动监控输入文件夹，将多种格式的教学材料（PDF、Word、视频、音频、图片）
转换为 AI 易读的 Markdown 格式。

功能模块:
    - DocumentParser: PDF/Word 文档解析
    - MediaTranscriber: 视频/音频语音转写
    - ImageOCR: 图片文字识别
    - FileWatcher: 文件监控

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import sys
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import threading
import queue

# 第三方库导入
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.panel import Panel
    from rich.table import Table
    import magic
except ImportError as e:
    print(f"[错误] 缺少依赖库: {e}")
    print("请运行: pip install -r requirements.txt")
    sys.exit(1)

# 初始化 Rich 控制台（用于美化输出）
console = Console()

# ============================================================================
# 日志配置
# ============================================================================
import logging

def setup_logging(log_dir: Path) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_dir: 日志文件存放目录
        
    Returns:
        配置好的 Logger 实例
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"smartparser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 创建日志记录器
    logger = logging.getLogger("SmartParser")
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器（详细日志）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台处理器（使用 Rich 美化）
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True
    )
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# 文档解析器 - 处理 PDF 和 Word 文档
# ============================================================================
class DocumentParser:
    """
    PDF/Word 文档解析器
    
    使用 docling 库将文档转换为 Markdown 格式，
    保留标题层级、表格结构和数学公式。
    """
    
    def __init__(self, logger: logging.Logger):
        """
        初始化文档解析器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger
        self._docling_available = False
        self._init_docling()
    
    def _init_docling(self):
        """初始化 docling 库"""
        try:
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()
            self._docling_available = True
            self.logger.info("[green]✓[/green] Docling 文档解析器初始化成功")
        except ImportError:
            self.logger.warning("[yellow]⚠[/yellow] Docling 未安装，文档解析功能不可用")
        except Exception as e:
            self.logger.error(f"[red]✗[/red] Docling 初始化失败: {e}")
    
    def parse(self, file_path: Path) -> Optional[str]:
        """
        解析 PDF 或 Word 文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            转换后的 Markdown 文本，失败返回 None
        """
        if not self._docling_available:
            self.logger.error("Docling 不可用，无法解析文档")
            return None
        
        try:
            self.logger.info(f"正在解析文档: {file_path.name}")
            
            # 使用 docling 转换文档
            result = self.converter.convert(str(file_path))
            markdown_content = result.document.export_to_markdown()
            
            # 添加元信息头部
            header = self._generate_header(file_path, "文档")
            full_content = header + markdown_content
            
            self.logger.info(f"[green]✓[/green] 文档解析完成: {file_path.name}")
            return full_content
            
        except Exception as e:
            self.logger.error(f"[red]✗[/red] 文档解析失败 [{file_path.name}]: {e}")
            return None
    
    def _generate_header(self, file_path: Path, doc_type: str) -> str:
        """生成 Markdown 元信息头部"""
        return f"""# {doc_type}解析：{file_path.name}

**原始文件：** {file_path.name}
**文件大小：** {file_path.stat().st_size / 1024:.2f} KB
**解析时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""


# ============================================================================
# 媒体转写器 - 处理视频和音频文件
# ============================================================================
class MediaTranscriber:
    """
    视频/音频转写器
    
    使用 faster-whisper 模型将语音转换为带时间戳的文本。
    支持 mp4, avi, mkv, mp3, wav, m4a 等格式。
    """
    
    def __init__(self, logger: logging.Logger, model_size: str = "small"):
        """
        初始化媒体转写器
        
        Args:
            logger: 日志记录器
            model_size: Whisper 模型大小 (tiny/base/small/medium/large)
        """
        self.logger = logger
        self.model_size = model_size
        self._whisper_available = False
        self._model = None
        self._init_whisper()
    
    def _init_whisper(self):
        """初始化 faster-whisper 模型"""
        try:
            from faster_whisper import WhisperModel
            
            self.logger.info(f"正在加载 Whisper {self.model_size} 模型（首次加载需要下载）...")
            
            # 尝试使用 GPU，如果不可用则使用 CPU
            try:
                self._model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                self.logger.info("[green]✓[/green] Whisper 模型已加载 (GPU 模式)")
            except Exception:
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                self.logger.info("[green]✓[/green] Whisper 模型已加载 (CPU 模式)")
            
            self._whisper_available = True
            
        except ImportError:
            self.logger.warning("[yellow]⚠[/yellow] faster-whisper 未安装，语音转写功能不可用")
        except Exception as e:
            self.logger.error(f"[red]✗[/red] Whisper 初始化失败: {e}")
    
    def transcribe(self, file_path: Path) -> Optional[str]:
        """
        转写音频/视频文件
        
        Args:
            file_path: 媒体文件路径
            
        Returns:
            带时间戳的 Markdown 文本，失败返回 None
        """
        if not self._whisper_available:
            self.logger.error("Whisper 不可用，无法转写音频")
            return None
        
        try:
            self.logger.info(f"正在转写: {file_path.name}")
            
            # 如果是视频，先提取音频
            audio_path = file_path
            temp_audio = None
            
            if file_path.suffix.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
                audio_path, temp_audio = self._extract_audio(file_path)
                if audio_path is None:
                    return None
            
            # 执行转写
            segments, info = self._model.transcribe(
                str(audio_path),
                language="zh",  # 中文优先
                beam_size=5,
                vad_filter=True  # 语音活动检测，过滤静音
            )
            
            # 格式化输出
            duration = self._format_duration(info.duration)
            lines = []
            
            for segment in segments:
                timestamp = self._format_timestamp(segment.start)
                lines.append(f"[{timestamp}] {segment.text.strip()}")
            
            # 清理临时文件
            if temp_audio and temp_audio.exists():
                temp_audio.unlink()
            
            # 生成完整 Markdown
            content = self._generate_transcription_markdown(file_path, duration, lines)
            
            self.logger.info(f"[green]✓[/green] 转写完成: {file_path.name}")
            return content
            
        except Exception as e:
            self.logger.error(f"[red]✗[/red] 转写失败 [{file_path.name}]: {e}")
            return None
    
    def _extract_audio(self, video_path: Path) -> tuple:
        """从视频中提取音频"""
        try:
            from moviepy.editor import VideoFileClip
            
            temp_audio = video_path.parent / f"_temp_{video_path.stem}.wav"
            
            self.logger.info(f"正在从视频提取音频...")
            video = VideoFileClip(str(video_path))
            video.audio.write_audiofile(str(temp_audio), verbose=False, logger=None)
            video.close()
            
            return temp_audio, temp_audio
            
        except Exception as e:
            self.logger.error(f"音频提取失败: {e}")
            return None, None
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳 (秒 -> MM:SS 或 HH:MM:SS)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    def _format_duration(self, seconds: float) -> str:
        """格式化总时长"""
        return self._format_timestamp(seconds)
    
    def _generate_transcription_markdown(self, file_path: Path, duration: str, lines: list) -> str:
        """生成转写结果的 Markdown 格式"""
        return f"""# 音视频转写：{file_path.name}

**原始文件：** {file_path.name}
**时长：** {duration}
**转写时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{chr(10).join(lines)}
"""


# ============================================================================
# 图片 OCR - 识别图片中的文字
# ============================================================================
class ImageOCR:
    """
    图片文字识别器
    
    使用 PaddleOCR 提取图片中的文字，对中文有良好支持。
    """
    
    def __init__(self, logger: logging.Logger):
        """
        初始化图片 OCR
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger
        self._ocr_available = False
        self._ocr = None
        self._init_ocr()
    
    def _init_ocr(self):
        """初始化 PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            
            # 初始化 PaddleOCR，使用中文模型，禁用 GPU 以提高兼容性
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
            self._ocr_available = True
            self.logger.info("[green]✓[/green] PaddleOCR 初始化成功")
            
        except ImportError:
            self.logger.warning("[yellow]⚠[/yellow] PaddleOCR 未安装，图片 OCR 功能不可用")
        except Exception as e:
            self.logger.error(f"[red]✗[/red] PaddleOCR 初始化失败: {e}")
    
    def recognize(self, file_path: Path) -> Optional[str]:
        """
        识别图片中的文字
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            识别结果的 Markdown 文本，失败返回 None
        """
        if not self._ocr_available:
            self.logger.error("PaddleOCR 不可用，无法识别图片")
            return None
        
        try:
            self.logger.info(f"正在识别图片: {file_path.name}")
            
            # 执行 OCR
            result = self._ocr.ocr(str(file_path), cls=True)
            
            if result is None or len(result) == 0 or result[0] is None:
                self.logger.warning(f"图片中未识别到文字: {file_path.name}")
                text_content = "（未识别到文字内容）"
            else:
                # 提取识别的文本 (PaddleOCR 返回格式: [[[坐标], (文字, 置信度)], ...])
                text_lines = []
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_lines.append(line[1][0])  # 提取文字内容
                text_content = "\n".join(text_lines)
            
            # 生成 Markdown
            content = self._generate_ocr_markdown(file_path, text_content)
            
            self.logger.info(f"[green]✓[/green] 图片识别完成: {file_path.name}")
            return content
            
        except Exception as e:
            self.logger.error(f"[red]✗[/red] 图片识别失败 [{file_path.name}]: {e}")
            return None
    
    def _generate_ocr_markdown(self, file_path: Path, text_content: str) -> str:
        """生成 OCR 结果的 Markdown 格式"""
        return f"""# 图片文字识别：{file_path.name}

**原始文件：** {file_path.name}
**文件大小：** {file_path.stat().st_size / 1024:.2f} KB
**识别时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{text_content}
"""


# ============================================================================
# 文件监控器 - 监听输入文件夹
# ============================================================================
class FileWatcher(FileSystemEventHandler):
    """
    文件监控器
    
    监听指定文件夹，当有新文件创建时触发处理回调。
    """
    
    def __init__(self, callback: Callable, logger: logging.Logger):
        """
        初始化文件监控器
        
        Args:
            callback: 文件处理回调函数
            logger: 日志记录器
        """
        super().__init__()
        self.callback = callback
        self.logger = logger
        self._processing = set()  # 正在处理的文件
        self._lock = threading.Lock()
    
    def on_created(self, event):
        """文件创建事件处理"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # 忽略临时文件和隐藏文件
        if file_path.name.startswith('.') or file_path.name.startswith('_temp'):
            return
        
        # 等待文件写入完成
        time.sleep(1)
        
        # 防止重复处理
        with self._lock:
            if str(file_path) in self._processing:
                return
            self._processing.add(str(file_path))
        
        try:
            self.callback(file_path)
        finally:
            with self._lock:
                self._processing.discard(str(file_path))


# ============================================================================
# SmartParser 主类
# ============================================================================
class SmartParser:
    """
    SmartParser 主解析器
    
    整合所有解析模块，提供统一的文件处理接口。
    """
    
    # 支持的文件类型映射
    FILE_TYPES = {
        'document': ['.pdf', '.docx', '.doc'],
        'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
        'image': ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
    }
    
    def __init__(self, input_dir: str = "input_materials", output_dir: str = "output_markdown"):
        """
        初始化 SmartParser
        
        Args:
            input_dir: 输入文件夹名称
            output_dir: 输出文件夹名称
        """
        # 设置路径
        self.base_dir = Path(__file__).parent
        self.input_dir = self.base_dir / input_dir
        self.output_dir = self.base_dir / output_dir
        self.log_dir = self.base_dir / "logs"
        
        # 创建必要的目录
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志
        self.logger = setup_logging(self.log_dir)
        
        # 初始化各解析模块
        self.doc_parser = DocumentParser(self.logger)
        self.media_transcriber = MediaTranscriber(self.logger, model_size="small")
        self.image_ocr = ImageOCR(self.logger)
        
        # 处理队列
        self.queue = queue.Queue()
        
        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0
        }
    
    def get_file_type(self, file_path: Path) -> Optional[str]:
        """
        检测文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件类型 (document/audio/video/image) 或 None
        """
        suffix = file_path.suffix.lower()
        
        for file_type, extensions in self.FILE_TYPES.items():
            if suffix in extensions:
                return file_type
        
        return None
    
    def process_file(self, file_path: Path):
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
        """
        self.stats['total'] += 1
        
        # 检测文件类型
        file_type = self.get_file_type(file_path)
        
        if file_type is None:
            self.logger.warning(f"[yellow]⚠[/yellow] 不支持的文件类型: {file_path.name}")
            self.stats['failed'] += 1
            return
        
        self.logger.info(f"[blue]→[/blue] 开始处理 [{file_type}]: {file_path.name}")
        
        # 根据文件类型调用对应的解析器
        result = None
        
        if file_type == 'document':
            result = self.doc_parser.parse(file_path)
        elif file_type in ['audio', 'video']:
            result = self.media_transcriber.transcribe(file_path)
        elif file_type == 'image':
            result = self.image_ocr.recognize(file_path)
        
        # 保存结果
        if result:
            output_path = self.output_dir / f"{file_path.stem}.md"
            output_path.write_text(result, encoding='utf-8')
            self.logger.info(f"[green]✓[/green] 已保存: {output_path.name}")
            self.stats['success'] += 1
        else:
            self.stats['failed'] += 1
    
    def process_existing_files(self):
        """处理输入文件夹中已存在的文件"""
        existing_files = list(self.input_dir.iterdir())
        file_count = len([f for f in existing_files if f.is_file()])
        
        if file_count > 0:
            self.logger.info(f"发现 {file_count} 个已存在的文件，开始处理...")
            
            for file_path in existing_files:
                if file_path.is_file() and not file_path.name.startswith('.'):
                    self.process_file(file_path)
    
    def start_watching(self):
        """启动文件监控"""
        # 显示启动信息
        self._show_startup_banner()
        
        # 处理已存在的文件
        self.process_existing_files()
        
        # 设置文件监控
        event_handler = FileWatcher(self.process_file, self.logger)
        observer = Observer()
        observer.schedule(event_handler, str(self.input_dir), recursive=False)
        observer.start()
        
        self.logger.info(f"[green]●[/green] 正在监听文件夹: {self.input_dir}")
        self.logger.info("[dim]按 Ctrl+C 停止程序[/dim]")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("\n[yellow]正在停止...[/yellow]")
            observer.stop()
        
        observer.join()
        
        # 显示统计信息
        self._show_stats()
    
    def _show_startup_banner(self):
        """显示启动横幅"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║           SmartParser - 多模态教学材料解析器              ║
║                                                           ║
║  支持格式:                                                ║
║    📄 文档: PDF, Word (.docx, .doc)                       ║
║    🎵 音频: MP3, WAV, M4A, FLAC                           ║
║    🎬 视频: MP4, AVI, MKV, MOV                            ║
║    🖼️  图片: PNG, JPG, BMP, GIF                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(Panel(banner, style="blue"))
        console.print(f"[dim]输入文件夹: {self.input_dir}[/dim]")
        console.print(f"[dim]输出文件夹: {self.output_dir}[/dim]")
        console.print()
    
    def _show_stats(self):
        """显示处理统计"""
        table = Table(title="处理统计")
        table.add_column("指标", style="cyan")
        table.add_column("数量", style="magenta")
        
        table.add_row("总文件数", str(self.stats['total']))
        table.add_row("成功", str(self.stats['success']))
        table.add_row("失败", str(self.stats['failed']))
        
        console.print(table)


# ============================================================================
# 程序入口
# ============================================================================
def main():
    """程序主入口"""
    try:
        parser = SmartParser()
        parser.start_watching()
    except Exception as e:
        console.print(f"[red]程序运行出错: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
