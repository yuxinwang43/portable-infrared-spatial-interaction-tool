#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化模块
负责绘制检测结果和跟踪信息
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
import config
from src.utils import draw_dashed_line


class Visualizer:
    """可视化器"""

    def __init__(self, led_mode):
        """
        初始化可视化器

        Args:
            led_mode: LED模式
        """
        self.led_mode = led_mode
        self.fps = 0

    def draw(self, frame: np.ndarray,
             led_centers: List[Tuple[int, int]],
             position_data: Optional[dict],
             tracking_state: dict) -> np.ndarray:
        """
        在图像上绘制检测结果和跟踪信息

        Args:
            frame: 输入图像
            led_centers: LED中心点列表
            position_data: 位置数据字典
            tracking_state: 跟踪状态字典
        """
        # ⚡ 优化：直接在原图上绘制，避免帧拷贝（节省5-15ms）
        output = frame

        # 提取跟踪状态
        state = tracking_state.get('state', 'SEARCHING')
        single_led_mode = tracking_state.get('single_led_mode', False)
        zero_led_mode = tracking_state.get('zero_led_mode', False)
        led_velocity = tracking_state.get('led_velocity')
        led_vector = tracking_state.get('led_vector')
        led_distance = tracking_state.get('led_distance')
        last_led_positions = tracking_state.get('last_led_positions')
        stable_frames = tracking_state.get('stable_frames', 0)

        # 绘制LED向量（单LED模式）
        if single_led_mode and led_vector is not None and len(led_centers) >= 2:
            self._draw_led_vector(output, led_centers, led_distance)

        # 绘制运动预测
        if config.ENABLE_MOTION_PREDICTION and led_velocity is not None and last_led_positions is not None:
            if zero_led_mode:
                self._draw_motion_prediction(output, last_led_positions, led_velocity)

        # 绘制LED标记
        self._draw_led_markers(output, led_centers, state, zero_led_mode, single_led_mode)

        # 绘制连线/矩形
        # 零LED模式下不绘制连线（因为没有真实检测）
        if not zero_led_mode:
            if self.led_mode == 'rectangle_4led' and len(led_centers) >= 4:
                self._draw_rectangle(output, led_centers, state, zero_led_mode, single_led_mode)
            elif self.led_mode == 'line_2led' and len(led_centers) >= 2:
                self._draw_line(output, led_centers, zero_led_mode, single_led_mode)

        # 显示3D坐标
        if position_data is not None:
            self._draw_position_info(output, position_data, zero_led_mode)

        # 显示调试信息
        if config.SHOW_DEBUG_INFO:
            self._draw_debug_info(output, len(led_centers), state,
                                 zero_led_mode, single_led_mode,
                                 stable_frames, led_velocity)

        return output

    def _draw_led_vector(self, output, led_centers, led_distance):
        """绘制LED向量（单LED模式）"""
        led1, led2 = led_centers[0], led_centers[1]
        draw_dashed_line(output, led1, led2, (255, 165, 0), 2, 10)

        mid_x = (led1[0] + led2[0]) // 2
        mid_y = (led1[1] + led2[1]) // 2
        if led_distance:
            cv2.putText(output, f"Est. {led_distance:.0f}px",
                      (mid_x - 40, mid_y - 15),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 165, 0), 1)

    def _draw_motion_prediction(self, output, last_led_positions, led_velocity):
        """绘制运动预测轨迹"""
        for last_pos in last_led_positions:
            for t in range(1, 6):
                pred_x = int(last_pos[0] + led_velocity[0] * t)
                pred_y = int(last_pos[1] + led_velocity[1] * t)
                if 0 <= pred_x < output.shape[1] and 0 <= pred_y < output.shape[0]:
                    alpha = 1.0 - (t / 6.0)
                    color = (int(100 * alpha), int(100 * alpha), int(255 * alpha))
                    cv2.circle(output, (pred_x, pred_y), 3, color, -1)

    def _draw_led_markers(self, output, led_centers, state, zero_led_mode, single_led_mode):
        """绘制LED标记"""
        # 零LED模式下：没有真实检测，不绘制LED（避免误导）
        if zero_led_mode:
            return

        for i, (x, y) in enumerate(led_centers):
            if zero_led_mode:
                led_color = (147, 20, 255)  # 深粉色 - 完全预测
                # 绘制虚线圆圈
                for angle in range(0, 360, 20):
                    angle_rad = np.radians(angle)
                    x1 = int(x + 10 * np.cos(angle_rad))
                    y1 = int(y + 10 * np.sin(angle_rad))
                    x2 = int(x + 10 * np.cos(angle_rad + np.radians(10)))
                    y2 = int(y + 10 * np.sin(angle_rad + np.radians(10)))
                    cv2.line(output, (x1, y1), (x2, y2), led_color, 2)
                cv2.circle(output, (x, y), 3, led_color, -1)
            elif single_led_mode:
                led_color = (0, 255, 0)  # 绿色
                cv2.circle(output, (x, y), 10, led_color, 2)
                cv2.circle(output, (x, y), 3, (255, 165, 0), -1)  # 橙色中心
            elif state == "TRACKING":
                led_color = (0, 255, 0)  # 绿色
                cv2.circle(output, (x, y), 10, led_color, 2)
                cv2.circle(output, (x, y), 3, led_color, -1)
            elif state == "LOST":
                led_color = (0, 165, 255)  # 橙色
                cv2.circle(output, (x, y), 10, led_color, 2)
                cv2.circle(output, (x, y), 3, led_color, -1)
            else:
                led_color = (0, 255, 255)  # 黄色
                cv2.circle(output, (x, y), 10, led_color, 2)
                cv2.circle(output, (x, y), 3, led_color, -1)

            label = f"LED{i+1}"
            cv2.putText(output, label, (x + 15, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, led_color, 2)

    def _draw_rectangle(self, output, led_centers, state, zero_led_mode, single_led_mode):
        """绘制矩形（4LED模式）"""
        if zero_led_mode:
            rect_color = (147, 20, 255)
            mid_color = (147, 20, 255)
        elif single_led_mode:
            rect_color = (255, 165, 0)
            mid_color = (255, 165, 0)
        elif state == "TRACKING":
            rect_color = (0, 255, 0)
            mid_color = (0, 255, 0)
        else:
            rect_color = (0, 255, 255)
            mid_color = (0, 255, 255)

        # 绘制矩形四条边
        for i in range(4):
            p1 = led_centers[i]
            p2 = led_centers[(i + 1) % 4]
            if zero_led_mode:
                draw_dashed_line(output, p1, p2, rect_color, 2, 8)
            else:
                cv2.line(output, p1, p2, rect_color, 2)

        # 绘制对角线
        if not zero_led_mode:
            cv2.line(output, led_centers[0], led_centers[2], rect_color, 1)
            cv2.line(output, led_centers[1], led_centers[3], rect_color, 1)

        # 绘制中心点
        mid_x = int(sum(p[0] for p in led_centers[:4]) / 4)
        mid_y = int(sum(p[1] for p in led_centers[:4]) / 4)
        cv2.circle(output, (mid_x, mid_y), 8, mid_color, -1)
        cv2.circle(output, (mid_x, mid_y), 12, mid_color, 2)

        # 模式提示
        if zero_led_mode or single_led_mode:
            mode_text = "PRED" if zero_led_mode else "EST"
            cv2.putText(output, mode_text, (mid_x + 20, mid_y + 5),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, mid_color, 2)

    def _draw_line(self, output, led_centers, zero_led_mode, single_led_mode):
        """绘制连线（2LED模式）"""
        led1, led2 = led_centers[0], led_centers[1]

        if zero_led_mode:
            draw_dashed_line(output, led1, led2, (147, 20, 255), 2, 8)
            mid_color = (147, 20, 255)
        elif single_led_mode:
            draw_dashed_line(output, led1, led2, (255, 165, 0), 2, 15)
            mid_color = (255, 165, 0)
        else:
            cv2.line(output, led1, led2, (255, 0, 0), 2)
            mid_color = (0, 0, 255)

        mid_x = int((led1[0] + led2[0]) / 2)
        mid_y = int((led1[1] + led2[1]) / 2)
        cv2.circle(output, (mid_x, mid_y), 8, mid_color, -1)
        cv2.circle(output, (mid_x, mid_y), 12, mid_color, 2)

        # 模式提示
        if zero_led_mode or single_led_mode:
            mode_text = "PRED" if zero_led_mode else "EST"
            cv2.putText(output, mode_text, (mid_x + 20, mid_y + 5),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, mid_color, 2)

    def _draw_position_info(self, output, position_data, zero_led_mode=False):
        """显示3D坐标信息"""
        if 'position' in position_data:
            x, y, z = position_data['position']

            # 根据模式调整颜色和文本
            if zero_led_mode:
                coord_color = (147, 20, 255)  # 粉色 - 预测坐标
                prefix = "[PRED] "
            else:
                coord_color = (0, 255, 255)  # 黄色 - 真实坐标
                prefix = ""

            coord_text = f"{prefix}Position: X={x:.1f}, Y={y:.1f}, Z={z:.1f} mm"
            cv2.putText(output, coord_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, coord_color, 2)

            distance = np.sqrt(x**2 + y**2 + z**2)
            dist_text = f"{prefix}Distance: {distance:.1f} mm"
            cv2.putText(output, dist_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, coord_color, 2)

            if 'orientation' in position_data and position_data['orientation'] is not None:
                roll, pitch, yaw = position_data['orientation']
                orient_text = f"{prefix}Orientation: R={roll:.1f}, P={pitch:.1f}, Y={yaw:.1f} deg"
                cv2.putText(output, orient_text, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, coord_color, 2)

    def _draw_debug_info(self, output, led_count, state, zero_led_mode,
                        single_led_mode, stable_frames, led_velocity):
        """显示调试信息"""
        # FPS
        cv2.putText(output, f"FPS: {self.fps:.1f}", (10, output.shape[0] - 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # LED数量 - 区分真实检测和预测
        # zero_led_mode 和 single_led_mode 已经作为参数传入
        if zero_led_mode:
            # 零LED模式：没有真实检测，显示为0
            led_text = f"LEDs: 0 (PREDICTING)"
            led_color = (147, 20, 255)  # 粉色
        elif single_led_mode:
            # 单LED模式：只检测到1个
            led_text = f"LEDs: 1 (ESTIMATED)"
            led_color = (255, 165, 0)  # 橙色
        else:
            # 正常检测
            led_text = f"LEDs: {led_count}"
            led_color = (255, 255, 255)  # 白色

        cv2.putText(output, led_text, (10, output.shape[0] - 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, led_color, 2)

        # 跟踪状态
        state_colors = {
            "SEARCHING": (0, 255, 255),
            "TRACKING": (0, 255, 0),
            "LOST": (0, 165, 255)
        }
        state_color = state_colors.get(state, (255, 255, 255))

        mode_suffix = ""
        if zero_led_mode:
            mode_suffix = " [0LED PRED]"
            state_color = (147, 20, 255)
        elif single_led_mode:
            mode_suffix = " [1LED EST]"
            state_color = (255, 165, 0)
        else:
            mode_suffix = f" [{led_count}LED DETECTED]"

        cv2.putText(output, f"State: {state}{mode_suffix}", (10, output.shape[0] - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)

        # 速度信息
        if led_velocity is not None:
            speed = np.sqrt(led_velocity[0]**2 + led_velocity[1]**2)
            cv2.putText(output, f"Speed: {speed:.1f} px/f", (10, output.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def update_fps(self, fps):
        """更新FPS"""
        self.fps = fps
