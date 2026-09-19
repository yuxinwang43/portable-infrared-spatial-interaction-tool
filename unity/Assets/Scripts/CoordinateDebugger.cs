using UnityEngine;
using TMPro;

/// <summary>Displays raw and Unity coordinates with observed ranges.</summary>
public class CoordinateDebugger : MonoBehaviour
{
    [Header("References")]
    public UDPReceiver receiver;
    public TrajectoryDrawer drawer;

    [Header("Display settings")]
    public bool showRawCoordinates = true;
    public bool showUnityCoordinates = true;
    public bool showStatistics = true;

    private Vector3 rawMin = Vector3.positiveInfinity;
    private Vector3 rawMax = Vector3.negativeInfinity;
    private Vector3 unityMin = Vector3.positiveInfinity;
    private Vector3 unityMax = Vector3.negativeInfinity;

    private Vector3 lastRawPos;
    private Vector3 lastUnityPos;

    private TextMeshProUGUI textDisplay;

    void Start()
    {
        textDisplay = GetComponent<TextMeshProUGUI>();
        if (textDisplay == null)
        {
            Debug.LogError("CoordinateDebugger requires a TextMeshProUGUI component.");
        }
    }

    void Update()
    {
        if (textDisplay == null) return;

        string info = "<b><color=yellow>🔍 Coordinate diagnostics</color></b>\n\n";

        if (showRawCoordinates)
        {
            info += "<color=cyan>Raw coordinates (mm)</color>\n";
            info += $"Current: X={lastRawPos.x:F1}  Y={lastRawPos.y:F1}  Z={lastRawPos.z:F1}\n\n";
        }

        if (showUnityCoordinates)
        {
            info += "<color=lime>Unity coordinates</color>\n";
            info += $"Current: X={lastUnityPos.x:F3}  Y={lastUnityPos.y:F3}  Z={lastUnityPos.z:F3}\n\n";
        }

        if (showStatistics)
        {
            info += "<color=orange>Coordinate ranges</color>\n";
            info += "<color=cyan>Raw coordinate range (mm):</color>\n";
            info += $"  X: {rawMin.x:F1} ~ {rawMax.x:F1}  (Range: {rawMax.x - rawMin.x:F1})\n";
            info += $"  Y: {rawMin.y:F1} ~ {rawMax.y:F1}  (Range: {rawMax.y - rawMin.y:F1})\n";
            info += $"  Z: {rawMin.z:F1} ~ {rawMax.z:F1}  (Range: {rawMax.z - rawMin.z:F1})\n\n";

            info += "<color=lime>Unity coordinate range:</color>\n";
            info += $"  X: {unityMin.x:F3} ~ {unityMax.x:F3}  (Range: {unityMax.x - unityMin.x:F3})\n";
            info += $"  Y: {unityMin.y:F3} ~ {unityMax.y:F3}  (Range: {unityMax.y - unityMin.y:F3})\n";
            info += $"  Z: {unityMin.z:F3} ~ {unityMax.z:F3}  (Range: {unityMax.z - unityMin.z:F3})\n\n";
        }

        info += "<color=yellow>💡 Tips:</color>\n";
        info += "• Move in each direction to inspect ranges\n";
        info += "• Comparable Unity ranges produce balanced display\n";
        info += "• Tune TrajectoryDrawer scaleX/Y/Z\n";
        info += "• Press R to reset statistics";

        textDisplay.text = info;

        if (Input.GetKeyDown(KeyCode.R))
        {
            ResetStatistics();
            Debug.Log("Statistics reset");
        }
    }

    /// <summary>Update coordinate values and observed ranges.</summary>
    public void UpdateCoordinates(float rawX, float rawY, float rawZ, Vector3 unityPos)
    {
        lastRawPos = new Vector3(rawX, rawY, rawZ);
        lastUnityPos = unityPos;

        rawMin = Vector3.Min(rawMin, lastRawPos);
        rawMax = Vector3.Max(rawMax, lastRawPos);
        unityMin = Vector3.Min(unityMin, lastUnityPos);
        unityMax = Vector3.Max(unityMax, lastUnityPos);
    }

    /// <summary>Clear the observed ranges.</summary>
    public void ResetStatistics()
    {
        rawMin = Vector3.positiveInfinity;
        rawMax = Vector3.negativeInfinity;
        unityMin = Vector3.positiveInfinity;
        unityMax = Vector3.negativeInfinity;
    }
}
