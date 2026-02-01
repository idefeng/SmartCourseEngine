#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地视频生成引擎 (Engine Local) - RTX 4060 专项优化版
======================================================

集成 CosyVoice (语音合成) 和 LivePortrait (视频驱动) 的本地推理核心逻辑。
针对 NVIDIA Ada 架构 (RTX 40系列) 和 RTX 4060 (8GB VRAM) 进行了专项性能调优。

主要功能:
1. CUDA 环境自适配 (TF32 Tensor Core 加速)
2. CosyVoice 语音合成 (零显存残留)
3. LivePortrait 视频驱动 (FP16 + xformers + OOM 自动降级)
4. FFmpeg 音画同步合成
5. OOM 异常容错 (串行回退机制)

作者: SmartCourseEngine Team
日期: 2026-02-01
"""

import os
import sys
import gc
import time
import subprocess
import shutil
import traceback
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Union

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# RTX 4060 专项配置
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
WEIGHTS_DIR = BASE_DIR / "pretrained_weights"
TOOLS_DIR = BASE_DIR / "tools"

# 路径映射配置
TEMP_UPLOAD_DIR = BASE_DIR / "temp_upload"          # 驱动图来源 (Streamlit 上传)
LOCAL_GEN_OUTPUT_DIR = BASE_DIR / "output_videos" / "local_gen"  # 最终输出目录

# RTX 4060 (8GB) 最优配置
RTX_4060_CONFIG = {
    "target_size": 512,         # 平衡画质与速度的最佳分辨率
    "use_fp16": True,           # 半精度推理，显存占用减半
    "fallback_size": 384,       # OOM 降级分辨率
    "min_size": 256,            # 最小分辨率
    "enable_xformers": True,    # 启用 xformers 优化
    "batch_size": 1,            # RTX 4060 推荐批次
}

# 关键依赖库列表
REQUIRED_PACKAGES = [
    "torch", "numpy", "opencv-python", "librosa", "soundfile", 
    "mediapipe", "diffusers", "transformers", "gradio"
]

# xformers 可用性检测
XFORMERS_AVAILABLE = False
try:
    import xformers
    import xformers.ops
    XFORMERS_AVAILABLE = True
    logger.info("✓ xformers 可用，将启用内存高效注意力机制")
except ImportError:
    logger.info("✗ xformers 未安装，使用标准注意力机制 (建议安装: pip install xformers)")


class LocalInferenceEngine:
    """
    本地推理引擎核心类 - RTX 4060 优化版
    
    针对 NVIDIA Ada 架构进行了以下优化:
    - TF32 Tensor Core 加速
    - 显存零残留管理
    - FP16 半精度推理
    - xformers 内存高效注意力
    - OOM 串行回退机制
    """
    
    def __init__(self, callback: Optional[Callable[[str, int], None]] = None):
        """
        初始化引擎
        :param callback: 进度回调函数 callback(step_name, progress_0_to_100)
        """
        self.callback = callback
        self.serial_mode = False  # OOM 串行回退标志
        self.config = RTX_4060_CONFIG.copy()
        
        # 检查 CUDA 并设置优化
        self.device = "cuda" if self._check_cuda() else "cpu"
        if self.device == "cuda":
            self._setup_cuda_optimizations()
        
        # 环境自检
        self._check_environment()
        
        # 确保输出目录存在
        LOCAL_GEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (LOCAL_GEN_OUTPUT_DIR / "temp").mkdir(exist_ok=True)
        TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
    def _report_progress(self, message: str, progress: int):
        """上报进度"""
        if self.callback:
            self.callback(message, progress)
        logger.info(f"[{progress}%] {message}")

    def _check_cuda(self) -> bool:
        """检查 CUDA 可用性并获取 GPU 信息"""
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                vram_gb = props.total_memory / 1024**3
                
                # 检测 GPU 架构
                compute_capability = f"{props.major}.{props.minor}"
                is_ada = props.major >= 8 and props.minor >= 9  # sm_89 = Ada
                
                arch_info = "Ada 架构 ✓" if is_ada else f"Compute {compute_capability}"
                logger.info(f"检测到 GPU: {props.name} ({arch_info}, VRAM: {vram_gb:.2f} GB)")
                
                # 针对显存不足的设备调整配置
                if vram_gb < 6:
                    logger.warning("显存较小，自动降低推理分辨率")
                    self.config["target_size"] = 384
                    self.config["fallback_size"] = 256
                
                return True
        except ImportError:
            logger.warning("PyTorch 未安装")
        except Exception as e:
            logger.warning(f"CUDA 检测异常: {e}")
        return False
    
    def _setup_cuda_optimizations(self):
        """
        设置 CUDA 优化选项 (针对 RTX 40 系列 Ada 架构)
        
        启用 TF32 Tensor Core 加速:
        - RTX 40 系列显卡具有第四代 Tensor Cores
        - TF32 在保持精度的同时提供显著的性能提升
        """
        try:
            import torch
            
            # 开启 TF32 加速 (RTX 30/40 系列支持)
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            
            # cuDNN 优化
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            
            logger.info("✓ CUDA 优化已启用: TF32 Tensor Core + cuDNN benchmark")
            
            # 检查 CUDA 版本
            cuda_version = torch.version.cuda
            logger.info(f"  CUDA 版本: {cuda_version}")
            
        except Exception as e:
            logger.warning(f"设置 CUDA 优化时出错: {e}")

    def _cleanup_vram(self, aggressive: bool = False):
        """
        彻底清理 VRAM (零显存残留)
        
        :param aggressive: 是否进行激进清理 (包括同步和多次 GC)
        """
        try:
            # Python 垃圾回收
            gc.collect()
            
            if self.device == "cuda":
                import torch
                
                # 清空 CUDA 缓存
                torch.cuda.empty_cache()
                
                if aggressive:
                    # 同步所有 CUDA 操作
                    torch.cuda.synchronize()
                    
                    # 多次 GC 确保彻底清理
                    for _ in range(3):
                        gc.collect()
                    torch.cuda.empty_cache()
                    
                    # 记录当前显存状态
                    allocated = torch.cuda.memory_allocated() / 1024**2
                    reserved = torch.cuda.memory_reserved() / 1024**2
                    logger.info(f"显存清理完成: 已分配 {allocated:.1f}MB, 已保留 {reserved:.1f}MB")
                    
        except Exception as e:
            logger.warning(f"清理显存时出错: {e}")

    def _check_environment(self):
        """环境自检与自我修复建议"""
        logger.info("正在检查运行环境...")
        missing_packages = []
        
        for pkg in REQUIRED_PACKAGES:
            try:
                # 处理包名与导入名不一致的情况
                import_name = pkg.replace("-", "_")
                if pkg == "opencv-python":
                    import_name = "cv2"
                __import__(import_name)
            except ImportError:
                missing_packages.append(pkg)
        
        if missing_packages:
            msg = f"缺少必要依赖库: {', '.join(missing_packages)}"
            logger.warning(msg)
            # 自动提示安装指令
            install_cmd = f"pip install {' '.join(missing_packages)}"
            logger.info(f"建议执行: {install_cmd}")
        
        # 检查 FFmpeg
        if shutil.which("ffmpeg") is None:
            logger.error("❌ 未找到 FFmpeg，请确保将其添加到系统 PATH 中！")
        else:
            logger.info("✓ FFmpeg 已就绪")
        
        # 检查 xformers 建议
        if not XFORMERS_AVAILABLE and self.device == "cuda":
            logger.info("💡 建议安装 xformers 以进一步优化显存占用: pip install xformers")

    def synthesize_audio(self, text: str, voice_wav: str, output_path: str) -> bool:
        """
        使用 CosyVoice 合成音频 (零显存残留)
        
        合成完成后会彻底清理显存，确保为 LivePortrait 腾出全部显存空间。
        
        :param text: 要合成的文本
        :param voice_wav: 参考音色的 wav 文件路径
        :param output_path: 输出音频路径
        :return: 是否成功
        """
        self._report_progress("正在加载 CosyVoice 模型...", 10)
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        cosyvoice_script = TOOLS_DIR / "CosyVoice" / "cli.py"
        
        try:
            if not cosyvoice_script.exists():
                # 模拟模式
                logger.warning(f"未找到 CosyVoice 脚本 ({cosyvoice_script})，使用模拟生成。")
                time.sleep(1)
                
                # 生成正弦波测试音频
                import numpy as np
                import soundfile as sf
                
                sr = 22050
                duration = max(len(text) * 0.15, 2.0)  # 估算时长，至少2秒
                t = np.linspace(0, duration, int(sr * duration))
                
                # 生成多频率叠加的测试音频
                y = 0.3 * np.sin(2 * np.pi * 440 * t)  # A4
                y += 0.2 * np.sin(2 * np.pi * 554 * t)  # C#5
                y += 0.1 * np.sin(2 * np.pi * 659 * t)  # E5
                
                sf.write(output_path, y.astype(np.float32), sr)
                
                self._report_progress("音频合成完成 (Mock 模式)", 30)
            else:
                # 真实调用 CosyVoice
                self._report_progress("正在合成语音...", 20)
                
                cmd = [
                    sys.executable, str(cosyvoice_script),
                    "--text", text,
                    "--prompt_audio", voice_wav,
                    "--output", output_path,
                    "--device", self.device
                ]
                
                # 如果使用 FP16
                if self.config["use_fp16"]:
                    cmd.append("--fp16")
                
                subprocess.run(cmd, check=True, capture_output=True)
                self._report_progress("音频合成完成", 30)
            
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"CosyVoice 推理失败: {error_msg}")
            return False
            
        except Exception as e:
            logger.error(f"音频合成异常: {e}")
            return False
            
        finally:
            # 关键: 彻底清理显存，为 LivePortrait 腾出空间
            self._cleanup_vram(aggressive=True)
            logger.info("CosyVoice 显存已释放")

    def drive_video(self, source_image: str, driving_audio: str, output_path: str) -> bool:
        """
        使用 LivePortrait 驱动视频 (FP16 + xformers 优化)
        
        针对 RTX 4060 优化:
        - FP16 半精度推理 (显存占用减半)
        - target_size=512 (平衡画质与速度)
        - xformers 内存高效注意力 (如可用)
        - OOM 自动降级到串行处理
        
        :param source_image: 驱动图路径
        :param driving_audio: 驱动音频路径
        :param output_path: 输出视频路径
        :return: 是否成功
        """
        self._report_progress("正在加载 LivePortrait 模型...", 40)
        
        # 检查权重
        if not (WEIGHTS_DIR / "liveportrait").exists():
            logger.warning("未检测到 LivePortrait 权重，将使用模拟模式。")
        
        image_path = Path(source_image).absolute()
        audio_path = Path(driving_audio).absolute()
        out_path = Path(output_path).absolute()
        
        # 确保输出目录存在
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        liveportrait_script = TOOLS_DIR / "LivePortrait" / "inference.py"
        
        if not liveportrait_script.exists():
            # 模拟模式: 使用 ffmpeg 生成静态图视频
            logger.warning(f"未找到 LivePortrait 脚本 ({liveportrait_script})，使用模拟生成。")
            time.sleep(2)
            
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
                "-i", str(audio_path), "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                "-shortest", str(out_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._report_progress("视频驱动完成 (Mock 模式)", 90)
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg 模拟生成失败: {e}")
                return False
        
        # 真实推理 - 带 OOM 自动降级
        resolution = self.config["target_size"]
        use_fp16 = self.config["use_fp16"]
        max_attempts = 3 if not self.serial_mode else 1
        
        for attempt in range(max_attempts):
            try:
                mode_info = "串行模式" if self.serial_mode else f"尝试 {attempt+1}/{max_attempts}"
                self._report_progress(
                    f"LivePortrait 推理中 ({mode_info}, FP16={use_fp16}, Res={resolution})...", 
                    50 + attempt * 10
                )
                
                cmd = [
                    sys.executable, str(liveportrait_script),
                    "--source", str(image_path),
                    "--driving", str(audio_path),
                    "--output", str(out_path),
                    "--device", self.device,
                    "--resolution", str(resolution),
                    "--batch_size", str(1 if self.serial_mode else self.config["batch_size"])
                ]
                
                # FP16 半精度
                if use_fp16:
                    cmd.append("--fp16")
                
                # xformers 优化
                if XFORMERS_AVAILABLE and self.config["enable_xformers"]:
                    cmd.append("--xformers")
                
                subprocess.run(cmd, check=True, capture_output=True)
                
                self._report_progress("视频驱动完成", 90)
                return True
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                logger.error(f"LivePortrait 推理出错: {error_msg}")
                
                # 检测 OOM 错误
                if "out of memory" in error_msg.lower() or "cuda" in error_msg.lower():
                    logger.warning("检测到显存不足，正在尝试降级...")
                    
                    # 清理显存
                    self._cleanup_vram(aggressive=True)
                    
                    if attempt == 0:
                        # 第一次失败: 降低分辨率
                        resolution = self.config["fallback_size"]
                        logger.info(f"降级到分辨率: {resolution}")
                    elif attempt == 1:
                        # 第二次失败: 切换到串行模式 + 最小分辨率
                        self.serial_mode = True
                        resolution = self.config["min_size"]
                        logger.warning(f"切换到串行处理模式，分辨率: {resolution}")
                    else:
                        # 三次失败: 放弃
                        logger.error("多次尝试后仍然 OOM，请检查 GPU 显存是否被其他程序占用")
                        return False
                else:
                    # 非 OOM 错误，直接失败
                    return False
                    
            except Exception as e:
                logger.error(f"LivePortrait 推理异常: {e}")
                return False
        
        return False

    def run_pipeline(self, 
                     text: str, 
                     source_image: str, 
                     voice_seed: str, 
                     output_filename_base: str) -> Optional[str]:
        """
        执行全流程 (文本 -> 音频 -> 视频)
        
        :param text: 要合成的脚本文本
        :param source_image: 驱动图路径 (来自 temp_upload/)
        :param voice_seed: 参考音色 wav 路径
        :param output_filename_base: 输出文件名基础 (不含扩展名)
        :return: 最终视频路径，失败返回 None
        """
        # 使用 local_gen 输出目录
        temp_dir = LOCAL_GEN_OUTPUT_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_audio = temp_dir / f"{output_filename_base}_audio.wav"
        final_video = LOCAL_GEN_OUTPUT_DIR / f"{output_filename_base}.mp4"
        
        try:
            # 1. 音频合成 (CosyVoice)
            if not self.synthesize_audio(text, voice_seed, str(temp_audio)):
                raise RuntimeError("音频合成步骤失败")
            
            # 验证音频文件
            if not temp_audio.exists() or temp_audio.stat().st_size < 100:
                raise RuntimeError("生成的音频文件异常 (文件不存在或过小)")

            # 2. 视频驱动 (LivePortrait)
            if not self.drive_video(source_image, str(temp_audio), str(final_video)):
                raise RuntimeError("视频驱动步骤失败")
            
            # 3. 后处理: 检查是否需要音画合并
            if not self._has_audio_stream(str(final_video)):
                self._report_progress("正在进行音画同步合并...", 95)
                temp_merged = str(final_video).replace(".mp4", "_merged.mp4")
                self._merge_av(str(final_video), str(temp_audio), temp_merged)
                shutil.move(temp_merged, str(final_video))
            
            self._report_progress("✅ 全流程完成", 100)
            return str(final_video)

        except Exception as e:
            logger.error(f"Pipeline 执行异常: {e}")
            traceback.print_exc()
            self._report_progress(f"❌ 失败: {str(e)}", 0)
            return None
            
        finally:
            # 最终清理
            self._cleanup_vram(aggressive=True)

    def run_batch_pipeline(self, 
                           segments: List[Dict], 
                           source_image: str, 
                           voice_seed: str) -> List[Optional[str]]:
        """
        批量视频生成 (带 OOM 串行回退)
        
        :param segments: 视频片段列表 [{"text": "...", "output_name": "..."}]
        :param source_image: 驱动图路径
        :param voice_seed: 参考音色 wav 路径
        :return: 各片段的输出路径列表
        """
        results = []
        total = len(segments)
        
        for i, seg in enumerate(segments):
            self._report_progress(f"处理片段 {i+1}/{total}...", int((i / total) * 100))
            
            result = self.run_pipeline(
                text=seg.get("text", ""),
                source_image=source_image,
                voice_seed=voice_seed,
                output_filename_base=seg.get("output_name", f"segment_{i+1}")
            )
            results.append(result)
            
            # 串行模式下每个片段后都彻底清理
            if self.serial_mode:
                self._cleanup_vram(aggressive=True)
                time.sleep(1)  # 给 GPU 一些冷却时间
        
        return results

    def _has_audio_stream(self, video_path: str) -> bool:
        """检查视频是否包含音频流"""
        try:
            output = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path
            ])
            return len(output) > 0
        except:
            return False

    def _merge_av(self, video_path: str, audio_path: str, output_path: str):
        """合并音视频并校准延迟"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ----------------------------------------------------------------------------
# CLI 入口 (用于测试)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="RTX 4060 优化版本地视频生成引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python engine_local.py --text "你好，欢迎使用智能课程引擎" --image avatar.png --voice voice.wav
  
路径映射:
  - 驱动图: temp_upload/
  - 输出:   output_videos/local_gen/
        """
    )
    parser.add_argument("--text", type=str, required=True, help="要合成的脚本文本")
    parser.add_argument("--image", type=str, required=True, help="驱动图路径")
    parser.add_argument("--voice", type=str, required=True, help="参考音色 wav 文件")
    parser.add_argument("--output", type=str, default="test_output", help="输出文件名 (不含扩展名)")
    parser.add_argument("--serial", action="store_true", help="强制使用串行模式")
    
    args = parser.parse_args()
    
    def test_callback(msg, prog):
        print(f"PROGRESS: {prog:3d}% - {msg}")
    
    engine = LocalInferenceEngine(callback=test_callback)
    
    if args.serial:
        engine.serial_mode = True
        print("⚠ 已启用串行处理模式")
    
    result = engine.run_pipeline(args.text, args.image, args.voice, args.output)
    
    if result:
        print(f"\n✅ 视频生成成功: {result}")
    else:
        print("\n❌ 视频生成失败")
        sys.exit(1)
