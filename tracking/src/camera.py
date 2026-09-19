#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相机管理模块
负责相机的初始化和配置
"""

import cv2
import numpy as np
import time
import config


class CameraManager:
    """相机管理器"""

    def __init__(self, camera_id, video_width, video_height):
        """
        初始化相机管理器

        Args:
            camera_id: 相机ID
            video_width: 视频宽度
            video_height: 视频高度
        """
        self.camera_id = camera_id
        self.video_width = video_width
        self.video_height = video_height
        self.cap = None
        self.camera_matrix = None
        self.dist_coeffs = np.array(config.DISTORTION_COEFFS, dtype=np.float32).reshape(-1, 1)

    def initialize(self) -> bool:
        """初始化摄像头 - 黑玻滤片极限模式"""
        # 使用默认后端（最大兼容性，支持iPhone Continuity Camera）
        self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap.isOpened():
            print("错误：无法打开摄像头")
            return False

        print("正在配置黑玻滤片极限参数（800-2500nm）...")

        # ===== 第1步：设置分辨率和帧率 =====
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_height)
        # [*] 30fps是黑玻滤片模式的关键！允许更长的曝光时间
        self.cap.set(cv2.CAP_PROP_FPS, config.VIDEO_FPS)

        # ===== 第2步：禁用所有自动调节功能 =====
        # 关闭自动曝光（使用手动模式）
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, config.AUTO_EXPOSURE)

        # 关闭自动白平衡（红外拍摄不需要）
        if hasattr(config, 'AUTO_WHITE_BALANCE'):
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 0 if not config.AUTO_WHITE_BALANCE else 1)
        else:
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)

        # 关闭自动对焦（固定焦距）
        if hasattr(config, 'AUTO_FOCUS'):
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0 if not config.AUTO_FOCUS else 1)
        else:
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

        # ===== 第3步：设置固定的曝光参数（黑玻滤片极限模式）===== [***]
        # [***] 黑玻滤片阻挡几乎所有光线，必须使用极限参数
        self.cap.set(cv2.CAP_PROP_EXPOSURE, config.EXPOSURE)      # 10: 极限曝光 [***]
        self.cap.set(cv2.CAP_PROP_GAIN, config.GAIN)              # 255: 最大增益 [***]
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, config.BRIGHTNESS)  # 255: 最大亮度 [***]

        # 对比度：增强LED与背景对比 [**]
        if hasattr(config, 'CONTRAST'):
            self.cap.set(cv2.CAP_PROP_CONTRAST, config.CONTRAST)  # 255: 最大对比度
        else:
            self.cap.set(cv2.CAP_PROP_CONTRAST, 255)

        # ===== 第4步：优化缓冲设置 =====
        if hasattr(config, 'BUFFER_SIZE'):
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, config.BUFFER_SIZE)
        else:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 饱和度：设为低值（红外不需要色彩，黑玻滤片下更不需要）
        self.cap.set(cv2.CAP_PROP_SATURATION, 30)

        print("[OK] 黑玻滤片极限参数配置完成")

        # 获取实际分辨率
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        # 打印实际应用的固定参数
        print("\n" + "="*60)
        print("[***] 摄像头参数（黑玻滤片极限模式 - 800-2500nm） [***]")
        print("="*60)
        print(f"分辨率:     {width} x {height}")
        print(f"帧率:       {fps} fps   (30fps适应极长曝光)")
        print(f"---")
        print(f"曝光模式:   手动 (值: {self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE):.2f})")
        print(f"曝光值:     {self.cap.get(cv2.CAP_PROP_EXPOSURE):.2f}  [***] (极限)")
        print(f"增益/ISO:   {self.cap.get(cv2.CAP_PROP_GAIN):.2f}  [***] (最大)")
        print(f"亮度:       {self.cap.get(cv2.CAP_PROP_BRIGHTNESS):.2f}  [***] (最大)")
        print(f"对比度:     {self.cap.get(cv2.CAP_PROP_CONTRAST):.2f}  [**] (最大)")
        print(f"饱和度:     {self.cap.get(cv2.CAP_PROP_SATURATION):.2f}")
        print(f"---")
        print(f"自动白平衡: {'关闭' if self.cap.get(cv2.CAP_PROP_AUTO_WB) == 0 else '开启'}")
        print(f"自动对焦:   {'关闭' if self.cap.get(cv2.CAP_PROP_AUTOFOCUS) == 0 else '开启'}")
        print(f"缓冲区:     {int(self.cap.get(cv2.CAP_PROP_BUFFERSIZE))} 帧")
        print("="*60)
        print("[*] 黑玻滤片模式：极长曝光 + 30fps + 最大增益")
        print("="*60 + "\n")

        # 设置相机内参
        if config.USE_CUSTOM_CAMERA_MATRIX:
            self.camera_matrix = np.array([
                [config.FOCAL_LENGTH_X, 0, config.PRINCIPAL_POINT_X],
                [0, config.FOCAL_LENGTH_Y, config.PRINCIPAL_POINT_Y],
                [0, 0, 1]
            ], dtype=np.float32)
            print("使用自定义相机内参")
        else:
            # 使用估算值
            focal_length = width * 1.2
            self.camera_matrix = np.array([
                [focal_length, 0, width / 2],
                [0, focal_length, height / 2],
                [0, 0, 1]
            ], dtype=np.float32)
            print("使用估算的相机内参")

        print(f"摄像头已初始化: {width}x{height}")

        # ===== 预热摄像头（macOS必需）=====
        print("正在预热摄像头...")
        warmup_frames = 10
        for i in range(warmup_frames):
            ret, frame = self.cap.read()
            if ret:
                print(f"  预热进度: {i+1}/{warmup_frames} [OK]")
            else:
                print(f"  预热进度: {i+1}/{warmup_frames} [FAIL] (继续尝试...)")
            time.sleep(0.1)  # 每帧间隔100ms

        # 验证摄像头是否真的可以读取
        print("验证摄像头状态...")
        test_successful = False
        for attempt in range(5):
            ret, frame = self.cap.read()
            if ret and frame is not None:
                print(f"[OK] 摄像头验证成功！(尝试 {attempt+1}/5)")
                test_successful = True
                break
            else:
                print(f"[X] 摄像头验证失败 (尝试 {attempt+1}/5)，等待重试...")
                time.sleep(0.2)

        if not test_successful:
            print("错误：摄像头无法稳定读取帧")
            return False

        print("[OK] 摄像头预热完成，可以开始追踪\n")
        return True

    def read_frame(self):
        """读取一帧图像"""
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        """释放摄像头资源"""
        if self.cap is not None:
            self.cap.release()

    def get_camera_matrix(self):
        """获取相机内参矩阵"""
        return self.camera_matrix

    def get_distortion_coeffs(self):
        """获取畸变系数"""
        return self.dist_coeffs
