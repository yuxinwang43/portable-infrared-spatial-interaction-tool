# -*- coding: utf-8 -*-
"""
配置文件 - 红外LED追踪系统
在此文件中调整所有参数
"""

# ========== 硬件参数 ==========

# LED配置模式
# 'rectangle_4led': 矩形四LED布局（推荐，可追踪姿态）
# 'line_2led': 直线双LED布局（仅追踪位置）
LED_MODE = 'rectangle_4led'

# 矩形LED配置（当 LED_MODE = 'rectangle_4led' 时使用）
# 矩形的宽度和高度（毫米）
LED_RECT_WIDTH_MM = 30.0   # 3.0cm
LED_RECT_HEIGHT_MM = 25.0  # 2.5cm

# 传统双LED配置（当 LED_MODE = 'line_2led' 时使用）
# 两个红外LED之间的实际距离（毫米）
# 此参数仅在 line_2led 模式下使用，rectangle_4led 模式下不需要
# 如果你只用 rectangle_4led 模式，可以注释掉此行（代码会使用默认值50.0）
LED_DISTANCE_MM = 50.0

# 摄像头设备ID
# 0 = 默认摄像头
CAMERA_ID = 0

# 摄像头倾斜角度（度）
# 摄像头挂在胸前向下倾斜的角度
CAMERA_TILT_ANGLE = 0


# ========== LED检测参数（针对2mm小型LED优化）==========

# 亮度阈值（0-255）
# [*] 800-2500nm黑玻滤片下，背景极暗，需要极低阈值
# 黑玻滤片阻挡几乎所有光线，只有LED会发光
# 配合圆度和中心亮度过滤，可以稍微提高以减少噪声
# [!] 如果二值化噪声太多，逐步提高此值：30 -> 40 -> 50 -> 60
BRIGHTNESS_THRESHOLD = 50

# LED区域最小面积（像素）
# 小型LED在20-50cm距离投影较小，降低最小面积
# 50cm距离：约15-30像素
# 20cm距离：约80-150像素
# 极小值以检测非常小的LED点
MIN_LED_AREA = 20

# LED区域最大面积（像素）
# [*] 黑玻滤片极长曝光模式下光晕非常大，大幅增加上限
# 极长曝光会导致LED光晕扩散很大
MAX_LED_AREA = 4000

# ========== LED智能过滤参数（多重验证）==========

# 【过滤1】圆度阈值（0-1，1为完美圆形）
# LED通常是圆形的，噪声可能是不规则形状
# [!] 运动模糊和光晕会影响形状，不要设置太高
# 推荐值：0.2-0.35（降低以提高检测率）
MIN_CIRCULARITY = 0.20

# 【过滤2】中心亮度倍数
# LED中心亮度应该是阈值的多少倍
# 真正的LED中心应该很亮，噪声通常亮度较低
# 推荐值：1.3-2.0（降低以提高检测率）
CENTER_BRIGHTNESS_FACTOR = 1.5

# 【过滤3】最大长宽比
# LED应该接近圆形，长宽比接近1.0
# [!] 运动模糊会导致拉长，允许较大的长宽比
# 推荐值：3.0-5.0（提高以容忍运动模糊）
MAX_ASPECT_RATIO = 4.5

# 【过滤4】最小对比度比率
# LED与周围背景的亮度对比度
# 推荐值：1.3-2.0（降低以提高检测率）
MIN_CONTRAST_RATIO = 1.5

# 【过滤5】局部最亮点阈值
# LED中心应该是局部最亮的点（或非常接近）
# 值为局部最大值的百分比（0.0-1.0）
# [!] 光晕可能导致边缘更亮，降低要求
# 推荐值：0.6-0.8（降低以提高检测率）
LOCAL_MAX_THRESHOLD = 0.65

# 【过滤6】最大候选LED数量
# 在所有候选中最多保留多少个（按质量排序）
# 矩形4LED模式：建议8-12（需要找到4个点）
# 直线2LED模式：建议4-8
MAX_LED_CANDIDATES = 12

# 【过滤7】LED配对验证
# 是否启用LED配对验证（检查两个LED之间的距离是否合理）
# True: 更严格，只接受距离合理的LED对
# False: 更宽松，接受任意两个最亮的点
ENABLE_LED_PAIRING = True

