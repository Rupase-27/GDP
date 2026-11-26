# realtime_shape_view_and_log.py
# Real-time Shape CORE stream -> live 3D plot + CSV logging (one frame per row)

import socket, struct, time, os, csv, json, threading
import numpy as np
import matplotlib
# Threading allows data aq to run independent of the GUI
matplotlib.use("QtAgg")
# from FBGCurvatureCalc import FBGBendingAngle
from RealTimeVisualiserPlotterScript import CableVisualisation
from BendingAngleCalc import BendingAngle
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

_anim_ref = None

# ----------------------------
# Config
# ----------------------------
CMD_HOST = "127.0.0.1"
CMD_PORT = 50011

STREAM_HOST = "127.0.0.1"
STREAM_PORT = 50012  # will set via command
ENABLE_ERROR = True

FPS = 30 # GUI update rate
VIEW_ELEV = 20
VIEW_AZIM = 120
AUTO_EXPAND_AXES = True
SHOW_ORIGIN = True

OUT_CSV = "shape_realtime_frames.csv"
FLUSH_EVERY_FRAMES = 10  # force flush to disk every N frames # how many stream messages to consume per GUI tick (lower latency)


# CSV format:
# one frame per row:
# pc_time, fiber, core_error, device_timestamp, n_points, x_mm_json, y_mm_json, z_mm_json
# (JSON arrays; easy to load back, no gigantic "one point per row" files)

# ----------------------------
# Socket helpers
# ----------------------------
def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed.")
        buf.extend(chunk)
    return bytes(buf)

def pack_cmd(cmd_id: int, args: bytes = b"") -> bytes:
    length = 2 + len(args)
    return struct.pack("<iH", length, cmd_id) + args

def cmd_u16(v: int) -> bytes:
    return struct.pack("<H", v & 0xFFFF)

def cmd_bool(flag: bool) -> bytes:
    return struct.pack("<B", 1 if flag else 0)

def read_cmd_reply(sock: socket.socket):
    header = recv_exact(sock, 4)
    (length,) = struct.unpack("<i", header)
    #Validate the report length first to ensure it is approriate 
    if length < 2 or length > 1024 * 1024:
        raise ValueError(f"Invalid Commmand Reply length: {length}")
    payload = recv_exact(sock,length)
    status = struct.unpack_from("<H", payload, 0)[0]
    return status, payload[2:]

def send_cmd(sock: socket.socket, cmd_id: int, args: bytes = b""):
    sock.sendall(pack_cmd(cmd_id, args))
    status, _ = read_cmd_reply(sock)
    if status != 0:
        raise RuntimeError(f"Command {cmd_id} failed (status={status}).")



def configure_stream():
    # 1028 Set Stream out Port (U16)
    # 2048 Set Stream Error? (bool)
    # 2050 Set Stream Timestamp? (bool)
    # 2053 Set Stream Shape? (bool)
    with socket.create_connection((CMD_HOST, CMD_PORT), timeout=5) as s:
        send_cmd(s, 1028, cmd_u16(STREAM_PORT))
        if ENABLE_ERROR:
            send_cmd(s, 2048, cmd_bool(True))
        send_cmd(s, 2050, cmd_bool(True))
        send_cmd(s, 2053, cmd_bool(True))

# ----------------------------
# Stream parsing // Improve parsing, when mbad data was encountered it would stop
# Now raise an error instead of allowing rejections of bad packets
# ----------------------------
# def parse_stream_message(payload: bytes):
#     if len(payload) <1 : 
#         raise ValueError("Empty stream payload")
#     off = 0
#     fiber = struct.unpack_from("<B", payload, off)[0]
#     off += 1
#     fields = {}
#     while off < len(payload):
#         if off + 4 > len(payload): 
#             raise ValueError("Incomplete field length")
#         field_len = struct.unpack_from("<i", payload, off)[0]
#         off += 4
#         if field_len < 2: 
#             raise ValueError(f"Invalid length:{field_len}")
#         if off + field_len > len(payload):
#             raise ValueError("Incomplete field payload")
#         field_id = struct.unpack_from("<H", payload, off)[0]
#         fields[field_id] = payload[off + 2:off + field_len]
#         off += field_len
#     return fiber, fields

def parse_stream_message(payload: bytes):
    off = 0
    fiber = struct.unpack_from("<B", payload, off)[0]
    off += 1
    fields = {}

    while off < len(payload):
        field_len = struct.unpack_from("<i", payload, off)[0]
        off += 4
        field_id = struct.unpack_from("<H", payload, off)[0]

        if field_len < 2 or off + field_len > len(payload):
            raise ValueError("Invalid field boundary")
        fields[field_id] = payload[off + 2:off + field_len]
        off += field_len

    return fiber, fields

