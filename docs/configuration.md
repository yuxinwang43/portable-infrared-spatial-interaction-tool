# Tracker configuration

Edit `tracking/config.py` before running the tracker. The file is the original prototype configuration, with comments retained from the source archive. The values below explain the main controls in English.

| Setting | Purpose | Supplied value |
| --- | --- | --- |
| `LED_MODE` | `rectangle_4led` for pose, or `line_2led` for position | `rectangle_4led` |
| `LED_RECT_WIDTH_MM`, `LED_RECT_HEIGHT_MM` | Physical dimensions of the four-marker rectangle | 30 mm, 25 mm |
| `LED_DISTANCE_MM` | Physical separation in two-marker mode | 50 mm |
| `CAMERA_ID` | OpenCV camera index | 0 |
| `CAMERA_TILT_ANGLE` | Camera mounting tilt in degrees | 0 |
| `VIDEO_WIDTH`, `VIDEO_HEIGHT`, `VIDEO_FPS` | Requested capture format | 1920 x 1080 at 30 fps |
| `BRIGHTNESS_THRESHOLD` | Initial segmentation threshold | 50 |
| `MIN_LED_AREA`, `MAX_LED_AREA` | Candidate area bounds in pixels | 20, 4000 |
| `USE_CUSTOM_CAMERA_MATRIX` | Use manually supplied intrinsics | `False` |
| `ENABLE_UNITY_TRANSMISSION` | Send tracking data to Unity | `True` |
| `UNITY_IP`, `UNITY_PORT` | UDP destination | `127.0.0.1`, `5005` |

Camera exposure and gain settings are hardware dependent. If markers are not detected, inspect the live image, confirm camera permissions and IR visibility, and tune exposure before lowering detection thresholds. For reliable depth or pose measurements, calibrate the camera and replace the estimated intrinsics with measured values.

`SHOW_DEBUG_INFO`, `SHOW_BINARY_IMAGE`, `SAVE_VIDEO`, and `SAVE_COORDINATES` control optional diagnostics and recordings. Recorded outputs are ignored by Git.
