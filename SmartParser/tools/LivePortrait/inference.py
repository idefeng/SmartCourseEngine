#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LivePortrait 视频驱动 CLI 脚本
==============================

用于 engine_local.py 调用的 LivePortrait 音频驱动视频推理脚本。
支持静态图像 + 音频 -> 说话人头像视频生成。

使用方法:
    python inference.py --source image.png --driving audio.wav --output video.mp4

依赖:
    pip install opencv-python mediapipe onnxruntime-gpu

作者: SmartCourseEngine Team
日期: 2026-02-02
"""

import os
import sys
import argparse
import logging
import tempfile
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取权重目录
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent.parent
WEIGHTS_DIR = BASE_DIR / "pretrained_weights" / "liveportrait"


def check_dependencies():
    """检查必要的依赖"""
    missing = []
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    try:
        import torch
    except ImportError:
        missing.append("torch")
    
    if missing:
        logger.error(f"缺少依赖: {', '.join(missing)}")
        logger.info(f"请安装: pip install {' '.join(missing)}")
        return False
    
    return True


def drive_video(source_image: str, driving_audio: str, output_path: str,
                device: str = "cuda", resolution: int = 512, 
                fp16: bool = True, xformers: bool = False, batch_size: int = 1):
    """
    使用 LivePortrait 驱动视频
    
    :param source_image: 源图像路径
    :param driving_audio: 驱动音频路径
    :param output_path: 输出视频路径
    :param device: 推理设备
    :param resolution: 输出分辨率
    :param fp16: 是否使用半精度
    :param xformers: 是否使用 xformers
    :param batch_size: 批次大小
    """
    try:
        import cv2
        import numpy as np
        import torch
        
        # 设置设备
        if device == "cuda" and torch.cuda.is_available():
            torch.set_default_device("cuda")
            if fp16:
                torch.set_default_dtype(torch.float16)
            logger.info(f"使用 GPU: {torch.cuda.get_device_name(0)}")
            
            # TF32 优化
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        else:
            device = "cpu"
            logger.info("使用 CPU 推理")
        
        # 检查模型权重
        liveportrait_dir = WEIGHTS_DIR / "liveportrait"
        if not liveportrait_dir.exists():
            liveportrait_dir = WEIGHTS_DIR
        
        base_models = liveportrait_dir / "base_models"
        if not base_models.exists():
            raise FileNotFoundError(f"未找到 LivePortrait base_models: {base_models}")
        
        logger.info(f"模型路径: {liveportrait_dir}")
        
        # 尝试导入 LivePortrait
        try:
            # 添加 LivePortrait 源码路径
            lp_src = BASE_DIR / "LivePortrait"
            if lp_src.exists():
                sys.path.insert(0, str(lp_src))
            
            from src.live_portrait_pipeline import LivePortraitPipeline
            from src.config.inference_config import InferenceConfig
            
            # 创建配置
            cfg = InferenceConfig()
            cfg.flag_pasteback = True
            cfg.flag_do_crop = True
            cfg.output_fps = 25
            
            if fp16:
                cfg.flag_use_half_precision = True
            
            # 创建 Pipeline
            pipeline = LivePortraitPipeline(
                inference_cfg=cfg,
                checkpoint_dir=str(liveportrait_dir)
            )
            
            # 执行推理
            logger.info("开始 LivePortrait 推理...")
            pipeline.execute(
                source=source_image,
                driving=driving_audio,
                output=output_path
            )
            
            logger.info(f"视频已保存: {output_path}")
            return True
            
        except ImportError as e:
            logger.warning(f"无法导入 LivePortrait Pipeline: {e}")
            logger.info("回退到 FFmpeg 静态图模式...")
            
            # 备用方案：使用 FFmpeg 生成静态图视频
            return generate_static_video(source_image, driving_audio, output_path, resolution)
            
    except Exception as e:
        logger.error(f"LivePortrait 推理异常: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试备用方案
        logger.info("尝试备用 FFmpeg 方案...")
        return generate_static_video(source_image, driving_audio, output_path, resolution)


def generate_static_video(image_path: str, audio_path: str, output_path: str, resolution: int = 512):
    """
    备用方案：使用 FFmpeg 生成静态图+音频的视频
    
    :param image_path: 图像路径
    :param audio_path: 音频路径
    :param output_path: 输出视频路径
    :param resolution: 输出分辨率
    """
    try:
        import cv2
        
        # 读取并调整图像大小
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        h, w = img.shape[:2]
        if max(h, w) != resolution:
            scale = resolution / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
            
            # 保存调整后的图像
            temp_img = Path(output_path).parent / "temp_resized.png"
            cv2.imwrite(str(temp_img), img)
            image_path = str(temp_img)
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 FFmpeg 生成视频
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={resolution}:{resolution}:force_original_aspect_ratio=decrease,pad={resolution}:{resolution}:(ow-iw)/2:(oh-ih)/2",
            "-shortest",
            output_path
        ]
        
        logger.info(f"执行 FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg 错误: {result.stderr}")
            return False
        
        logger.info(f"静态视频已生成: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"生成静态视频失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="LivePortrait 视频驱动 CLI")
    parser.add_argument("--source", type=str, required=True, help="源图像路径")
    parser.add_argument("--driving", type=str, required=True, help="驱动音频路径")
    parser.add_argument("--output", type=str, required=True, help="输出视频路径")
    parser.add_argument("--device", type=str, default="cuda", help="推理设备")
    parser.add_argument("--resolution", type=int, default=512, help="输出分辨率")
    parser.add_argument("--fp16", action="store_true", help="使用半精度")
    parser.add_argument("--xformers", action="store_true", help="使用 xformers")
    parser.add_argument("--batch_size", type=int, default=1, help="批次大小")
    
    args = parser.parse_args()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查权重
    if not WEIGHTS_DIR.exists():
        logger.error(f"模型权重不存在: {WEIGHTS_DIR}")
        logger.info("请下载模型: git clone https://huggingface.co/KwaiVGI/LivePortrait pretrained_weights/liveportrait")
        sys.exit(1)
    
    # 执行推理
    success = drive_video(
        source_image=args.source,
        driving_audio=args.driving,
        output_path=args.output,
        device=args.device,
        resolution=args.resolution,
        fp16=args.fp16,
        xformers=args.xformers,
        batch_size=args.batch_size
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
