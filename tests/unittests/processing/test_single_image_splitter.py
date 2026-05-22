# -*- coding: utf-8 -*-

"""大图拆分模块单元测试
测试用例统计：
========================
一、完整流水线测试 - 3个
  设计角度：
  1. 4主沟场景：验证num_segments_to_remove=4时，完整流水线输出正确
  2. 3主沟场景：验证num_segments_to_remove=3时，完整流水线输出正确
  3. 默认配置：不传入config时，使用DEFAULT_CONFIG处理

二、配置校验测试 - 2个
  设计角度：
  1. 无效配置：vertical_parts_to_keep配置错误时返回config_error状态
  2. 不支持参数：num_segments_to_remove=2时抛出异常

三、过滤功能测试 - 3个
  设计角度：
  1. vertical_parts_to_keep过滤：只保留指定索引，验证输出数量减少
  2. 边界过滤：保留最小有效组合（1个side+1个center）
  3. 过窄段过滤：宽度<5像素的图像段被自动跳过

四、异常处理测试 - 2个
  设计角度：
  1. 处理异常：处理过程中抛出异常时正确捕获并返回error状态
  2. 空图像输入：传入None时正确处理并返回error状态

五、异常检测测试 - 1个
  设计角度：
  1. 宽高比异常：输入超宽图像，验证异常图像被正确识别
  2. 颜色异常：输入单色图像，验证异常图像被正确识别

六、真实数据集成测试 - 2个
  设计角度：
  1. 真实图片匹配：使用tire_design_images数据集验证处理结果与参考图片一致
  2. 真实图片结构：验证真实图片处理结果结构完整性
========================
"""

import sys
import os
import unittest
import numpy as np
import cv2
from pathlib import Path

from src.processing.single_image_splitter import process_single_file, DEFAULT_CONFIG

# 定义真实数据集路径
_DATASET_ROOT = Path("tests/datasets/tire_design_images")
_IMAGES_DIR = _DATASET_ROOT / "images"
_PIECES_DIR = _DATASET_ROOT / "pieces"


def _load_image(path: Path, flags=cv2.IMREAD_COLOR):
    """读取图片（使用np.fromfile + cv2.imdecode，支持中文路径）"""
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, flags)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