# ========== 时间连续性跟踪（稳定性增强）==========

# 【过滤8】启用时间跟踪
# 基于上一帧的位置来稳定当前帧的检测
# 可以大幅减少闪烁和目标丢失
ENABLE_TEMPORAL_TRACKING = True

# 最大跟踪距离（像素）
# 两帧之间LED移动的最大距离
# 如果超过此距离，认为不是同一个LED
# 推荐值：100-300（提高以适应快速运动）
MAX_TRACKING_DISTANCE = 250

# 最大丢失帧数
# 连续丢失多少帧后才真正认为目标丢失
# 在此期间会使用运动预测或历史位置
# 推荐值：10-20（提高以增强稳定性）
MAX_LOST_FRAMES = 15

# ========== 运动预测（快速移动优化）==========

# 【过滤9】启用运动预测
# 根据LED的运动速度预测下一帧位置
# 特别适合快速移动场景
ENABLE_MOTION_PREDICTION = True

# 预测半径（像素）
# 在预测位置周围多大范围内搜索
# 推荐值：80-150（提高以增强预测能力）
PREDICTION_RADIUS = 120

# ========== 自适应检测（跟踪状态优化）==========

# 稳定帧数阈值
# 连续稳定跟踪多少帧后，启用宽松检测模式
# 推荐值：3-10（降低以更快启用宽松模式）
STABLE_FRAMES_THRESHOLD = 5

# ========== 永不中断输出（关键功能！）==========

# 【核心】启用连续输出模式
# 即使完全丢失LED，也继续输出预测坐标
# 确保中心点坐标永不中断
ENABLE_CONTINUOUS_OUTPUT = True

# 【核心】启用单LED恢复
# 当只检测到1个LED时，根据LED几何关系推算另一个LED的位置
# 大幅提升移动时的稳定性
ENABLE_SINGLE_LED_RECOVERY = True

# 速度平滑系数（0.0-1.0）
# 用于平滑速度计算，避免速度突变
# 0.7 = 70%使用新速度，30%保留旧速度
# 推荐值：0.5-0.8
VELOCITY_SMOOTHING_ALPHA = 0.7


# ========== 视频参数 ==========

# 视频分辨率
# 推荐：1920x1080 (Full HD) - 最佳兼容性和性能平衡
# 可选：1280x720 (HD) - 更快的处理速度
# 可选：3840x2160 (4K) - 需要高端摄像头支持
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# 帧率（30fps - 适应800-2500nm黑玻滤片的极长曝光需求）
# [*] 黑玻滤片几乎完全阻挡可见光，需要30fps以支持更长曝光时间
VIDEO_FPS = 30

# ========== 红外拍摄优化参数（黑玻滤片极限模式）==========
# [***] 针对800-2500nm黑玻滤片优化
# 黑玻滤片阻挡几乎所有可见光（400-700nm），只通过红外光（800-2500nm）
# 需要极限参数才能在极暗环境下看到红外LED

# === 核心参数（自动模式） ===
# 自动曝光：0.25=手动（固定），0.75=自动
AUTO_EXPOSURE = 0.25

# 曝光值：10（极限曝光 - 针对800-2500nm黑玻滤片） [***]
# 黑玻滤片下环境极暗，使用最大可能的曝光值
# 配合30fps可以使用更长的曝光时间
EXPOSURE = 5

# 增益/ISO：255（最大增益 - 黑玻滤片必需） [***]
# 黑玻滤片环境极暗，必须使用最大增益
GAIN = 255

# 亮度：255（最大亮度 - 黑玻滤片必需） [***]
BRIGHTNESS = 255

# 对比度：255（最大对比度 - 增强LED与背景对比） [**]
# 黑玻滤片下需要极高对比度才能突出LED
CONTRAST = 255

# === 启用的自动功能 ===
# 自动白平衡：开启
AUTO_WHITE_BALANCE = True

# 自动对焦：开启
AUTO_FOCUS = True

# === 专用设置 ===
# 缓冲区大小（减少延迟）
BUFFER_SIZE = 1

# 注意：OpenCV会自动选择最佳后端（macOS使用AVFOUNDATION，Windows使用DSHOW）
# 手动设置后端可能导致兼容性问题，因此使用默认自动选择

