#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份脚本
=============

自动备份 SmartCourseEngine 的关键数据：
- ChromaDB 向量数据库
- output_markdown 解析结果
- standards_library 标准库
- 配置文件

使用方法:
  python scripts/backup.py              # 手动备份
  python scripts/backup.py --restore    # 恢复备份

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json
import zipfile
import hashlib

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# 配置
# ============================================================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"

# 需要备份的目录和文件
BACKUP_TARGETS = [
    ("chroma_db", "ChromaDB 向量数据库"),
    ("output_markdown", "解析结果"),
    ("standards_library", "标准库"),
    ("generated_courseware", "生成的课件"),
]

BACKUP_FILES = [
    ("config.json", "配置文件"),
]

# 保留最近 N 个备份
MAX_BACKUPS = 7


# ============================================================================
# 备份函数
# ============================================================================
def create_backup(backup_name: str = None) -> Path:
    """
    创建数据备份
    
    Args:
        backup_name: 备份名称，默认使用时间戳
        
    Returns:
        备份文件路径
    """
    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成备份名称
    if not backup_name:
        backup_name = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    
    backup_path = BACKUP_DIR / f"{backup_name}.zip"
    
    print(f"📦 开始创建备份: {backup_path}")
    
    # 创建 ZIP 文件
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 备份目录
        for target, desc in BACKUP_TARGETS:
            target_path = DATA_DIR / target
            if target_path.exists():
                print(f"  📁 备份 {desc}...")
                for file_path in target_path.rglob('*'):
                    if file_path.is_file():
                        arcname = f"{target}/{file_path.relative_to(target_path)}"
                        zf.write(file_path, arcname)
        
        # 备份文件
        for target, desc in BACKUP_FILES:
            target_path = BASE_DIR / target
            if target_path.exists():
                print(f"  📄 备份 {desc}...")
                zf.write(target_path, target)
        
        # 添加元数据
        metadata = {
            "created_at": datetime.now().isoformat(),
            "targets": [t[0] for t in BACKUP_TARGETS],
            "files": [f[0] for f in BACKUP_FILES],
            "version": "1.0"
        }
        zf.writestr("_backup_metadata.json", json.dumps(metadata, indent=2))
    
    # 计算文件大小和校验和
    file_size = backup_path.stat().st_size
    file_hash = hashlib.md5(backup_path.read_bytes()).hexdigest()
    
    print(f"✅ 备份完成!")
    print(f"   路径: {backup_path}")
    print(f"   大小: {file_size / 1024 / 1024:.2f} MB")
    print(f"   MD5: {file_hash}")
    
    # 清理旧备份
    cleanup_old_backups()
    
    return backup_path


def restore_backup(backup_path: str) -> bool:
    """
    恢复数据备份
    
    Args:
        backup_path: 备份文件路径
        
    Returns:
        是否成功
    """
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        print(f"❌ 备份文件不存在: {backup_path}")
        return False
    
    print(f"🔄 开始恢复备份: {backup_path}")
    
    # 解压备份
    with zipfile.ZipFile(backup_path, 'r') as zf:
        # 读取元数据
        try:
            metadata = json.loads(zf.read("_backup_metadata.json"))
            print(f"   备份时间: {metadata.get('created_at', '未知')}")
        except Exception:
            print("   ⚠️ 无法读取备份元数据")
        
        # 恢复目录
        for target, desc in BACKUP_TARGETS:
            target_path = DATA_DIR / target
            print(f"  📁 恢复 {desc}...")
            
            # 清空目标目录
            if target_path.exists():
                shutil.rmtree(target_path)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 解压文件
            for name in zf.namelist():
                if name.startswith(f"{target}/"):
                    zf.extract(name, DATA_DIR)
        
        # 恢复文件
        for target, desc in BACKUP_FILES:
            if target in zf.namelist():
                print(f"  📄 恢复 {desc}...")
                zf.extract(target, BASE_DIR)
    
    print(f"✅ 备份恢复完成!")
    return True


def list_backups() -> list:
    """
    列出所有备份
    
    Returns:
        备份文件列表
    """
    if not BACKUP_DIR.exists():
        return []
    
    backups = sorted(
        BACKUP_DIR.glob("backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    return backups


def cleanup_old_backups():
    """清理旧备份，只保留最近的 N 个"""
    backups = list_backups()
    
    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            print(f"  🗑️ 删除旧备份: {old_backup.name}")
            old_backup.unlink()


# ============================================================================
# 命令行入口
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="SmartCourseEngine 数据备份工具")
    parser.add_argument(
        "--restore",
        type=str,
        metavar="BACKUP_FILE",
        help="恢复指定的备份文件"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有备份"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="指定备份名称"
    )
    
    args = parser.parse_args()
    
    if args.list:
        backups = list_backups()
        if backups:
            print("📋 可用备份列表:")
            for backup in backups:
                stat = backup.stat()
                size_mb = stat.st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(stat.st_mtime)
                print(f"  - {backup.name} ({size_mb:.2f} MB, {mtime.strftime('%Y-%m-%d %H:%M')})")
        else:
            print("📭 暂无备份")
    
    elif args.restore:
        restore_backup(args.restore)
    
    else:
        create_backup(args.name)


if __name__ == "__main__":
    main()
