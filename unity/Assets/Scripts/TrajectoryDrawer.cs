using UnityEngine;
using System.Collections.Generic;

public class TrajectoryDrawer : MonoBehaviour
{
    public LineRenderer line;
    List<Vector3> points = new List<Vector3>();

    [Header("Trajectory density")]
    [Tooltip("Minimum point spacing (higher is sparser)")]
    public float minDistance = 0.05f;

    [Tooltip("Smoothing factor (higher follows motion faster)")]
    public float smoothFactor = 0.8f;

    Vector3 last;

    public enum SpacePreset { Custom, Small, Medium, Large, ExtraLarge }

    [Header("Space presets")]
    [Tooltip("Select a preset to apply it in the Editor")]
    public SpacePreset selectedPreset = SpacePreset.Medium;

    private SpacePreset lastAppliedPreset = SpacePreset.Medium;

    void Start()
    {
        if (line == null)
            line = GetComponent<LineRenderer>();

        line.positionCount = 0;
    }

    void Update()
    {
        #if UNITY_EDITOR
        if (selectedPreset != lastAppliedPreset && selectedPreset != SpacePreset.Custom)
        {
            ApplyPreset(selectedPreset);
            lastAppliedPreset = selectedPreset;
        }
        #endif
    }

    /// <summary>Apply a preset for the intended working distance.</summary>
    public void ApplyPreset(SpacePreset preset)
    {
        switch (preset)
        {
            case SpacePreset.Small:
                scaleX = 0.02f;
                scaleY = 0.025f;
                scaleZ = 0.02f;
                minDistance = 0.02f;
                Debug.Log("Applied small-space preset (20-40 cm)");
                break;

            case SpacePreset.Medium:
                scaleX = 0.04f;
                scaleY = 0.05f;
                scaleZ = 0.04f;
                minDistance = 0.05f;
                Debug.Log("Applied medium-space preset (40-80 cm)");
                break;

            case SpacePreset.Large:
                scaleX = 0.08f;
                scaleY = 0.1f;
                scaleZ = 0.1f;
                minDistance = 0.1f;
                Debug.Log("Applied large-space preset (80-150 cm)");
                break;

            case SpacePreset.ExtraLarge:
                scaleX = 0.15f;
                scaleY = 0.18f;
                scaleZ = 0.08f;
                minDistance = 0.15f;
                Debug.Log("Applied extra-large-space preset (150 cm or more)");
                break;
        }

        presetTip = GetPresetDescription(preset);
    }

    private string GetPresetDescription(SpacePreset preset)
    {
        switch (preset)
        {
            case SpacePreset.Small: return "Current: small space (20-40 cm)";
            case SpacePreset.Medium: return "Current: medium space (40-80 cm)";
            case SpacePreset.Large: return "Current: large space (80-150 cm)";
            case SpacePreset.ExtraLarge: return "Current: extra-large space (150 cm or more)";
            default: return "Current: custom settings";
        }
    }

    [Header("Coordinate scales")]
    [Tooltip("Scale for left/right motion (X)")]
    public float scaleX = 0.01f;

    [Tooltip("Scale for vertical motion (Y)")]
    public float scaleY = 0.01f;

    [Tooltip("Scale for depth motion (Z)")]
    public float scaleZ = 0.02f;

    [Header("Preset reference")]
    [Tooltip("Small: 0.02/0.025/0.01 | Medium: 0.04/0.05/0.02 | Large: 0.08/0.1/0.04")]
    public string presetTip = "Current: medium-space preset";

    public Vector3 MapToUnity(float x, float y, float z)
    {
        return new Vector3(
            x * scaleX,
            -z * scaleY,
            -y * scaleZ
        );
    }

    public void AddPoint(Vector3 p)
    {
        if (points.Count == 0)
        {
            last = p;
            points.Add(p);
            line.positionCount = 1;
            line.SetPosition(0, p);
            return;
        }

        Vector3 s = Vector3.Lerp(last, p, smoothFactor);

        if (Vector3.Distance(s, last) < minDistance) return;

        last = s;
        points.Add(s);

        line.positionCount++;
        line.SetPosition(line.positionCount - 1, s);
    }

    /// <summary>Remove all rendered trajectory points.</summary>
    [ContextMenu("Clear trajectory")]
    public void ClearTrajectory()
    {
        points.Clear();
        if (line != null)
        {
            line.positionCount = 0;
        }
        Debug.Log("Trajectory cleared");
    }

    /// <summary>Summarize the bounding range of accepted points.</summary>
    public string GetStatistics()
    {
        if (points.Count < 2) return "Insufficient points";

        Vector3 min = points[0];
        Vector3 max = points[0];

        foreach (var p in points)
        {
            min = Vector3.Min(min, p);
            max = Vector3.Max(max, p);
        }

        Vector3 range = max - min;
        return $"Points:{points.Count} | range X:{range.x:F2} Y:{range.y:F2} Z:{range.z:F2}";
    }
}
