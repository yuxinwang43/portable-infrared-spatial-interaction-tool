# Prototype evaluation notes

The following values summarize the reported evaluation of the prototype. They characterize the tested setup but are not reproduced by an automated test suite in this repository.

| Metric | Goal | Reported observation | Method described in report |
| --- | --- | --- | --- |
| End-to-end latency | At most 120 ms | 72 ms in optimized mode; 95 ms in normal mode | 1,000 fps high-speed video and timestamp comparison |
| Static positioning error | 10-20 mm | 12 mm at 30-90 cm; 18 mm at 90-120 cm | Repeated fixed-point measurements with laser-rangefinder reference |
| Refresh rate | Up to 60 Hz | Stable 58 Hz under 2K input | Unity Profiler |
| Effective field of view | 20-120 degrees | 25-115 degrees | Calibration-plate measurement |
| Complex-curve reproduction | Not specified | 92% | Spatial-drawing demonstration; calculation details not supplied |
| PCB stability | No short circuit; frequency drift at most 1% | Six-hour operation; 0.3% frequency fluctuation | Continuous operation test |

The reported emitter dimensions are 3.91 x 3.34 x 4.15 cm. The published hardware files are design artifacts; fabrication and camera calibration are needed before a fresh evaluation.

## Limitations

- Strong ambient light and reflections can disrupt marker detection.
- Occlusion is difficult for a monocular camera, and depth error rises with distance.
- The repository does not contain raw recordings, calibration files, or a benchmark harness, so the reported numbers cannot be independently reproduced from source alone.
- The included Unity scene demonstrates position-driven drawing. Orientation data may be transmitted by Python, but the scene does not use it to control an object.