def parse_timestamp(b: bytes):
    return struct.unpack_from("<d", b, 0)[0] if b and len(b) >= 8 else np.nan

def parse_error(b: bytes):
    return struct.unpack_from("<H", b, 0)[0] if b and len(b) >= 2 else -1
# Prevent malformed measurements from being plotted or exported
# def parse_shape(b: bytes):
#     if not b or len(b) < 4:
#         return np.empty((0,3), dtype=np.float32)
#     n = struct.unpack_from("<i", b, 0)[0]
#     data = b[4:]
#     if n <= 0 or n % 3 != 0:
#         raise ValueError(f"invalid float count : {n}")
#     expected_bytes = 4 + 4 * n
#     if len(b) != expected_bytes:
#         raise ValueError("Expected lenght does not match")
#     vals = np.frombuffer( b, dtype="<f4", count=n, offset=4 )
#     if not np.all(np.isfinite(vals)):
#         raise ValueError("Shape contains either None of INf")
#     return vals.reshape(-1,3).copy()

def parse_shape(b: bytes):

    if not b or len(b) < 8:
        return np.empty((0, 3), dtype=np.float32)

    rows, cols = struct.unpack_from("<ii", b, 0)

    if rows <= 0 or cols != 3:
        raise ValueError(
            f"Invalid shape dimensions: {rows} x {cols}"
        )

    expected_bytes = 8 + rows * cols * 4

    if len(b) != expected_bytes:
        raise ValueError(
            f"Shape length mismatch: "
            f"expected={expected_bytes}, actual={len(b)}"
        )

    vals = np.frombuffer(
        b,
        dtype="<f4",
        count=rows * cols,
        offset=8
    )

    if not np.all(np.isfinite(vals)):
        raise ValueError("Shape contains NaN or Inf")

    return vals.reshape(rows, cols).copy()
# ----------------------------
# CSV logging (one frame per row)
# ----------------------------
def open_csv(path: str):
    new_file = not os.path.exists(path)
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new_file:
        #Angles are in Degrees
        w.writerow(["pc_time", "fiber", "core_error", "device_timestamp",
                    "n_points", "x_mm_json", "y_mm_json", "z_mm_json", "relative_tip_angle",
                    "signed_tip_angle", "delta_tip_angle", "tip_angular_vel_deg_s"])
        f.flush()
    return f, w



def main(embedded=False): # If run from UI app, main(True) will return the visualiser


    stop_event = threading.Event()
    state_lock = threading.Lock()
    socket_lock = threading.Lock()

    active_socket = [None]

    state = {
        "pts": np.empty((0, 3), dtype=np.float32),
        "fiber": 0, "ts": np.nan, "err": 0, "axes_fixed": False,
        "connected": False, "frames": 0, "bad_packets": 0,
    }
    angle_calc = BendingAngle(
        tip_points=10,
        history_seconds=60
    )

    visualizer = CableVisualisation(
        state=state,
        state_lock=state_lock,
        fps=FPS,
        view_elev=VIEW_ELEV,
        view_azim=VIEW_AZIM,
        auto_expand=AUTO_EXPAND_AXES,
        show_origin=SHOW_ORIGIN,
        angle_calc=angle_calc
    )

    f_csv, w_csv = open_csv(OUT_CSV)
