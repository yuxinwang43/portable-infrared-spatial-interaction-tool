using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Generic;

public class UDPReceiver : MonoBehaviour
{
    public int port = 5005;
    public TrajectoryDrawer drawer;

    [Header("Debug settings")]
    [Tooltip("Show received raw coordinates when tuning scale")]
    public bool showDebugCoordinates = false;

    [Tooltip("Frames between debug logs")]
    public int debugPrintInterval = 30;

    [Tooltip("Optional coordinate debug UI")]
    public CoordinateDebugger debugger;

    private int frameCounter = 0;

    private UdpClient client;
    private Thread recvThread;
    private bool running = false;

    private Queue<string> messageQueue = new Queue<string>();
    private object queueLock = new object();

    void Start()
    {
        client = new UdpClient(port);
        running = true;

        recvThread = new Thread(ReceiveLoop);
        recvThread.IsBackground = true;
        recvThread.Start();

        Debug.Log("UDP Receiver Started on port " + port);
    }

    void ReceiveLoop()
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, 0);

        while (running)
        {
            try
            {
                byte[] data = client.Receive(ref ep);
                string json = Encoding.UTF8.GetString(data);

                lock (queueLock)
                {
                    messageQueue.Clear();
                    messageQueue.Enqueue(json);
                }
            }
            catch (SocketException)
            {
                break;
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning("UDP ReceiveLoop error: " + ex.Message);
            }
        }
    }

    void Update()
    {
        string json = null;

        lock (queueLock)
        {
            if (messageQueue.Count > 0)
            {
                json = messageQueue.Dequeue();
            }
        }

        if (string.IsNullOrEmpty(json))
            return;

        try
        {
            Vector3Data pos = JsonUtility.FromJson<Vector3Data>(json);

            if (showDebugCoordinates)
            {
                frameCounter++;
                if (frameCounter >= debugPrintInterval)
                {
                    Debug.Log($"[Raw coordinates] X={pos.x:F1}mm  Y={pos.y:F1}mm  Z={pos.z:F1}mm");
                    frameCounter = 0;
                }
            }

            Vector3 worldPos = drawer.MapToUnity(pos.x, pos.y, pos.z);

            if (showDebugCoordinates && frameCounter == 1)
            {
                Debug.Log($"[Unity coordinates] X={worldPos.x:F3}  Y={worldPos.y:F3}  Z={worldPos.z:F3}");
            }

            if (debugger != null)
            {
                debugger.UpdateCoordinates(pos.x, pos.y, pos.z, worldPos);
            }

            drawer.AddPoint(worldPos);
        }
        catch (System.Exception ex)
        {
            Debug.LogWarning("Parse/Draw error: " + ex.Message);
        }
    }

    void OnApplicationQuit()
    {
        running = false;

        try
        {
            client?.Close();
        }
        catch { }

        try
        {
            if (recvThread != null && recvThread.IsAlive)
            {
                recvThread.Join(200);
            }
        }
        catch { }
    }
}

[System.Serializable]
public class Vector3Data
{
    public float x;
    public float y;
    public float z;
}
