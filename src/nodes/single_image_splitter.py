# -*- coding: utf-8 -*-

"""
大图拆分模块 - 单图处理入口

提供单张成品设计图的拆分与预处理流水线。
输入整图，输出切分后的侧边/中间小图及异常检测结果。

依赖:
    - core.split.cropping: 裁剪与切分算法
    - core.split.analysis: 图像分析与质量检测
    - core.split.validation: 配置校验

入口函数:
    process_single_file(image, config) -> dict
"""

# Copyright © 2026. All rights reserved.

import cv2
import numpy as np

from src.utils.logger import get_logger

from src.core.split.cropping import (
    remove_black_and_split_segments,
    remove_side_white,
    remove_edge_gray,
    random_horizontal_crop,
    detect_periodic_blocks,
)
from src.core.split.analysis import (
    analyze_dominant_color,
    remove_vertical_lines_center,
    analyze_single_image_abnormalities,
)
from src.core.split.validation import _validate_vertical_parts_to_keep

logger = get_logger(__name__)

# 默认配置常量
DEFAULT_CONFIG = {
    'num_segments_to_remove': 4,
    'gray_tolerance': 20,
    'gray_edge_percent': 50,
    'vertical_parts_to_keep': None
}


def process_single_file(image, config) -> dict:
    """
    单文件处理主函数

    流程:
    1. 纵向切分 -> center 和 side (支持通过vertical_parts_to_keep过滤)
    2. 去除灰边 -> side_cleaned
    3. 横向切分 -> center_final 和 side_final
    4. 异常检测 -> abnormal
    
    Args:
        image: numpy数组 (BGR格式)，输入图像
        config: 处理配置字典，包含:
            - num_segments_to_remove: 要移除的黑色段数量，支持3或4
            - gray_tolerance: 灰色容差（默认20）
            - gray_edge_percent: 边缘百分比（默认50）
            - vertical_parts_to_keep: 要保留的纵向切分索引列表（可选，从1开始）
              示例: [1,2,3,4] 表示只保留第1,2,3,4部分
    
    Returns:
        dict: 处理结果，包含:
            - side_final_images: list[(numpy.ndarray, str)] 侧边最终图像列表 [(img, suffix), ...]
            - center_final_images: list[(numpy.ndarray, str)] 中间最终图像列表 [(img, suffix), ...]
            - abnormal_images: list[(numpy.ndarray, str, list)] 异常图像列表 [(img, suffix, abnormalities), ...]
            - stats: dict 处理统计信息
    """
    num_segments_to_remove = config.get('num_segments_to_remove', DEFAULT_CONFIG['num_segments_to_remove'])
    gray_tolerance = config.get('gray_tolerance', DEFAULT_CONFIG['gray_tolerance'])
    gray_edge_percent = config.get('gray_edge_percent', DEFAULT_CONFIG['gray_edge_percent'])
    vertical_parts_to_keep = config.get('vertical_parts_to_keep', DEFAULT_CONFIG['vertical_parts_to_keep'])
    
    # 提前校验配置
    if vertical_parts_to_keep is not None:
        try:
            _validate_vertical_parts_to_keep(vertical_parts_to_keep, num_segments_to_remove)
        except ValueError as e:
            logger.error(f"配置错误: {str(e)}")
            return {
                'side_final_images': [],
                'center_final_images': [],
                'abnormal_images': [],
                'stats': {
                    'status': 'config_error',
                    'error_type': 'invalid_config',
                    'error_message': str(e),
                    'vertical_segments': 0,
                    'gray_edge_removed': 0,
                    'horizontal_splits': 0,
                    'abnormal_count': 0
                }
            }
    
    stats = {
        'vertical_segments': 0,
        'gray_edge_removed': 0,
        'horizontal_splits': 0,
        'abnormal_count': 0,
        'status': 'success'
    }
    
    try:
        if num_segments_to_remove == 4:
            side_indices = [1, 5]
        elif num_segments_to_remove == 3:
            side_indices = [1, 4]
        else:
            raise ValueError(f"num_segments_to_remove只支持3或4，当前值为{num_segments_to_remove}")
        
        if vertical_parts_to_keep is not None:
            logger.debug(f"  [配置] vertical_parts_to_keep={vertical_parts_to_keep}")
        
        logger.debug(f"  [流程1] 执行纵向切分...")
        vertical_parts = remove_black_and_split_segments(image, num_segments_to_remove)
        
        vertical_parts_with_idx = list(enumerate(vertical_parts, 1))
        
        if vertical_parts_to_keep is not None:
            vertical_parts_with_idx = [
                (idx, img) for idx, img in vertical_parts_with_idx
                if idx in vertical_parts_to_keep
            ]
            logger.debug(f"  [流程1] 过滤后保留 {len(vertical_parts_with_idx)} 个图像段")
        
        side_images = []
        center_images = []
        
        for idx, img_part in vertical_parts_with_idx:
            if idx == 1:
                img_part = remove_side_white(img_part, direction='left')
            elif idx == side_indices[1]:
                img_part = remove_side_white(img_part, direction='right')
            
            height, width = img_part.shape[:2]
            
            if width < 5:
                logger.warning(f"跳过过窄的图像段: 索引{idx}, 宽度={width}")
                continue
            
            if idx in side_indices:
                side_images.append((idx, img_part))
            else:
                center_images.append((idx, img_part))
            
            stats['vertical_segments'] += 1
        
        logger.debug(f"  [流程1] 纵向切分完成，生成 {stats['vertical_segments']} 个图像段")
        
        logger.debug(f"  [流程2] 去除边缘灰边...")
        side_images_cleaned = []
        
        for idx, side_img in side_images:
            dominant_color = analyze_dominant_color(side_img)
            dominant_color_bgr = dominant_color[::-1]
            cleaned_img = remove_edge_gray(side_img, dominant_color_bgr, gray_tolerance, gray_edge_percent)
            side_images_cleaned.append((idx, cleaned_img))
            stats['gray_edge_removed'] += 1
        
        logger.debug(f"  [流程2] 灰边去除完成，处理了 {stats['gray_edge_removed']} 个图像")
        
        logger.debug(f"  [流程3] 执行横向切分...")
        side_final_images = []
        center_final_images = []
        
        for idx, side_img in side_images_cleaned:
            image_part = detect_periodic_blocks(side_img, min_cycles=5, max_cycles=7)
            
            if image_part is None:
                image_part = random_horizontal_crop(side_img, min_splits=5, max_splits=7)
                suffix = "random"
            else:
                suffix = "periodic"
            
            side_final_images.append((image_part, f"_side_part{idx}_{suffix}"))
            
            de_line_image = remove_vertical_lines_center(image_part, x_tolerance=1, length_ratio=0.5, line_width=3)
            
            if de_line_image is not None:
                side_final_images.append((de_line_image, f"_side_part{idx}_{suffix}_de_line"))
        
        side_horizontal_count = len(side_final_images)
        logger.debug(f"  [流程3] 侧边横向切分完成，生成 {side_horizontal_count} 个图像块")
        
        center_horizontal_count = 0
        for idx, center_img in center_images:
            image_part = detect_periodic_blocks(center_img, min_cycles=5, max_cycles=7)
            
            if image_part is None:
                image_part = random_horizontal_crop(center_img, min_splits=5, max_splits=7)
                suffix = "random"
            else:
                suffix = "periodic"
            
            center_final_images.append((image_part, f"_center_part{idx}_{suffix}"))
            
            de_line_image = remove_vertical_lines_center(image_part, x_tolerance=2, length_ratio=0.7, line_width=3)
            
            if de_line_image is not None:
                center_final_images.append((de_line_image, f"_center_part{idx}_{suffix}_de_line"))
        
        center_horizontal_count = len(center_final_images)
        logger.debug(f"  [流程3] 中间横向切分完成，生成 {center_horizontal_count} 个图像块")
        
        stats['horizontal_splits'] = side_horizontal_count + center_horizontal_count
        logger.debug(f"  [流程3] 横向切分总计，生成 {stats['horizontal_splits']} 个图像块")
        
        logger.debug(f"  [流程4] 执行异常检测...")
        abnormal_images = []
        
        side_normal_images = []
        for img_array, suffix in side_final_images:
            is_abnormal, abnormalities = analyze_single_image_abnormalities(img_array)
            
            if is_abnormal:
                abnormal_desc = "，".join(abnormalities)
                logger.warning(f"异常图片: {suffix} - {abnormal_desc}")
                abnormal_images.append((img_array, suffix, abnormalities))
            else:
                side_normal_images.append((img_array, suffix))
        
        center_normal_images = []
        for img_array, suffix in center_final_images:
            is_abnormal, abnormalities = analyze_single_image_abnormalities(img_array)
            
            if is_abnormal:
                abnormal_desc = "，".join(abnormalities)
                logger.warning(f"异常图片: {suffix} - {abnormal_desc}")
                abnormal_images.append((img_array, suffix, abnormalities))
            else:
                center_normal_images.append((img_array, suffix))
        
        stats['abnormal_count'] = len(abnormal_images)
        logger.debug(f"  [流程4] 异常检测完成，发现 {stats['abnormal_count']} 张异常图片")
        
    except Exception as e:
        logger.error(f"处理图像时发生错误: {str(e)}")
        stats['status'] = 'error'
        stats['error_message'] = str(e)
        
        return {
            'side_final_images': [],
            'center_final_images': [],
            'abnormal_images': [],
            'stats': stats
        }
    
    return {
        'side_final_images': side_normal_images,
        'center_final_images': center_normal_images,
        'abnormal_images': abnormal_images,
        'stats': stats
    }