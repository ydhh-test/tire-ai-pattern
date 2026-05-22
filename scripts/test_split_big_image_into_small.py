# -*- coding: utf-8 -*-

"""大图拆分集成测试"""

# Copyright © 2026. All rights reserved.

import cv2
import numpy as np
import os
import glob
from PIL import Image

from src.utils.logger import get_logger

from src.processing.single_image_splitter import process_single_file, DEFAULT_CONFIG

logger = get_logger(__name__)


def _get_image_files(input_dir, extensions=None):
    """获取输入目录中的所有图片文件"""
    if extensions is None:
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tif', '*.tiff']
    img_files = []
    for ext in extensions:
        img_files.extend(glob.glob(os.path.join(input_dir, ext)))
        img_files.extend(glob.glob(os.path.join(input_dir, ext.upper())))
    return sorted(set(img_files))


def _save_image(image, output_path):
    """统一保存图像，自动处理路径创建"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, image)
    return output_path


def _ensure_dir(dir_path):
    """确保目录存在"""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def convert_cmyk_to_rgb(img_pil):
    """
    将PIL CMYK图像转换为OpenCV BGR格式（内存转换，无需文件IO）

    Args:
        img_pil: PIL Image对象 (CMYK模式)

    Returns:
        numpy数组 (BGR格式)
    """
    img_rgb = img_pil.convert('RGB')
    return cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)


def batch_process_files(workspace_dir, config=None, debug=False):
    """
    批量处理文件主函数

    数据流转图:
        batch_process_files
            ↓
        [读取图片] PIL.Image.open + convert_cmyk_to_rgb
            ↓
        img (numpy.ndarray)
            ↓
        调用 process_single_file(img, config)
            ↓
        [流程1-4纯内存处理]
            ↓
        返回结果字典:
        {
            'side_final_images': [(img, suffix), ...],
            'center_final_images': [(img, suffix), ...],
            'abnormal_images': [(img, suffix, abnormalities), ...],
            'stats': {...}
        }
            ↓
        [debug=True 时批量写盘]
            ↓
        输出文件:
            ├── side_final/
            ├── center_final/
            └── abnormal/

    Args:
        workspace_dir: 工作空间目录路径
        config: 处理配置字典，为None时使用默认配置。
            示例:
            {
                'num_segments_to_remove': 4,
                'vertical_parts_to_keep': [1,2,3,4],
                'gray_tolerance': 20,
                'gray_edge_percent': 50
            }
        debug: 调试开关，True时输出图片到磁盘

    Returns:
        dict: 批量处理结果统计
    """
    paths = {
        'input': os.path.join(workspace_dir, "images"),
        'side_final': os.path.join(workspace_dir, "pieces", "side"),
        'center_final': os.path.join(workspace_dir, "pieces", "center"),
        'abnormal': os.path.join(workspace_dir, "pieces", "abnormal"),
    }

    # 使用传入配置或默认配置
    effective_config = config if config is not None else DEFAULT_CONFIG.copy()

    logger.info(f"开始批量处理，工作目录: {workspace_dir}, debug={debug}")
    logger.info(f"当前生效配置: {effective_config}")

    img_files = _get_image_files(paths['input'])

    if not img_files:
        raise ValueError(f"输入目录 {paths['input']} 中没有找到有效的图片文件")

    stats = {
        'total_files': len(img_files),
        'processed_files': 0,
        'failed_files': 0,
        'file_results': [],
        'total_abnormal': 0
    }

    for idx, img_path in enumerate(img_files, 1):
        base_name = os.path.splitext(os.path.basename(img_path))[0]

        logger.info(f"处理文件 [{idx}/{len(img_files)}]: {base_name}")

        try:
            img_pil = Image.open(img_path)
            if img_pil.mode == "CMYK":
                img = convert_cmyk_to_rgb(img_pil)
            else:
                img = cv2.cvtColor(np.array(img_pil.convert('RGB')), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"无法读取图片: {img_path}, 错误: {e}")
            stats['failed_files'] += 1
            stats['file_results'].append({
                'file_name': base_name,
                'status': 'error',
                'error_message': str(e)
            })
            continue

        result = process_single_file(img, effective_config)

        file_stats = result['stats']
        file_stats['file_name'] = base_name
        stats['file_results'].append(file_stats)

        if file_stats['status'] == 'success':
            stats['processed_files'] += 1
            stats['total_abnormal'] += file_stats.get('abnormal_count', 0)

            if debug:
                _ensure_dir(paths['side_final'])
                _ensure_dir(paths['center_final'])
                _ensure_dir(paths['abnormal'])

                for img_array, suffix in result['side_final_images']:
                    filename = f"{base_name}{suffix}.png"
                    save_path = os.path.join(paths['side_final'], filename)
                    _save_image(img_array, save_path)

                for img_array, suffix in result['center_final_images']:
                    filename = f"{base_name}{suffix}.png"
                    save_path = os.path.join(paths['center_final'], filename)
                    _save_image(img_array, save_path)

                for img_array, suffix, abnormalities in result['abnormal_images']:
                    filename = f"{base_name}{suffix}_abnormal.png"
                    save_path = os.path.join(paths['abnormal'], filename)
                    _save_image(img_array, save_path)

                logger.debug(f"已保存 {len(result['side_final_images'])} 张侧边图像, "
                             f"{len(result['center_final_images'])} 张中间图像, "
                             f"{len(result['abnormal_images'])} 张异常图片")
        else:
            stats['failed_files'] += 1

    logger.info(f"{'='*50}")
    logger.info("批量处理全部完成！")
    logger.info(f"  输入文件: {stats['total_files']}")
    logger.info(f"  成功处理: {stats['processed_files']}")
    logger.info(f"  失败文件: {stats['failed_files']}")
    logger.info(f"  异常图片: {stats['total_abnormal']}")

    if debug:
        side_final_count = len(os.listdir(paths['side_final'])) if os.path.exists(paths['side_final']) else 0
        center_final_count = len(os.listdir(paths['center_final'])) if os.path.exists(paths['center_final']) else 0
        abnormal_count = len(os.listdir(paths['abnormal'])) if os.path.exists(paths['abnormal']) else 0

        logger.info(f"  目录文件统计:")
        logger.info(f"  最终输出: side={side_final_count}, center={center_final_count}")
        logger.info(f"  异常图片: abnormal={abnormal_count}")

    logger.info(f"{'='*50}")

    return {
        'status': 'success',
        'stats': stats
    }


def main(workspace_dir):
    """
    批处理测试主函数

    Args:
        workspace_dir: 工作目录路径
    """
    # 调试模式（自动输出结果图片至{workspace_dir}/pieces目录）
    test_config = {
        'num_segments_to_remove': 4,
        'vertical_parts_to_keep': [1, 4]
    }
    result = batch_process_files(workspace_dir, config=test_config, debug=True)

    # 生产模式（仅内存处理，不写盘）
    # result = batch_process_files(workspace_dir, config=test_config, debug=False)
    return result


if __name__ == "__main__":
    # 测试用例目录,{workspace_dir}/images下包含了输入的图片
    workspace_dir = r"./tests/datasets/tire_design_images"
    main(workspace_dir)
