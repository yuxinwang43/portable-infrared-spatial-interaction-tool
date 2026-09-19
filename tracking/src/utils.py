#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
包含绘图和几何计算等辅助函数
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from itertools import combinations


def draw_dashed_line(img, pt1, pt2, color, thickness=1, gap=10):
    """绘制虚线"""
    dist = np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)
    pts = []
    for i in np.arange(0, dist, gap):
        r = i / dist
        x = int((pt1[0] * (1 - r) + pt2[0] * r))
        y = int((pt1[1] * (1 - r) + pt2[1] * r))
        pts.append((x, y))

    for i in range(0, len(pts) - 1, 2):
        cv2.line(img, pts[i], pts[i + 1] if i + 1 < len(pts) else pts[-1], color, thickness)


def order_rectangle_points(points):
    """
    将4个点按矩形顺序排列：左上、右上、右下、左下

    Args:
        points: 4个点的列表 [(x, y), ...]

    Returns:
        排序后的点列表 [左上, 右上, 右下, 左下]
    """
    if len(points) != 4:
        return points

    # 计算质心
    center_x = sum(p[0] for p in points) / 4
    center_y = sum(p[1] for p in points) / 4

    # 按象限分类
    top_left = None
    top_right = None
    bottom_left = None
    bottom_right = None

    for point in points:
        x, y = point
        if x < center_x and y < center_y:
            top_left = point
        elif x >= center_x and y < center_y:
            top_right = point
        elif x < center_x and y >= center_y:
            bottom_left = point
        else:
            bottom_right = point

    # 按顺序返回：左上、右上、右下、左下
    ordered = []
    for p in [top_left, top_right, bottom_right, bottom_left]:
        if p is not None:
            ordered.append(p)

    # 如果某些点缺失，尝试用距离排序
    if len(ordered) < 4:
        # 按照到左上角的距离排序
        points_sorted = sorted(points, key=lambda p: (p[0]**2 + p[1]**2))
        return points_sorted

    return ordered


def find_best_rectangle(candidates, expected_width, expected_height, focal_length):
    """
    从候选点中找到最佳的矩形配置

    Args:
        candidates: 候选LED列表
        expected_width: 期望的矩形宽度（毫米）
        expected_height: 期望的矩形高度（毫米）
        focal_length: 相机焦距（像素）

    Returns:
        (最佳4个点的索引, 评分) 或 (None, 0)
    """
    if len(candidates) < 4:
        return None, 0

    best_indices = None
    best_score = 0

    # 尝试所有4个点的组合
    for combo in combinations(range(len(candidates)), 4):
        points = [candidates[i]['center'] for i in combo]

        # 计算这4个点是否能形成矩形
        # 1. 计算质心
        center_x = sum(p[0] for p in points) / 4
        center_y = sum(p[1] for p in points) / 4

        # 2. 计算每个点到质心的距离（矩形的对角线应该相等）
        distances = [np.sqrt((p[0] - center_x)**2 + (p[1] - center_y)**2) for p in points]
        avg_dist = np.mean(distances)
        dist_std = np.std(distances)

        # 对角线长度应该相近（标准差小）
        if dist_std > avg_dist * 0.3:  # 允许30%的偏差
            continue

        # 3. 排序点以计算边长
        ordered_points = order_rectangle_points(points)
        if len(ordered_points) < 4:
            continue

        # 计算四条边的长度
        edges = []
        for i in range(4):
            p1 = ordered_points[i]
            p2 = ordered_points[(i + 1) % 4]
            edge_len = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            edges.append(edge_len)

        # 对边应该相等
        width1, height1, width2, height2 = edges
        if abs(width1 - width2) > max(width1, width2) * 0.3:  # 宽度偏差
            continue
        if abs(height1 - height2) > max(height1, height2) * 0.3:  # 高度偏差
            continue

        # 计算长宽比
        measured_width = (width1 + width2) / 2
        measured_height = (height1 + height2) / 2
        aspect_ratio = measured_width / (measured_height + 1e-6)
        expected_aspect_ratio = expected_width / expected_height

        # 检查长宽比是否匹配
        aspect_diff = abs(aspect_ratio - expected_aspect_ratio) / expected_aspect_ratio
        if aspect_diff > 0.5:  # 允许50%的偏差
            continue

        # 计算综合评分
        quality_sum = sum(candidates[i]['quality'] for i in combo)
        geometry_score = 1.0 / (1.0 + dist_std / avg_dist)  # 对角线一致性
        aspect_score = 1.0 / (1.0 + aspect_diff)  # 长宽比匹配度

        total_score = quality_sum * 0.5 + geometry_score * 0.25 + aspect_score * 0.25

        if total_score > best_score:
            best_score = total_score
            best_indices = combo

    return best_indices, best_score
