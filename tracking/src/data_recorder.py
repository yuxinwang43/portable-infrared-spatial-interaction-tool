#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据记录模块
负责视频录制和CSV数据记录
"""

import cv2
import csv
from datetime import datetime
from typing import List, Tuple, Optional
import config


class DataRecorder:
    """数据记录器"""

    def __init__(self, led_mode, video_width, video_height):
        """
        初始化数据记录器

        Args:
            led_mode: LED模式
            video_width: 视频宽度
            video_height: 视频高度
        """
        self.led_mode = led_mode
        self.video_width = video_width
        self.video_height = video_height

        # 视频录制
        self.video_writer = None
        if config.SAVE_VIDEO:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                config.OUTPUT_VIDEO_PATH, fourcc, config.VIDEO_FPS,
                (self.video_width, self.video_height)
            )

        # 数据记录
        self.csv_file = None
        self.csv_writer = None
        if config.SAVE_COORDINATES:
            self.csv_file = open(config.COORDINATES_FILE, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            if self.led_mode == 'rectangle_4led':
                self.csv_writer.writerow(['timestamp', 'x_mm', 'y_mm', 'z_mm', 'roll', 'pitch', 'yaw',
                                         'led1_x', 'led1_y', 'led2_x', 'led2_y',
                                         'led3_x', 'led3_y', 'led4_x', 'led4_y'])
            else:
                self.csv_writer.writerow(['timestamp', 'x_mm', 'y_mm', 'z_mm',
                                         'led1_x', 'led1_y', 'led2_x', 'led2_y'])

    def record_video_frame(self, frame):
        """记录视频帧"""
        if self.video_writer is not None:
            self.video_writer.write(frame)

    def record_position_data(self, position_data: dict, led_centers: List[Tuple[int, int]]):
        """
        记录位置数据到CSV

        Args:
            position_data: 位置数据字典
            led_centers: LED中心点列表
        """
        if self.csv_writer is None or position_data is None or 'position' not in position_data:
            return

        x, y, z = position_data['position']
        timestamp = datetime.now().isoformat()

        if self.led_mode == 'rectangle_4led' and len(led_centers) >= 4:
            roll, pitch, yaw = position_data.get('orientation', (0, 0, 0))
            self.csv_writer.writerow([
                timestamp, x, y, z, roll, pitch, yaw,
                led_centers[0][0], led_centers[0][1],
                led_centers[1][0], led_centers[1][1],
                led_centers[2][0], led_centers[2][1],
                led_centers[3][0], led_centers[3][1]
            ])
        elif len(led_centers) >= 2:
            self.csv_writer.writerow([
                timestamp, x, y, z,
                led_centers[0][0], led_centers[0][1],
                led_centers[1][0], led_centers[1][1]
            ])

    def cleanup(self):
        """清理资源"""
        if self.video_writer is not None:
            self.video_writer.release()
            print(f"\n视频已保存: {config.OUTPUT_VIDEO_PATH}")

        if self.csv_file is not None:
            self.csv_file.close()
            print(f"坐标数据已保存: {config.COORDINATES_FILE}")
