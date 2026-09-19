#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D位置计算模块
负责计算LED的3D位置和姿态
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from src.kalman_filter import KalmanFilter3D
import config


class PositionCalculator:
    """3D位置计算器"""

    def __init__(self, led_mode, led_distance_mm, led_rect_width_mm, led_rect_height_mm,
                 camera_matrix, dist_coeffs, camera_tilt_angle):
        """
        初始化位置计算器

        Args:
            led_mode: LED模式
            led_distance_mm: LED间距（毫米）
            led_rect_width_mm: 矩形宽度（毫米）
            led_rect_height_mm: 矩形高度（毫米）
            camera_matrix: 相机内参矩阵
            dist_coeffs: 畸变系数
            camera_tilt_angle: 相机倾斜角度
        """
        self.led_mode = led_mode
        self.led_distance_mm = led_distance_mm
        self.led_rect_width_mm = led_rect_width_mm
        self.led_rect_height_mm = led_rect_height_mm
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.camera_tilt_angle = camera_tilt_angle

        # 卡尔曼滤波器
        self.kalman_filter = KalmanFilter3D() if config.USE_KALMAN_FILTER else None

    def calculate(self, led_positions: List[Tuple[int, int]]) -> Optional[dict]:
        """
        计算LED的3D位置和姿态

        Args:
            led_positions: LED位置列表，可以是2个（直线）或4个（矩形）

        Returns:
            字典包含 {'position': (x, y, z), 'orientation': (roll, pitch, yaw)} 或 None
            - 2LED模式：只返回position
            - 4LED模式：返回position和orientation
        """
        if self.camera_matrix is None or len(led_positions) < 2:
            return None

        if self.led_mode == 'line_2led' and len(led_positions) >= 2:
            return self._calculate_2led_position(led_positions)
        elif self.led_mode == 'rectangle_4led' and len(led_positions) >= 4:
            return self._calculate_4led_position(led_positions)

        return None

    def _calculate_2led_position(self, led_positions):
        """计算2LED直线模式的3D位置"""
        led1, led2 = led_positions[0], led_positions[1]

        pixel_distance = np.sqrt((led2[0] - led1[0])**2 + (led2[1] - led1[1])**2)

        if pixel_distance < 1:
            return None

        # 计算深度
        focal_length = self.camera_matrix[0, 0]
        z_distance = (focal_length * self.led_distance_mm) / pixel_distance

        # 中点像素坐标
        center_x = (led1[0] + led2[0]) / 2
        center_y = (led1[1] + led2[1]) / 2

        # 相机参数
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]

        # 相机坐标系
        x_cam = (center_x - cx) * z_distance / fx
        y_cam = (center_y - cy) * z_distance / fy
        z_cam = z_distance

        # 坐标转换（考虑倾斜角度）
        angle_rad = np.radians(-self.camera_tilt_angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        # ⚡ 修正：反转X轴（左右）和Z轴（上下）以匹配Unity坐标系
        x_world = -x_cam                             # 左右反转
        y_world = y_cam * cos_a - z_cam * sin_a     # 前后保持
        z_world = -(y_cam * sin_a + z_cam * cos_a)  # 上下反转

        position = np.array([x_world, y_world, z_world])

        # 应用卡尔曼滤波
        if self.kalman_filter is not None:
            position = self.kalman_filter.update(position)

        return {
            'position': tuple(position),
            'orientation': None
        }

    def _calculate_4led_position(self, led_positions):
        """计算4LED矩形模式的3D位置和姿态"""
        # 定义3D物体坐标（矩形的四个角，以中心为原点）
        half_width = self.led_rect_width_mm / 2
        half_height = self.led_rect_height_mm / 2

        object_points = np.array([
            [-half_width, -half_height, 0],  # 左上
            [half_width, -half_height, 0],   # 右上
            [half_width, half_height, 0],    # 右下
            [-half_width, half_height, 0]    # 左下
        ], dtype=np.float32)

        # 图像坐标（2D点）
        image_points = np.array([
            [led_positions[0][0], led_positions[0][1]],
            [led_positions[1][0], led_positions[1][1]],
            [led_positions[2][0], led_positions[2][1]],
            [led_positions[3][0], led_positions[3][1]]
        ], dtype=np.float32)

        # 使用solvePnP计算位姿
        success, rvec, tvec = cv2.solvePnP(
            object_points,
            image_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return None

        # 位置向量（相机坐标系）
        x_cam, y_cam, z_cam = tvec[0, 0], tvec[1, 0], tvec[2, 0]

        # 坐标转换（考虑倾斜角度）
        angle_rad = np.radians(-self.camera_tilt_angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        # ⚡ 修正：反转X轴（左右）和Z轴（上下）以匹配Unity坐标系
        x_world = -x_cam                             # 左右反转
        y_world = y_cam * cos_a - z_cam * sin_a     # 前后保持
        z_world = -(y_cam * sin_a + z_cam * cos_a)  # 上下反转

        position = np.array([x_world, y_world, z_world])

        # 旋转向量转换为欧拉角
        rotation_matrix, _ = cv2.Rodrigues(rvec)

        # 提取欧拉角（roll, pitch, yaw）
        roll = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        pitch = np.arctan2(-rotation_matrix[2, 0],
                          np.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2))
        yaw = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])

        # 转换为度
        roll_deg = np.degrees(roll)
        pitch_deg = np.degrees(pitch)
        yaw_deg = np.degrees(yaw)

        # 应用卡尔曼滤波（仅位置）
        if self.kalman_filter is not None:
            position = self.kalman_filter.update(position)

        return {
            'position': tuple(position),
            'orientation': (roll_deg, pitch_deg, yaw_deg)
        }

    def reset_kalman_filter(self):
        """重置卡尔曼滤波器"""
        if config.USE_KALMAN_FILTER:
            self.kalman_filter = KalmanFilter3D()
