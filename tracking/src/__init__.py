#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infrared spatial interaction source package
"""

__version__ = "2.0.0"

# 导入主要类
from .tracker import IRTrackerAdvanced
from .detector import LEDDetector
from .position_calculator import PositionCalculator
from .camera import CameraManager
from .visualizer import Visualizer
from .data_recorder import DataRecorder
from .kalman_filter import KalmanFilter3D
from .utils import draw_dashed_line, order_rectangle_points, find_best_rectangle

__all__ = [
    'IRTrackerAdvanced',
    'LEDDetector',
    'PositionCalculator',
    'CameraManager',
    'Visualizer',
    'DataRecorder',
    'KalmanFilter3D',
    'draw_dashed_line',
    'order_rectangle_points',
    'find_best_rectangle'
]
