#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡尔曼滤波器模块
用于平滑3D坐标跟踪结果
"""

import cv2
import numpy as np


class KalmanFilter3D:
    """3D坐标卡尔曼滤波器，用于平滑跟踪结果"""

    def __init__(self):
        # 创建卡尔曼滤波器（6维状态：x, y, z, vx, vy, vz）
        self.kf = cv2.KalmanFilter(6, 3)

        # 状态转移矩阵
        self.kf.transitionMatrix = np.array([
            [1, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 1],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ], dtype=np.float32)

        # 测量矩阵
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ], dtype=np.float32)

        # 过程噪声协方差
        self.kf.processNoiseCov = np.eye(6, dtype=np.float32) * 0.03

        # 测量噪声协方差
        self.kf.measurementNoiseCov = np.eye(3, dtype=np.float32) * 10

        self.initialized = False

    def update(self, measurement: np.ndarray) -> np.ndarray:
        """
        更新滤波器

        Args:
            measurement: 测量值 [x, y, z]

        Returns:
            滤波后的估计值 [x, y, z]
        """
        if not self.initialized:
            # 初始化状态
            self.kf.statePost = np.array([
                [measurement[0]], [measurement[1]], [measurement[2]],
                [0], [0], [0]
            ], dtype=np.float32)
            self.initialized = True
            return measurement

        # 预测
        prediction = self.kf.predict()

        # 更新
        measurement_matrix = np.array([[measurement[0]], [measurement[1]], [measurement[2]]],
                                     dtype=np.float32)
        estimated = self.kf.correct(measurement_matrix)

        return np.array([estimated[0, 0], estimated[1, 0], estimated[2, 0]])
