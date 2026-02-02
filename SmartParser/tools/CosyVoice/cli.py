#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CosyVoice 语音合成 CLI 脚本
===========================

用于 engine_local.py 调用的 CosyVoice 语音克隆推理脚本。
支持零样本语音克隆（Zero-shot Voice Cloning）。

使用方法:
    python cli.py --text "要合成的文本" --prompt_audio voice.wav --output output.wav

依赖:
    pip install cosyvoice torchaudio

作者: SmartCourseEngine Team
日期: 2026-02-02
"""

import os
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取权重目录
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent.parent
WEIGHTS_DIR = BASE_DIR / "pretrained_weights" / "CosyVoice-300M"


def setup_cosyvoice_path():
    """设置 CosyVoice 导入路径"""
    # 添加 CosyVoice 源码路径 (如果存在)
    cosyvoice_src = BASE_DIR / "CosyVoice"
    if cosyvoice_src.exists():
        sys.path.insert(0, str(cosyvoice_src))
        
        # 添加 Matcha-TTS 子模块路径 (关键!)
        matcha_path = cosyvoice_src / "third_party" / "Matcha-TTS"
        if matcha_path.exists():
            sys.path.insert(0, str(matcha_path))
            logger.info(f"已添加 Matcha-TTS 路径: {matcha_path}")
    
    # 尝试添加权重目录中的第三方依赖路径
    matcha_path = WEIGHTS_DIR / "third_party" / "Matcha-TTS"
    if matcha_path.exists():
        sys.path.insert(0, str(matcha_path))


def synthesize(text: str, prompt_audio: str, output_path: str, device: str = "cuda", fp16: bool = False):
    """
    使用 CosyVoice 进行语音合成
    
    :param text: 要合成的文本
    :param prompt_audio: 参考音色的音频文件路径
    :param output_path: 输出音频文件路径
    :param device: 推理设备 (cuda/cpu)
    :param fp16: 是否使用半精度
    """
    try:
        import torch
        import torchaudio
        
        # 设置设备
        if device == "cuda" and torch.cuda.is_available():
            torch.set_default_device("cuda")
            if fp16:
                torch.set_default_dtype(torch.float16)
            logger.info(f"使用 GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = "cpu"
            logger.info("使用 CPU 推理")
        
        # 尝试导入 CosyVoice
        try:
            from cosyvoice.cli.cosyvoice import AutoModel
        except ImportError:
            # 备用导入方式
            try:
                from cosyvoice.cli.cosyvoice import CosyVoice as AutoModel
            except ImportError:
                raise ImportError(
                    "无法导入 CosyVoice，请确保已安装: pip install cosyvoice\n"
                    "或者克隆官方仓库: git clone https://github.com/FunAudioLLM/CosyVoice"
                )
        
        logger.info(f"加载模型: {WEIGHTS_DIR}")
        model = AutoModel(model_dir=str(WEIGHTS_DIR))
        
        # 读取参考音频的文本提示（简化处理：使用固定提示）
        prompt_text = "希望你以后能够做的比我还好呦。"
        
        logger.info(f"开始合成: {text[:50]}...")
        
        # 使用零样本语音克隆
        output_audio = None
        for i, result in enumerate(model.inference_zero_shot(text, prompt_text, prompt_audio)):
            output_audio = result['tts_speech']
            if i == 0:  # 只取第一个结果
                break
        
        if output_audio is not None:
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存音频
            torchaudio.save(output_path, output_audio, model.sample_rate)
            logger.info(f"音频已保存: {output_path}")
            return True
        else:
            logger.error("合成失败：未生成音频数据")
            return False
            
    except Exception as e:
        logger.error(f"CosyVoice 推理异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="CosyVoice 语音合成 CLI")
    parser.add_argument("--text", type=str, required=True, help="要合成的文本")
    parser.add_argument("--prompt_audio", type=str, required=True, help="参考音色的音频文件")
    parser.add_argument("--output", type=str, required=True, help="输出音频文件路径")
    parser.add_argument("--device", type=str, default="cuda", help="推理设备 (cuda/cpu)")
    parser.add_argument("--fp16", action="store_true", help="使用半精度推理")
    
    args = parser.parse_args()
    
    # 设置路径
    setup_cosyvoice_path()
    
    # 检查权重
    if not WEIGHTS_DIR.exists():
        logger.error(f"模型权重不存在: {WEIGHTS_DIR}")
        logger.info("请下载模型: python -c \"from huggingface_hub import snapshot_download; snapshot_download('FunAudioLLM/CosyVoice-300M', local_dir='pretrained_weights/CosyVoice-300M')\"")
        sys.exit(1)
    
    # 执行合成
    success = synthesize(
        text=args.text,
        prompt_audio=args.prompt_audio,
        output_path=args.output,
        device=args.device,
        fp16=args.fp16
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