# ---------------------------------
# Background data acquisition
# Process Steps
# Reads complete TCP headers and payloads.
# Parses sensor packets before updating the plot.
# Writes each valid received shape frame to CSV.
# Reconnects after connection failures.
# Keeps the Matplotlib window responsive during network interruptions.
# Flushes recorded measurements on disconnection and shutdow
# ---------------------------------
    def receiver():
        frames_since_flush = 0
        while not stop_event.is_set():
            sock = None
            try:
                # Configure command and stream ports.
                configure_stream()

                sock = socket.create_connection(
                    (STREAM_HOST, STREAM_PORT), timeout=3 )

                # Blocking reads preserve packet framing.
                # Closing the socket stops the receiver.
                sock.settimeout(None)
                with socket_lock:
                    active_socket[0] = sock

                with state_lock:
                    state["connected"] = True

                print("[CONNECTED] Shape CORE stream")

                while not stop_event.is_set():
                    # Read the COMPLETE TCP header.
                    header = recv_exact(sock, 4)

                    (msg_len,) = struct.unpack( "<i", header )

                    # Protect against corrupt packet sizes.
                    if not (1 <= msg_len <= 8 * 1024 * 1024):
                        raise ValueError( f"Invalid packet length: {msg_len}")

                    payload = recv_exact(sock, msg_len)
                    try:
                        fiber, fields = parse_stream_message( payload )

                        ts = parse_timestamp( fields.get(2, b"") )

                        err = (
                            parse_error(fields.get(0, b""))if ENABLE_ERROR else 0
                        )

                        pts = parse_shape( fields.get(5, b"")
                        )

                        # Ignore packets without a valid shape.
                        if pts.shape[0] == 0:
                            raise ValueError( "No shape points in packet")

                    except (ValueError, struct.error) as e:
                        with state_lock:
                            state["bad_packets"] += 1

                        print("[BAD PACKET]", e)
                        continue
                    # Record each valid received frame.
                    pc_time = time.time()
                    # Calculate bending angle
                    try: 
                        angle = angle_calc.record_frame(pts,timestamp=pc_time)
                        metrics = angle_calc.get_latest_metrics()
                        signed_angle = metrics["signed_angle"]
                        delta_angle = metrics["delta_angle"]
                        angular_velocity = metrics["angular_velocity"]
                    except ValueError as e:
                        angle = float("nan")
                        signed_angle = float("nan")
                        delta_angle = float("nan")
                        angular_velocity = float("nan")
                        print("[ANGLE ERROR]", e)
                    n = int(pts.shape[0])

                    xj = json.dumps(
                        pts[:, 0].astype(float).tolist(), separators=(",", ":")
                    )
                    yj = json.dumps(
                        pts[:, 1].astype(float).tolist(), separators=(",", ":")
                    )
                    zj = json.dumps(
                        pts[:, 2].astype(float).tolist(), separators=(",", ":")
                    )

                    w_csv.writerow([
                        pc_time, fiber, err, ts, n, xj, yj, zj, 
                        f"{angle:.3f}" if np.isfinite(angle) else "",
                        f"{signed_angle:.3f}" if np.isfinite(signed_angle) else "",
                        f"{delta_angle:.3f}" if np.isfinite(delta_angle) else "",
                        f"{angular_velocity:.3f}" if np.isfinite(angular_velocity) else ""
                    ])

                    frames_since_flush += 1

                    if frames_since_flush >= FLUSH_EVERY_FRAMES:
                        f_csv.flush()
                        frames_since_flush = 0

                    # Only the latest frame is needed by GUI.
                    with state_lock:
                        state["pts"] = pts
                        state["fiber"] = fiber
                        state["ts"] = ts
                        state["err"] = err
                        state["frames"] += 1

            except (OSError, ConnectionError,
                    #Prevents these type of errors from killing the threads
                    #Instead uses the logic to attempt retries for connections
                    ValueError, struct.error, RuntimeError) as e:
                if not stop_event.is_set():
                    print("[DISCONNECTED]", e)

            finally:
                with state_lock:
                    state["connected"] = False

                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                with socket_lock:
                    if active_socket[0] is sock:
                        active_socket[0] = None

                # Preserve recorded frames on disconnect.
                f_csv.flush()

            # Retry without blocking the plotting window.
            if not stop_event.is_set():
                print("[RETRY] Connecting again...")
                stop_event.wait(1.0)

    # ---------------------------------
    # Matplotlib interface
    # ---------------------------------
    # Call visualisation script

    # ---------------------------------
    # Start acquisition and animation
    # ---------------------------------
    worker = threading.Thread(
        target=receiver,
        daemon=True
    )
    
    def shutdown(): 
        # Was in finally, but moved to a function that might be needed elsewhere
        
        stop_event.set()
        # Interrupt a blocking socket read.
        with socket_lock:
            sock = active_socket[0]
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        worker.join(timeout=8)

        if worker.is_alive():
            print(
                "_ WARNING || Receiver did not stop cleanly" )
        else:
            f_csv.flush()
            f_csv.close()

        with state_lock:
            print(
                "_ STOPPED || Saved frames:", state["frames"],
                "| Bad packets:", state["bad_packets"] )
        angle_calc.close() 
    
    worker.start()
    # Start the Matplotlib animation
    visualizer.start()
    # Create the separate live bending-angle plot

    if embedded:
        return visualizer, shutdown # For access if used by another program

    try:
        # Display the interactive 3D plot
        visualizer.show()

    finally:
        shutdown()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())