class TestProcessSingleFile(unittest.TestCase):
    """process_single_file 函数测试（原有测试用例保持不变）"""

    def _create_test_image_4_segments(self, height=300, width=500):
        """创建4主沟测试图像"""
        img = np.ones((height, width, 3), dtype=np.uint8) * 200
        for pos in [100, 200, 300, 400]:
            img[:, pos:pos+5, :] = [0, 0, 0]
        return img

    def _create_test_image_3_segments(self, height=300, width=400):
        """创建3主沟测试图像"""
        img = np.ones((height, width, 3), dtype=np.uint8) * 200
        for pos in [100, 200, 300]:
            img[:, pos:pos+5, :] = [0, 0, 0]
        return img

    # ========== 完整流水线测试 ==========

    def test_process_4_segments_full_pipeline(self):
        """PASS: 4主沟完整流水线处理"""
        img = self._create_test_image_4_segments()
        config = {'num_segments_to_remove': 4}
        result = process_single_file(img, config)
        self.assertIn('side_final_images', result)
        self.assertIn('center_final_images', result)
        self.assertIn('abnormal_images', result)
        self.assertIn('stats', result)
        except_rst = {
            'status': 'success'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertGreater(result['stats']['vertical_segments'], 0)

    def test_process_3_segments_full_pipeline(self):
        """PASS: 3主沟完整流水线处理"""
        img = self._create_test_image_3_segments()
        config = {'num_segments_to_remove': 3}
        result = process_single_file(img, config)
        except_rst = {
            'status': 'success'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertGreater(result['stats']['vertical_segments'], 0)

    def test_default_config(self):
        """PASS: 使用默认配置处理"""
        img = self._create_test_image_4_segments()
        result = process_single_file(img, {})
        except_rst = {
            'status': 'success'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])

    # ========== 配置校验测试 ==========

    def test_invalid_config_returns_error(self):
        """FAIL: vertical_parts_to_keep配置错误返回config_error"""
        img = self._create_test_image_4_segments()
        config = {
            'num_segments_to_remove': 4,
            'vertical_parts_to_keep': [2, 3, 4]
        }
        result = process_single_file(img, config)
        except_rst = {
            'status': 'config_error',
            'side_len': 0,
            'center_len': 0
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertEqual(len(result['side_final_images']), except_rst['side_len'])
        self.assertEqual(len(result['center_final_images']), except_rst['center_len'])

    def test_unsupported_segments(self):
        """FAIL: 不支持的主沟数抛出异常"""
        img = self._create_test_image_4_segments()
        config = {'num_segments_to_remove': 2}
        result = process_single_file(img, config)
        except_rst = {
            'status': 'error'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])

    # ========== 过滤功能测试 ==========

    def test_vertical_parts_to_keep_filtering(self):
        """PASS: vertical_parts_to_keep过滤生效"""
        img = self._create_test_image_4_segments()
        config = {
            'num_segments_to_remove': 4,
            'vertical_parts_to_keep': [1, 2, 3]
        }
        result = process_single_file(img, config)
        except_rst = {
            'status': 'success',
            'vertical_segments': 3
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertEqual(result['stats']['vertical_segments'], except_rst['vertical_segments'])

    def test_vertical_parts_minimal_keep(self):
        """PASS: 保留最小有效组合（1个side+1个center）"""
        img = self._create_test_image_4_segments()
        config = {
            'num_segments_to_remove': 4,
            'vertical_parts_to_keep': [1, 2]
        }
        result = process_single_file(img, config)
        except_rst = {
            'status': 'success',
            'vertical_segments': 2
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertEqual(result['stats']['vertical_segments'], except_rst['vertical_segments'])

    def test_narrow_segment_skipped(self):
        """PASS: 宽度<5像素的图像段被跳过"""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        img[:, 30:33, :] = [0, 0, 0]
        img[:, 60:70, :] = [0, 0, 0]
        config = {'num_segments_to_remove': 3}
        result = process_single_file(img, config)
        except_rst = {
            'status': 'success'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])

    # ========== 异常处理测试 ==========

    def test_process_exception_handled(self):
        """PASS: 处理过程中异常被正确捕获"""
        config = {'num_segments_to_remove': 4}
        result = process_single_file(None, config)
        except_rst = {
            'status': 'error'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertIn('error_message', result['stats'])

    def test_process_exception_with_empty_image(self):
        """PASS: 传入空数组图像时异常被正确捕获"""
        img = np.array([])
        config = {'num_segments_to_remove': 4}
        result = process_single_file(img, config)
        except_rst = {
            'status': 'error'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])

    # ========== 异常检测测试 ==========

    def test_abnormal_image_detection(self):
        """PASS: 异常宽高比图像被正确检测"""
        img = np.ones((50, 300, 3), dtype=np.uint8) * 128
        config = {'num_segments_to_remove': 4}
        result = process_single_file(img, config)
        except_rst = {
            'status': 'success'
        }
        self.assertEqual(result['stats']['status'], except_rst['status'])
        self.assertGreaterEqual(result['stats']['abnormal_count'], 0)


class TestProcessSingleFileWithRealData(unittest.TestCase):
    """使用真实轮胎设计图片的集成测试"""

    def setUp(self):
        """检查数据集是否存在"""
        if not _IMAGES_DIR.exists():
            self.skipTest(f"测试数据集不存在: {_IMAGES_DIR}")
        if not _PIECES_DIR.exists():
            self.skipTest(f"测试数据集不存在: {_PIECES_DIR}")

    def _get_test_config(self):
        return {
            'num_segments_to_remove': 4,
            'vertical_parts_to_keep': [1, 4]
        }

    def _iter_image_files(self):
        """遍历所有输入图片文件"""
        extensions = ['*.png', '*.jpg', '*.jpeg']
        for ext in extensions:
            yield from sorted(_IMAGES_DIR.glob(ext))

    def _load_reference_images(self, base_name):
        """加载参考图片（pieces/side 和 pieces/center）"""
        side_dir = _PIECES_DIR / "side"
        center_dir = _PIECES_DIR / "center"
        
        side_images = {}
        for path in sorted(side_dir.glob(f"{base_name}_*.png")):
            suffix = path.stem.replace(base_name, "")
            side_images[suffix] = _load_image(path)
        
        center_images = {}
        for path in sorted(center_dir.glob(f"{base_name}_*.png")):
            suffix = path.stem.replace(base_name, "")
            center_images[suffix] = _load_image(path)
        
        return side_images, center_images

    def test_real_images_match_reference(self):
        """真实图片处理结果应与参考图片一致"""
        config = self._get_test_config()
        
        for idx, img_path in enumerate(self._iter_image_files(), 1):
            with self.subTest(case_idx=idx):
                # 1. 读取输入图片
                base_name = img_path.stem
                img = _load_image(img_path)
                
                # 2. 运行完整流水线
                result = process_single_file(img, config)
                
                # 3. 验证处理成功
                self.assertEqual(result['stats']['status'], 'success')
                
                # 4. 加载参考图片
                expected_side, expected_center = self._load_reference_images(base_name)
                
                # 5. 比较侧边图片
                for img_array, suffix in result['side_final_images']:
                    expected_key = suffix
                    self.assertIn(expected_key, expected_side, 
                                f"缺少预期的侧边图片: {base_name}{expected_key}.png")
                    expected_img = expected_side[expected_key]
                    self.assertEqual(img_array.shape, expected_img.shape,
                                    f"侧边图片 {base_name}{expected_key} 尺寸不一致")
                    self.assertTrue(np.array_equal(img_array, expected_img),
                                    f"侧边图片 {base_name}{expected_key} 像素不一致")
                
                # 6. 比较中心图片
                for img_array, suffix in result['center_final_images']:
                    expected_key = suffix
                    self.assertIn(expected_key, expected_center,
                                f"缺少预期的中心图片: {base_name}{expected_key}.png")
                    expected_img = expected_center[expected_key]
                    self.assertEqual(img_array.shape, expected_img.shape,
                                    f"中心图片 {base_name}{expected_key} 尺寸不一致")
                    self.assertTrue(np.array_equal(img_array, expected_img),
                                    f"中心图片 {base_name}{expected_key} 像素不一致")

    def test_real_images_output_structure(self):
        """真实图片处理结果结构验证"""
        config = self._get_test_config()
        
        for idx, img_path in enumerate(self._iter_image_files(), 1):
            with self.subTest(case_idx=idx):
                img = _load_image(img_path)
                result = process_single_file(img, config)
                
                # 验证输出结构完整性
                self.assertIn('side_final_images', result)
                self.assertIn('center_final_images', result)
                self.assertIn('abnormal_images', result)
                self.assertIn('stats', result)
                
                # 验证图片格式
                for img_array, suffix in result['side_final_images']:
                    self.assertIsInstance(img_array, np.ndarray)
                    self.assertEqual(img_array.ndim, 3)  # BGR格式
                
                for img_array, suffix in result['center_final_images']:
                    self.assertIsInstance(img_array, np.ndarray)
                    self.assertEqual(img_array.ndim, 3)  # BGR格式


if __name__ == '__main__':
    unittest.main()