# ========== 降噪参数（已禁用）==========
# 禁用降噪，使用原生画面

# 是否启用降噪
ENABLE_DENOISING = False

# 降噪方法：'bilateral', 'nlmeans', 'gaussian', 'median'
# bilateral: 双边滤波（推荐，保留边缘）
# nlmeans: 非局部均值去噪（效果最好但最慢）
# gaussian: 高斯模糊（快速但会模糊边缘）
# median: 中值滤波（去除椒盐噪声）
DENOISE_METHOD = 'bilateral'

# 双边滤波参数
BILATERAL_D = 9           # 滤波器直径（越大越慢，推荐5-15）
BILATERAL_SIGMA_COLOR = 75    # 色彩空间标准差（越大越模糊）
BILATERAL_SIGMA_SPACE = 75    # 坐标空间标准差

# 非局部均值去噪参数（如果使用nlmeans）
NLMEANS_H = 10               # 滤波强度（越大越平滑，推荐3-15）
NLMEANS_TEMPLATE_SIZE = 7    # 模板窗口大小
NLMEANS_SEARCH_SIZE = 21     # 搜索窗口大小

# 高斯模糊参数（如果使用gaussian）
GAUSSIAN_KERNEL_SIZE = 5     # 核大小（必须是奇数）
GAUSSIAN_SIGMA = 0           # 标准差（0表示自动计算）

# 中值滤波参数（如果使用median）
MEDIAN_KERNEL_SIZE = 5       # 核大小（必须是奇数）

# 形态学降噪
ENABLE_MORPHOLOGY = False     # 禁用形态学操作，使用原生画面
MORPH_KERNEL_SIZE = 3        # 形态学核大小


# ========== 相机内参（需要标定）==========

# 如果你已经进行了相机标定，可以在这里填入标定结果
# 否则系统会使用估算值

# 是否使用自定义相机内参
USE_CUSTOM_CAMERA_MATRIX = False

# 焦距 (fx, fy) - 4K分辨率下需要更高的焦距值
FOCAL_LENGTH_X = 3000.0
FOCAL_LENGTH_Y = 3000.0

# 主点 (cx, cy) - 通常是图像中心
PRINCIPAL_POINT_X = VIDEO_WIDTH / 2  # 1920
PRINCIPAL_POINT_Y = VIDEO_HEIGHT / 2  # 1080

# 畸变系数 [k1, k2, p1, p2, k3]
# 如果相机有明显畸变，需要进行标定
DISTORTION_COEFFS = [0.0, 0.0, 0.0, 0.0, 0.0]


# ========== 显示参数 ==========

# 是否显示调试信息
# ⚡ 优化：关闭以降低延迟（节省50-100ms/帧）
SHOW_DEBUG_INFO = False

# 是否显示检测的二值图像
# ⚡ 优化：关闭以降低延迟（节省10-30ms/帧）
SHOW_BINARY_IMAGE = False

# 窗口名称
WINDOW_NAME = "IR LED Tracker"


# ========== 高级参数 ==========

# 是否使用卡尔曼滤波平滑坐标
USE_KALMAN_FILTER = False

# 保存视频
SAVE_VIDEO = False
OUTPUT_VIDEO_PATH = "output_tracking.mp4"

# 数据记录
SAVE_COORDINATES = False
COORDINATES_FILE = "coordinates_log.csv"

# ========== Unity 传输设置 ==========

# 是否启用 Unity 数据传输
ENABLE_UNITY_TRANSMISSION = True

# Unity 接收端地址
UNITY_IP = "127.0.0.1"
UNITY_PORT = 5005

# 是否发送姿态数据（仅在 rectangle_4led 模式下有效）
SEND_ORIENTATION = True

# 是否发送时间戳（帮助Unity进行延迟补偿）
SEND_TIMESTAMP = True

# ========== 低延迟优化设置 ==========

# 低延迟模式（最小化Unity传输延迟）
# 启用后会：
# 1. 禁用卡尔曼滤波（减少1-2帧延迟）
# 2. 最小化可视化开销
# 3. 优化socket发送
LOW_LATENCY_MODE = False

# 注意：即使禁用此模式，也建议关闭 SHOW_BINARY_IMAGE 以减少延迟
