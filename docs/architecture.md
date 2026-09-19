# Architecture and data interface

The system joins a marker-tracking process to a Unity visualization scene. The Python process reads camera frames, detects bright IR LED candidates, estimates a position or pose, and sends results through UDP. Unity receives the latest packet on its main thread and appends a mapped point to the trajectory.

## Vision pipeline

The supplied tracker supports `line_2led` and `rectangle_4led` modes. Candidate detection uses brightness segmentation and geometric filters such as area, circularity, aspect ratio, and local contrast. Temporal association and motion prediction help maintain tracking through brief detection gaps. In four-marker mode, OpenCV `solvePnP` estimates the marker pose from the known rectangle dimensions and camera intrinsics. Two-marker mode estimates depth from the known LED separation and image-space separation.

Camera parameters in `tracking/config.py` are prototype defaults. For quantitative use, calibrate the actual camera and set its intrinsics and distortion coefficients. The monocular setup is sensitive to occlusion, reflections, and increasing depth.

## UDP packet

The tracker sends a UTF-8 JSON object to `UNITY_IP:UNITY_PORT` (default `127.0.0.1:5005`). A position packet has this shape:

```json
{"x": 12.4, "y": -8.1, "z": 430.0}
```

The numeric position fields are in millimetres. In four-marker mode, optional `roll`, `pitch`, and `yaw` fields may be added. The included Unity `UDPReceiver` consumes `x`, `y`, and `z` for trajectory rendering. It keeps only the latest queued packet to limit display lag; it does not currently apply the orientation fields.

## Unity visualization

The archived `MainScene` contains a `UDPReceiver` and `TrajectoryDrawer`. The receiver parses the JSON packet and calls `TrajectoryDrawer.MapToUnity`. The mapping is:

```text
unity_x =  x * scaleX
unity_y = -z * scaleY
unity_z = -y * scaleZ
```

The scale factors are adjustable in the Unity Inspector. The drawer uses `Vector3.Lerp` for smoothing, rejects points closer than `minDistance`, and appends accepted points to a `LineRenderer`. The standalone `CoordinateDebugger` script can be attached to a TextMeshPro UI element for live coordinate inspection; it is not required by the archived main scene.

## Scope of the published source

The Unity scene references the included project scripts and standard Unity package assets. Generated Unity `Library`, `Temp`, `Logs`, and local Python `.venv` files are excluded. A third-party demonstration asset pack is excluded because it is not needed by the main scene and has separate distribution terms.
