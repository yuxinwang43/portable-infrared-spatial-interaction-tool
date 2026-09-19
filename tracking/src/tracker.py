#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主追踪器模块
整合所有功能模块，运行追踪系统
"""

import cv2
import numpy as np
import time
from datetime import datetime
import socket
import json
import config
from src.camera import CameraManager
from src.detector import LEDDetector
from src.position_calculator import PositionCalculator
from src.visualizer import Visualizer
from src.data_recorder import DataRecorder


class IRTrackerAdvanced:
    """高级红外追踪器"""

    def __init__(self):
        """初始化追踪器"""
        # 从配置文件加载参数
        self.led_mode = config.LED_MODE if hasattr(config, 'LED_MODE') else 'line_2led'

        # LED_DISTANCE_MM 只在 line_2led 模式下需要，rectangle_4led 模式下不使用
        self.led_distance_mm = config.LED_DISTANCE_MM if hasattr(config, 'LED_DISTANCE_MM') else 50.0

        self.led_rect_width_mm = config.LED_RECT_WIDTH_MM if hasattr(config, 'LED_RECT_WIDTH_MM') else 30.0
        self.led_rect_height_mm = config.LED_RECT_HEIGHT_MM if hasattr(config, 'LED_RECT_HEIGHT_MM') else 25.0
        self.camera_tilt_angle = config.CAMERA_TILT_ANGLE
        self.video_width = config.VIDEO_WIDTH
        self.video_height = config.VIDEO_HEIGHT

        # 根据LED模式设置期望的LED数量
        self.expected_led_count = 4 if self.led_mode == 'rectangle_4led' else 2

        # 初始化各个模块
        self.camera_manager = CameraManager(
            config.CAMERA_ID,
            self.video_width,
            self.video_height
        )

        self.detector = None  # 需要相机初始化后才能创建
        self.position_calculator = None
        self.visualizer = Visualizer(self.led_mode)
        self.data_recorder = DataRecorder(
            self.led_mode,
            self.video_width,
            self.video_height
        )

        # 统计信息
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()

        # Unity 传输
        self.unity_socket = None
        self.unity_enabled = config.ENABLE_UNITY_TRANSMISSION if hasattr(config, 'ENABLE_UNITY_TRANSMISSION') else False
        if self.unity_enabled:
            try:
                self.unity_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.unity_ip = config.UNITY_IP if hasattr(config, 'UNITY_IP') else "127.0.0.1"
                self.unity_port = config.UNITY_PORT if hasattr(config, 'UNITY_PORT') else 5005
                self.send_orientation = config.SEND_ORIENTATION if hasattr(config, 'SEND_ORIENTATION') else True
                print(f"Unity 传输已启用: {self.unity_ip}:{self.unity_port}")
            except Exception as e:
                print(f"警告：Unity socket 初始化失败: {e}")
                self.unity_enabled = False

    def initialize_camera(self) -> bool:
        """初始化摄像头"""
        if not self.camera_manager.initialize():
            return False

        # 创建需要相机内参的模块
        camera_matrix = self.camera_manager.get_camera_matrix()
        dist_coeffs = self.camera_manager.get_distortion_coeffs()

        self.detector = LEDDetector(
            self.led_mode,
            self.led_distance_mm,
            self.led_rect_width_mm,
            self.led_rect_height_mm,
            camera_matrix,
            self.video_width,
            self.video_height
        )

        self.position_calculator = PositionCalculator(
            self.led_mode,
            self.led_distance_mm,
            self.led_rect_width_mm,
            self.led_rect_height_mm,
            camera_matrix,
            dist_coeffs,
            self.camera_tilt_angle
        )

        return True

    def run(self):
        """运行追踪系统"""
        if not self.initialize_camera():
            return

        self._print_startup_info()

        try:
            consecutive_failures = 0
            max_failures = 5

            while True:
                ret, frame = self.camera_manager.read_frame()

                if not ret or frame is None:
                    consecutive_failures += 1
                    print(f"\n警告：无法读取帧 (连续失败 {consecutive_failures}/{max_failures})")

                    if consecutive_failures >= max_failures:
                        print("错误：摄像头持续无法读取，退出程序")
                        break

                    time.sleep(0.1)
                    continue

                consecutive_failures = 0
                self.frame_count += 1

                # 计算FPS
                self._update_fps()

                # 检测LED
                led_centers, binary = self.detector.detect(frame)

                # 获取跟踪状态
                tracking_state = self.detector.get_tracking_state()
                is_real_detection = not tracking_state.get('zero_led_mode', False) and not tracking_state.get('single_led_mode', False)

                # 计算3D位置和姿态
                # ⚡ 优化：只有真实检测到LED时才计算和发送
                position_data = None
                if len(led_centers) >= self.expected_led_count and is_real_detection:
                    position_data = self.position_calculator.calculate(led_centers)

                    if position_data is not None and 'position' in position_data:
                        self._print_position_info(position_data)

                        # 发送数据到 Unity（只发送真实检测的数据）
                        self._send_to_unity(position_data)

                        # 记录数据
                        self.data_recorder.record_position_data(position_data, led_centers)

                # 绘制结果
                output_frame = self.visualizer.draw(frame, led_centers, position_data, tracking_state)

                # 显示主窗口
                cv2.imshow(config.WINDOW_NAME, output_frame)

                # 显示二值图像
                if binary is not None and config.SHOW_BINARY_IMAGE:
                    cv2.imshow('Binary (Debug)', binary)

                # 录制视频
                self.data_recorder.record_video_frame(output_frame)

                # 处理按键
                if not self._handle_key_press():
                    break

        finally:
            self.cleanup()

    def _update_fps(self):
        """更新FPS"""
        current_time = time.time()
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_time)
            self.visualizer.update_fps(self.fps)
            self.frame_count = 0
            self.last_time = current_time

    def _print_position_info(self, position_data):
        """打印位置信息"""
        # ⚡ 优化：禁用打印以降低延迟（节省50-200ms）
        # 如需调试，取消下面的注释
        # x, y, z = position_data['position']
        # distance = np.sqrt(x**2 + y**2 + z**2)
        #
        # if position_data.get('orientation') is not None:
        #     roll, pitch, yaw = position_data['orientation']
        #     print(f"\r3D坐标: X={x:7.1f}mm Y={y:7.1f}mm Z={z:7.1f}mm  "
        #           f"距离={distance:7.1f}mm  "
        #           f"姿态: R={roll:6.1f}° P={pitch:6.1f}° Y={yaw:6.1f}°",
        #           end='', flush=True)
        # else:
        #     print(f"\r3D坐标: X={x:7.1f}mm  Y={y:7.1f}mm  Z={z:7.1f}mm  "
        #           f"距离={distance:7.1f}mm",
        #           end='', flush=True)
        pass

    def _send_to_unity(self, position_data):
        """
        发送位置和姿态数据到 Unity

        Args:
            position_data: 包含 position 和 orientation 的字典
        """
        if not self.unity_enabled or self.unity_socket is None:
            return

        try:
            x, y, z = position_data['position']

            # 构建基础数据（位置）
            data = {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            }

            # 如果启用姿态发送且有姿态数据，添加姿态信息
            if self.send_orientation and position_data.get('orientation') is not None:
                roll, pitch, yaw = position_data['orientation']
                data["roll"] = float(roll)
                data["pitch"] = float(pitch)
                data["yaw"] = float(yaw)

            # 发送 JSON 数据
            msg = json.dumps(data).encode('utf-8')
            self.unity_socket.sendto(msg, (self.unity_ip, self.unity_port))

        except Exception as e:
            # 静默错误，避免影响主循环
            pass

    def _handle_key_press(self) -> bool:
        """
        处理按键事件

        Returns:
            True继续运行，False退出
        """
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            return False
        elif key == ord('s'):
            # 截图
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ret, frame = self.camera_manager.read_frame()
            if ret:
                cv2.imwrite(filename, frame)
                print(f"\n截图已保存: {filename}")
        elif key == ord('r'):
            # 重置卡尔曼滤波器
            if self.position_calculator is not None:
                self.position_calculator.reset_kalman_filter()
                print("\n卡尔曼滤波器已重置")
        return True

    def _print_startup_info(self):
        """打印启动信息"""
        print("\n" + "=" * 60)
        print("         红外LED追踪系统 - 高级版")
        print("=" * 60)

        if self.led_mode == 'rectangle_4led':
            print(f"LED模式: 矩形4LED (可追踪姿态)")
            print(f"矩形尺寸: {self.led_rect_width_mm}mm x {self.led_rect_height_mm}mm")
        else:
            print(f"LED模式: 直线2LED (仅追踪位置)")
            print(f"LED间距: {self.led_distance_mm} mm")

        print(f"摄像头角度: {self.camera_tilt_angle}°")
        print(f"卡尔曼滤波: {'启用' if config.USE_KALMAN_FILTER else '禁用'}")
        print(f"视频录制: {'启用' if config.SAVE_VIDEO else '禁用'}")
        print(f"坐标记录: {'启用' if config.SAVE_COORDINATES else '禁用'}")

        # Unity 传输状态
        if self.unity_enabled:
            orientation_status = "位置+姿态" if (self.send_orientation and self.led_mode == 'rectangle_4led') else "仅位置"
            print(f"Unity 传输: 启用 ({self.unity_ip}:{self.unity_port}) - {orientation_status}")
        else:
            print(f"Unity 传输: 禁用")

        print("\n按键操作：")
        print("  q - 退出程序")
        print("  s - 截图")
        print("  r - 重置卡尔曼滤波器")
        print("=" * 60 + "\n")

    def cleanup(self):
        """清理资源"""
        self.camera_manager.release()
        self.data_recorder.cleanup()

        # 关闭 Unity socket
        if self.unity_socket is not None:
            try:
                self.unity_socket.close()
                print("\nUnity 连接已关闭")
            except:
                pass

        cv2.destroyAllWindows()
        print("\n系统已关闭")


def main():
    tracker = IRTrackerAdvanced()
    tracker.run()


if __name__ == "__main__":
    main()
