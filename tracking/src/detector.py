#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED检测模块
负责在图像中检测红外LED
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
import config
from src.utils import find_best_rectangle, order_rectangle_points


class LEDDetector:
    """LED检测器"""

    def __init__(self, led_mode, led_distance_mm, led_rect_width_mm, led_rect_height_mm,
                 camera_matrix, video_width, video_height):
        """
        初始化LED检测器

        Args:
            led_mode: LED模式 ('line_2led' 或 'rectangle_4led')
            led_distance_mm: LED间距（毫米）
            led_rect_width_mm: 矩形宽度（毫米）
            led_rect_height_mm: 矩形高度（毫米）
            camera_matrix: 相机内参矩阵
            video_width: 视频宽度
            video_height: 视频高度
        """
        self.led_mode = led_mode
        self.led_distance_mm = led_distance_mm
        self.led_rect_width_mm = led_rect_width_mm
        self.led_rect_height_mm = led_rect_height_mm
        self.camera_matrix = camera_matrix
        self.video_width = video_width
        self.video_height = video_height

        # 根据LED模式设置期望的LED数量
        self.expected_led_count = 4 if self.led_mode == 'rectangle_4led' else 2

        # 检测参数
        self.brightness_threshold = config.BRIGHTNESS_THRESHOLD
        self.min_area = config.MIN_LED_AREA
        self.max_area = config.MAX_LED_AREA

        # 历史跟踪（用于稳定检测）
        self.last_led_positions = None  # 上一帧的LED位置
        self.led_velocity = None  # LED运动速度 (dx, dy)
        self.led_vector = None  # LED1到LED2的向量 (dx, dy)
        self.led_distance = None  # 两个LED之间的像素距离
        self.led_rect_shape = None  # 矩形LED的几何形状
        self.led_lost_counter = 0  # 连续丢失帧数
        self.max_lost_frames = config.MAX_LOST_FRAMES if hasattr(config, 'MAX_LOST_FRAMES') else 5
        self.tracking_state = "SEARCHING"  # SEARCHING, TRACKING, LOST
        self.stable_frames = 0  # 稳定跟踪的帧数
        self.single_led_mode = False  # 是否在单LED模式
        self.zero_led_mode = False  # 是否在零LED模式
        self.partial_led_count = 0  # 部分检测到的LED数量

    def detect(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int]], Optional[np.ndarray]]:
        """
        检测图像中的红外LED

        Returns:
            (LED中心点列表, 二值图像)
        """
        # 根据跟踪状态自适应调整检测参数
        if self.tracking_state == "TRACKING" and self.stable_frames > config.STABLE_FRAMES_THRESHOLD:
            # 稳定跟踪状态：使用更宽松的参数（减少误丢失）
            adaptive_circularity = config.MIN_CIRCULARITY * 0.6
            adaptive_aspect_ratio = config.MAX_ASPECT_RATIO * 1.4
            adaptive_contrast = config.MIN_CONTRAST_RATIO * 0.7
            adaptive_local_max = config.LOCAL_MAX_THRESHOLD * 0.8
            adaptive_brightness_factor = config.CENTER_BRIGHTNESS_FACTOR * 0.7
            use_relaxed = True
        elif self.tracking_state == "LOST":
            # LOST状态：使用极度宽松的参数以便快速恢复
            # 几乎只依靠亮度和面积过滤，其他条件大幅放宽
            adaptive_circularity = config.MIN_CIRCULARITY * 0.3  # 降到30%
            adaptive_aspect_ratio = config.MAX_ASPECT_RATIO * 2.0  # 提高到200%
            adaptive_contrast = config.MIN_CONTRAST_RATIO * 0.5  # 降到50%
            adaptive_local_max = config.LOCAL_MAX_THRESHOLD * 0.6  # 降到60%
            adaptive_brightness_factor = config.CENTER_BRIGHTNESS_FACTOR * 0.5  # 降到50%
            use_relaxed = True
            if config.SHOW_DEBUG_INFO and self.led_lost_counter % 30 == 1:
                print(f"\n  [LOST模式] 使用极度宽松参数搜索...")
        else:
            # 搜索或初始状态：使用标准参数
            adaptive_circularity = config.MIN_CIRCULARITY
            adaptive_aspect_ratio = config.MAX_ASPECT_RATIO
            adaptive_contrast = config.MIN_CONTRAST_RATIO
            adaptive_local_max = config.LOCAL_MAX_THRESHOLD
            adaptive_brightness_factor = config.CENTER_BRIGHTNESS_FACTOR
            use_relaxed = False

        # 降噪处理
        frame_denoised = self._denoise_frame(frame)

        # 提取亮度信息
        brightness = self._extract_brightness(frame_denoised)

        # 阈值化
        _, binary = cv2.threshold(brightness, self.brightness_threshold, 255, cv2.THRESH_BINARY)

        # 形态学降噪
        binary = self._morphological_processing(binary)

        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 筛选候选LED
        led_candidates = self._filter_candidates(
            contours, brightness,
            adaptive_circularity, adaptive_aspect_ratio,
            adaptive_contrast, adaptive_local_max,
            adaptive_brightness_factor
        )

        # LED配对验证
        led_candidates = self._pair_leds(led_candidates)

        # 提取LED中心点
        led_centers = [candidate['center'] for candidate in led_candidates]

        # 单LED补全
        led_centers = self._single_led_recovery(led_centers)

        # 时间跟踪和运动预测
        led_centers = self._temporal_tracking(led_centers, use_relaxed)

        # 更新历史位置
        self._update_history(led_centers)

        return led_centers, binary if config.SHOW_BINARY_IMAGE else None

    def _denoise_frame(self, frame):
        """降噪处理"""
        if config.ENABLE_DENOISING:
            if config.DENOISE_METHOD == 'bilateral':
                return cv2.bilateralFilter(
                    frame,
                    config.BILATERAL_D,
                    config.BILATERAL_SIGMA_COLOR,
                    config.BILATERAL_SIGMA_SPACE
                )
            elif config.DENOISE_METHOD == 'nlmeans':
                return cv2.fastNlMeansDenoisingColored(
                    frame, None,
                    config.NLMEANS_H, config.NLMEANS_H,
                    config.NLMEANS_TEMPLATE_SIZE,
                    config.NLMEANS_SEARCH_SIZE
                )
            elif config.DENOISE_METHOD == 'gaussian':
                return cv2.GaussianBlur(
                    frame,
                    (config.GAUSSIAN_KERNEL_SIZE, config.GAUSSIAN_KERNEL_SIZE),
                    config.GAUSSIAN_SIGMA
                )
            elif config.DENOISE_METHOD == 'median':
                return cv2.medianBlur(frame, config.MEDIAN_KERNEL_SIZE)
        return frame

    def _extract_brightness(self, frame):
        """提取亮度信息"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        _, _, v_channel = cv2.split(hsv)
        max_channel = np.max(frame, axis=2)
        return np.maximum(np.maximum(gray, v_channel), max_channel)

    def _morphological_processing(self, binary):
        """形态学处理"""
        if config.ENABLE_MORPHOLOGY:
            kernel = np.ones((config.MORPH_KERNEL_SIZE, config.MORPH_KERNEL_SIZE), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        return binary

    def _filter_candidates(self, contours, brightness, adaptive_circularity,
                          adaptive_aspect_ratio, adaptive_contrast,
                          adaptive_local_max, adaptive_brightness_factor):
        """筛选候选LED"""
        led_candidates = []

        if config.SHOW_DEBUG_INFO and len(contours) > 0:
            print(f"\n检测到 {len(contours)} 个轮廓:")

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if config.SHOW_DEBUG_INFO:
                print(f"  轮廓 {i+1}: 面积={area:.1f}", end='')

            # 面积过滤
            if not (self.min_area < area < self.max_area):
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 面积{'太小' if area <= self.min_area else '太大'}")
                continue

            # 圆度检查
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 周长为0")
                continue

            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity < adaptive_circularity:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 圆度={circularity:.2f}")
                continue

            # 计算质心
            M = cv2.moments(contour)
            if M["m00"] == 0:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 无效矩")
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            if not (0 <= cy < brightness.shape[0] and 0 <= cx < brightness.shape[1]):
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 超出边界")
                continue

            # 中心亮度检查
            center_brightness = brightness[cy, cx]
            if center_brightness < self.brightness_threshold * adaptive_brightness_factor:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 中心亮度={center_brightness}")
                continue

            # 长宽比检查
            rect = cv2.minAreaRect(contour)
            width, height = rect[1]
            if width == 0 or height == 0:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 尺寸无效")
                continue

            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > adaptive_aspect_ratio:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 长宽比={aspect_ratio:.2f}")
                continue

            # 对比度检查
            roi_size = int(np.sqrt(area) * 3)
            roi_size = max(roi_size, 10)

            y1 = max(0, cy - roi_size)
            y2 = min(brightness.shape[0], cy + roi_size)
            x1 = max(0, cx - roi_size)
            x2 = min(brightness.shape[1], cx + roi_size)

            roi = brightness[y1:y2, x1:x2]
            roi_mean = np.mean(roi)
            contrast_ratio = center_brightness / (roi_mean + 1)

            if contrast_ratio < adaptive_contrast:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 对比度={contrast_ratio:.2f}")
                continue

            # 局部最亮点检查
            local_size = max(3, int(np.sqrt(area)))
            ly1 = max(0, cy - local_size)
            ly2 = min(brightness.shape[0], cy + local_size)
            lx1 = max(0, cx - local_size)
            lx2 = min(brightness.shape[1], cx + local_size)

            local_roi = brightness[ly1:ly2, lx1:lx2]
            max_in_local = np.max(local_roi)

            if center_brightness < max_in_local * adaptive_local_max:
                if config.SHOW_DEBUG_INFO:
                    print(f" [X] 非局部最亮({center_brightness}/{max_in_local})")
                continue

            # 计算质量评分
            quality_score = (
                circularity * 0.25 +
                (center_brightness / 255.0) * 0.25 +
                (1.0 / aspect_ratio) * 0.15 +
                min(contrast_ratio / 5.0, 1.0) * 0.15
            )

            # 运动预测加权
            if config.ENABLE_MOTION_PREDICTION and self.last_led_positions is not None and self.led_velocity is not None:
                predicted_positions = []
                for last_pos in self.last_led_positions:
                    pred_x = last_pos[0] + self.led_velocity[0]
                    pred_y = last_pos[1] + self.led_velocity[1]
                    predicted_positions.append((pred_x, pred_y))

                min_dist_to_prediction = float('inf')
                for pred_pos in predicted_positions:
                    dist = np.sqrt((cx - pred_pos[0])**2 + (cy - pred_pos[1])**2)
                    min_dist_to_prediction = min(min_dist_to_prediction, dist)

                # LOST状态下加分更多，帮助快速恢复
                max_bonus = 0.4 if self.tracking_state == "LOST" else 0.25
                if min_dist_to_prediction < config.PREDICTION_RADIUS:
                    proximity_score = (1.0 - min_dist_to_prediction / config.PREDICTION_RADIUS) * max_bonus
                    quality_score += proximity_score
                    if config.SHOW_DEBUG_INFO:
                        print(f" [预测+{proximity_score:.2f}]", end='')

            led_candidates.append({
                'center': (cx, cy),
                'quality': quality_score,
                'brightness': center_brightness,
                'circularity': circularity,
                'contrast': contrast_ratio
            })

            if config.SHOW_DEBUG_INFO:
                print(f" [OK] 质量={quality_score:.2f}")

        # 按质量排序
        led_candidates.sort(key=lambda x: x['quality'], reverse=True)

        # 根据跟踪状态调整保留的候选数量
        # LOST状态保留更多候选（提高50%），增加恢复机会
        max_candidates = config.MAX_LED_CANDIDATES
        if self.tracking_state == "LOST":
            max_candidates = int(config.MAX_LED_CANDIDATES * 1.5)

        if len(led_candidates) > max_candidates:
            led_candidates = led_candidates[:max_candidates]

        return led_candidates

    def _pair_leds(self, led_candidates):
        """LED配对验证"""
        # LOST状态下跳过严格配对验证，快速恢复跟踪
        if self.tracking_state == "LOST":
            if config.SHOW_DEBUG_INFO and len(led_candidates) >= self.expected_led_count:
                print(f"\n  [LOST恢复] 跳过配对验证，直接使用检测到的LED")
            return led_candidates[:self.expected_led_count] if len(led_candidates) >= self.expected_led_count else led_candidates

        if not config.ENABLE_LED_PAIRING or len(led_candidates) < self.expected_led_count:
            return led_candidates

        focal_length = self.camera_matrix[0, 0] if self.camera_matrix is not None else self.video_width

        if self.led_mode == 'rectangle_4led' and len(led_candidates) >= 4:
            best_rect_indices, best_rect_score = find_best_rectangle(
                led_candidates,
                self.led_rect_width_mm,
                self.led_rect_height_mm,
                focal_length
            )

            if best_rect_indices is not None:
                selected_candidates = [led_candidates[i] for i in best_rect_indices]
                centers = [c['center'] for c in selected_candidates]
                ordered_centers = order_rectangle_points(centers)

                led_candidates = []
                for center in ordered_centers:
                    for candidate in selected_candidates:
                        if candidate['center'] == center:
                            led_candidates.append(candidate)
                            break

                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [OK] 找到最佳矩形LED配置 (评分: {best_rect_score:.2f})")
            else:
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [!] 未找到合理的矩形配置，使用质量最高的4个LED")
                led_candidates = led_candidates[:4]

        elif self.led_mode == 'line_2led' and len(led_candidates) >= 2:
            best_pair = None
            best_pair_score = 0

            for i in range(len(led_candidates)):
                for j in range(i + 1, len(led_candidates)):
                    led1 = led_candidates[i]
                    led2 = led_candidates[j]

                    dx = led1['center'][0] - led2['center'][0]
                    dy = led1['center'][1] - led2['center'][1]
                    pixel_dist = np.sqrt(dx * dx + dy * dy)

                    min_expected_pixels = (focal_length * self.led_distance_mm) / 1000
                    max_expected_pixels = (focal_length * self.led_distance_mm) / 100

                    if min_expected_pixels * 0.5 < pixel_dist < max_expected_pixels * 2.0:
                        pair_score = led1['quality'] + led2['quality']

                        if pair_score > best_pair_score:
                            best_pair_score = pair_score
                            best_pair = (i, j)

            if best_pair is not None:
                led_candidates = [led_candidates[best_pair[0]], led_candidates[best_pair[1]]]
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [OK] 找到最佳LED配对 (评分: {best_pair_score:.2f})")
            else:
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [!] 未找到合理的LED配对，使用质量最高的2个")
                led_candidates = led_candidates[:2]

        return led_candidates

    def _single_led_recovery(self, led_centers):
        """单LED补全"""
        if (self.led_mode == 'line_2led' and
            config.ENABLE_SINGLE_LED_RECOVERY and
            len(led_centers) == 1 and
            self.led_vector is not None and
            self.last_led_positions is not None and
            len(self.last_led_positions) == 2):

            detected_led = led_centers[0]

            dist_to_led1 = np.sqrt((detected_led[0] - self.last_led_positions[0][0])**2 +
                                   (detected_led[1] - self.last_led_positions[0][1])**2)
            dist_to_led2 = np.sqrt((detected_led[0] - self.last_led_positions[1][0])**2 +
                                   (detected_led[1] - self.last_led_positions[1][1])**2)

            if dist_to_led1 < dist_to_led2:
                estimated_led2 = (
                    int(detected_led[0] + self.led_vector[0]),
                    int(detected_led[1] + self.led_vector[1])
                )
                led_centers = [detected_led, estimated_led2]
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [1LED] 单LED补全: 检测到LED1，推算LED2位置 {estimated_led2}")
            else:
                estimated_led1 = (
                    int(detected_led[0] - self.led_vector[0]),
                    int(detected_led[1] - self.led_vector[1])
                )
                led_centers = [estimated_led1, detected_led]
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [1LED] 单LED补全: 检测到LED2，推算LED1位置 {estimated_led1}")

            self.single_led_mode = True
            self.zero_led_mode = False
            self.led_lost_counter = 0

            # 单LED补全成功，说明至少找到了一个真实LED
            # 状态应该是TRACKING而不是LOST（降低状态切换频率）
            if self.tracking_state != "TRACKING":
                self.tracking_state = "TRACKING"
                self.stable_frames = 1
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [✓] 单LED补全成功，恢复跟踪")
        else:
            self.single_led_mode = False

        return led_centers

    def _temporal_tracking(self, led_centers, use_relaxed):
        """时间跟踪和运动预测"""
        if config.ENABLE_TEMPORAL_TRACKING and self.last_led_positions is not None and len(self.last_led_positions) == self.expected_led_count:
            if len(led_centers) >= self.expected_led_count:
                # 计算参考位置
                reference_positions = []
                for last_pos in self.last_led_positions:
                    if config.ENABLE_MOTION_PREDICTION and self.led_velocity is not None:
                        ref_pos = (
                            last_pos[0] + self.led_velocity[0],
                            last_pos[1] + self.led_velocity[1]
                        )
                    else:
                        ref_pos = last_pos
                    reference_positions.append(ref_pos)

                # 贪心匹配
                matched_centers = []
                used_indices = set()

                for ref_pos in reference_positions:
                    best_dist = float('inf')
                    best_idx = None

                    for i, led_center in enumerate(led_centers):
                        if i in used_indices:
                            continue

                        dist = np.sqrt((led_center[0] - ref_pos[0])**2 + (led_center[1] - ref_pos[1])**2)
                        if dist < best_dist and dist < config.MAX_TRACKING_DISTANCE:
                            best_dist = dist
                            best_idx = i

                    if best_idx is not None:
                        matched_centers.append(led_centers[best_idx])
                        used_indices.add(best_idx)
                    else:
                        break

                # LOST状态下：即使匹配不完美，只要检测到足够数量的LED就尝试恢复
                # 正常状态：必须完美匹配
                can_recover = False
                if len(matched_centers) == self.expected_led_count:
                    can_recover = True
                elif self.tracking_state == "LOST" and len(led_centers) >= self.expected_led_count:
                    # LOST状态下匹配失败，但检测到足够LED，直接使用检测到的LED
                    matched_centers = led_centers[:self.expected_led_count]
                    can_recover = True
                    if config.SHOW_DEBUG_INFO:
                        print(f"\n  [LOST恢复] 匹配失败但检测充足，强制恢复跟踪")

                if can_recover:
                    # 更新速度
                    if config.ENABLE_MOTION_PREDICTION:
                        velocities = []
                        for i in range(len(matched_centers)):
                            vx = matched_centers[i][0] - self.last_led_positions[i][0]
                            vy = matched_centers[i][1] - self.last_led_positions[i][1]
                            velocities.append((vx, vy))

                        avg_vx = sum(v[0] for v in velocities) / len(velocities)
                        avg_vy = sum(v[1] for v in velocities) / len(velocities)

                        if self.led_velocity is not None:
                            alpha = 0.7
                            self.led_velocity = (
                                alpha * avg_vx + (1 - alpha) * self.led_velocity[0],
                                alpha * avg_vy + (1 - alpha) * self.led_velocity[1]
                            )
                        else:
                            self.led_velocity = (avg_vx, avg_vy)

                    led_centers = matched_centers
                    self.led_lost_counter = 0

                    # 从LOST状态恢复：需要连续稳定检测才能完全恢复
                    if self.tracking_state == "LOST":
                        self.stable_frames = 1  # 重新开始计数
                        if config.SHOW_DEBUG_INFO:
                            print(f"\n  [✓] 恢复检测，正在验证稳定性...")
                    else:
                        self.stable_frames += 1

                    # 只要能检测到全部LED就进入TRACKING状态（降低恢复门槛）
                    self.tracking_state = "TRACKING"
                    self.zero_led_mode = False

                    # 更新LED向量
                    if self.led_mode == 'line_2led' and len(matched_centers) >= 2:
                        self.led_vector = (
                            matched_centers[1][0] - matched_centers[0][0],
                            matched_centers[1][1] - matched_centers[0][1]
                        )
                        self.led_distance = np.sqrt(self.led_vector[0]**2 + self.led_vector[1]**2)

                    if config.SHOW_DEBUG_INFO and use_relaxed:
                        print(f"\n  [OK] 跟踪成功 [稳定x{self.stable_frames}]")
                        print(f"  [RELAX] 使用宽松检测模式")

            elif len(led_centers) == 0:
                # 零LED模式
                if config.ENABLE_CONTINUOUS_OUTPUT:
                    if self.led_velocity is not None and self.last_led_positions is not None:
                        predicted_centers = []
                        for last_pos in self.last_led_positions:
                            pred_x = int(last_pos[0] + self.led_velocity[0] * (self.led_lost_counter + 1))
                            pred_y = int(last_pos[1] + self.led_velocity[1] * (self.led_lost_counter + 1))
                            predicted_centers.append((pred_x, pred_y))
                        led_centers = predicted_centers

                        self.zero_led_mode = True
                        self.single_led_mode = False

                        if config.SHOW_DEBUG_INFO:
                            print(f"\n  [0LED] 零LED模式: 完全预测 (丢失 {self.led_lost_counter + 1} 帧)")
                    elif self.last_led_positions is not None:
                        led_centers = self.last_led_positions
                        self.zero_led_mode = True
                        self.single_led_mode = False

                        if config.SHOW_DEBUG_INFO:
                            print(f"\n  [!] 零LED模式: 使用历史位置 (丢失 {self.led_lost_counter + 1} 帧)")

                self.led_lost_counter += 1

                if self.led_lost_counter >= self.max_lost_frames:
                    if config.ENABLE_CONTINUOUS_OUTPUT:
                        self.tracking_state = "LOST"
                        if config.SHOW_DEBUG_INFO and self.led_lost_counter == self.max_lost_frames:
                            print(f"\n  [!] 超过最大丢失帧数，但继续输出预测坐标")
                    else:
                        self.tracking_state = "SEARCHING"
                        self.stable_frames = 0
                        self.led_velocity = None
                        self.led_vector = None
                        self.zero_led_mode = False
                        self.single_led_mode = False
                        if config.SHOW_DEBUG_INFO:
                            print(f"\n  [X] 目标完全丢失，重新搜索")
                else:
                    self.tracking_state = "LOST"
                    self.stable_frames = 0
            else:
                # 检测到部分LED（不足期望数量）
                self.led_lost_counter += 1

                # 快速进入LOST状态以启用宽松检测（3帧即可）
                # 这样可以更快地使用宽松参数搜索LED
                if self.led_lost_counter >= 3 and self.tracking_state != "LOST":
                    self.tracking_state = "LOST"
                    self.stable_frames = 0
                    if config.SHOW_DEBUG_INFO:
                        print(f"\n  [!] LED部分丢失，进入LOST搜索模式 (丢失 {self.led_lost_counter} 帧)")
                elif self.led_lost_counter < 3:
                    # 短暂丢失（1-2帧），保持TRACKING状态
                    if config.SHOW_DEBUG_INFO and self.led_lost_counter == 1:
                        print(f"\n  [!] LED短暂丢失...")
        else:
            # 没有历史记录的情况（首次检测或重新搜索）
            if len(led_centers) >= self.expected_led_count:
                # 检测到足够的LED，立即进入TRACKING状态
                self.tracking_state = "TRACKING"
                self.zero_led_mode = False
                self.single_led_mode = False
                self.led_lost_counter = 0
                self.stable_frames = 1

                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [OK] 首次检测成功，开始跟踪 ({len(led_centers)} LEDs)")
            elif len(led_centers) == 0:
                # 完全没有检测到
                self.tracking_state = "SEARCHING"
                self.zero_led_mode = False
                self.single_led_mode = False
            else:
                # 检测到部分LED，标记为LOST但继续尝试
                self.tracking_state = "LOST"
                self.partial_led_count = len(led_centers)
                if config.SHOW_DEBUG_INFO:
                    print(f"\n  [!] 检测到部分LED ({len(led_centers)}/{self.expected_led_count})")

        return led_centers

    def _update_history(self, led_centers):
        """更新历史位置"""
        if len(led_centers) >= self.expected_led_count:
            current_centers = led_centers[:self.expected_led_count]

            if not self.zero_led_mode:
                # 计算速度
                if self.last_led_positions is not None and config.ENABLE_MOTION_PREDICTION and len(self.last_led_positions) == len(current_centers):
                    velocities = []
                    for i in range(len(current_centers)):
                        vx = current_centers[i][0] - self.last_led_positions[i][0]
                        vy = current_centers[i][1] - self.last_led_positions[i][1]
                        velocities.append((vx, vy))

                    avg_vx = sum(v[0] for v in velocities) / len(velocities)
                    avg_vy = sum(v[1] for v in velocities) / len(velocities)

                    if self.led_velocity is not None:
                        alpha = config.VELOCITY_SMOOTHING_ALPHA if hasattr(config, 'VELOCITY_SMOOTHING_ALPHA') else 0.7
                        self.led_velocity = (
                            alpha * avg_vx + (1 - alpha) * self.led_velocity[0],
                            alpha * avg_vy + (1 - alpha) * self.led_velocity[1]
                        )
                    else:
                        self.led_velocity = (avg_vx, avg_vy)

                # 更新LED向量和几何形状
                if not self.single_led_mode:
                    if self.led_mode == 'line_2led' and len(current_centers) >= 2:
                        self.led_vector = (
                            current_centers[1][0] - current_centers[0][0],
                            current_centers[1][1] - current_centers[0][1]
                        )
                        self.led_distance = np.sqrt(self.led_vector[0]**2 + self.led_vector[1]**2)
                    elif self.led_mode == 'rectangle_4led' and len(current_centers) >= 4:
                        self.led_rect_shape = {
                            'width': np.sqrt((current_centers[1][0] - current_centers[0][0])**2 +
                                           (current_centers[1][1] - current_centers[0][1])**2),
                            'height': np.sqrt((current_centers[3][0] - current_centers[0][0])**2 +
                                            (current_centers[3][1] - current_centers[0][1])**2)
                        }

                self.last_led_positions = current_centers

                if self.zero_led_mode or self.single_led_mode:
                    self.zero_led_mode = False
                    self.single_led_mode = False
                    if config.SHOW_DEBUG_INFO:
                        print(f"\n  [OK] 重新检测到LED，退出预测模式")

            if not self.zero_led_mode:
                self.led_lost_counter = 0

    def get_tracking_state(self):
        """获取跟踪状态"""
        return {
            'state': self.tracking_state,
            'stable_frames': self.stable_frames,
            'single_led_mode': self.single_led_mode,
            'zero_led_mode': self.zero_led_mode,
            'led_velocity': self.led_velocity,
            'led_vector': self.led_vector,
            'led_distance': self.led_distance,
            'last_led_positions': self.last_led_positions
        }
