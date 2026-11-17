
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class CableVisualisation:
    def __init__(self, state, state_lock, fps=30, view_elev=20, view_azim=120, auto_expand=True, show_origin=True, angle_calc=None):
        self.state = state
        self.state_lock = state_lock
        self.fps = fps
        self.view_elev = view_elev
        self.view_azim = view_azim
        self.auto_expand  = auto_expand
        self.show_origin = show_origin
        self.animation = None
        self.axes_initialised = None
        self.angle_calc = angle_calc

        # -----------------------------
        if self.angle_calc is not None:
            # Combined 3D fibre and angle history
            self.fig = plt.figure(figsize=(13, 10))
            gs = self.fig.add_gridspec(2, 1,height_ratios=[3, 1.2],hspace=0.35)
            self.ax = self.fig.add_subplot(gs[0], projection="3d")
            self.angle_ax = self.fig.add_subplot(gs[1])

        else:
            # Original standalone 3D interface
            self.fig = plt.figure(figsize=(12, 8))
            self.ax = self.fig.add_subplot(111, projection="3d")
            self.angle_ax = None
            self.fig.subplots_adjust(left=0.02,right=0.98,bottom=0.08,top=0.90)
        self.fig.patch.set_facecolor("#F5F7FA")
        self.ax.set_facecolor("#FFFFFF")
        # Orthographic projection avoids perspective distortion.
        self.ax.set_proj_type("ortho")
        self.ax.view_init(elev=self.view_elev,azim=self.view_azim)

        # Main fibre line
        (self.reference_line,) = self.ax.plot(
            [], [], [],
            color="#888888",
            linestyle="--",
            linewidth=2,
            alpha=0.7,
            label="Reference fibre"
        )
        (self.line,) = self.ax.plot(
            [], [], [],
            color="#1565C0",
            linewidth=3,
            label="Fibre"
        )
        # Fibre start marker
        (self.start_marker,) = self.ax.plot(
            [], [], [],
            marker="o",
            linestyle="None",
            color="#2E7D32",
            markersize=7,
            label="Fibre start"
        )
        # Fibre end marker
        (self.end_marker,) = self.ax.plot(
            [], [], [],
            marker="o",
            linestyle="None",
            color="#D32F2F",
            markersize=7,
            label="Fibre end"
        )
        # Reference origin
        (self.origin_marker,) = self.ax.plot(
            [0], [0], [0],
            marker="+",
            linestyle="None",
            color="black",
            markersize=12,
            markeredgewidth=2,
            label="Origin (0, 0, 0)"
        )
        # Reference axes through the origin
        self.x_reference, = self.ax.plot(
            [], [], [],
            color="red",
            linewidth=1,
            alpha=0.4
        )
        self.y_reference, = self.ax.plot(
            [], [], [],
            color="green",
            linewidth=1,
            alpha=0.4
        )
        self.z_reference, = self.ax.plot(
            [], [], [],
            color="purple",
            linewidth=1,
            alpha=0.4
        )

        self.ax.set_xlabel("X (mm)", labelpad=12)
        self.ax.set_ylabel("Y (mm)", labelpad=12)
        self.ax.set_zlabel("Z (mm)", labelpad=12)

        self.ax.grid(True)
        self.title = self.ax.set_title("Waiting for Shape CORE...",fontsize=12,pad=20)
        self.ax.legend(loc="upper left",fontsize=9)
        # -----------------------------------
        # Combined angle visualisation
        # -----------------------------------
        if self.angle_ax is not None:
            (self.angle_line,) = self.angle_ax.plot(
                [], [],
                color="#1565C0",
                linewidth=2,
                label="3D tip angle from reference"
            )
            (self.signed_line,) = self.angle_ax.plot(
                [], [],
                color="#E67E22",
                linewidth=2,
                label="Signed planar tip angle"
            )
            self.angle_ax.axhline(0,color="gray",linewidth=1,alpha=0.5)
            self.angle_ax.set_title("Live fibre-tip orientation")
            self.angle_ax.set_xlabel("Time since reference (s)")
            self.angle_ax.set_ylabel("Angle (degrees)")
            self.angle_ax.set_xlim(0, 60)
            self.angle_ax.set_ylim(-5, 5)
            self.angle_ax.grid(True, alpha=0.3)
            self.angle_ax.legend(loc="upper right")

            # Numerical readout above the angle graph
            self.angle_text = self.angle_ax.text(
                0.02, 0.96,
                "Waiting for angle data...",
                transform=self.angle_ax.transAxes,
                va="top",
                fontsize=10,
                fontweight="bold",
                bbox=dict(
                    facecolor="white",
                    edgecolor="#dddddd",
                    alpha=0.85
                )
            )
        # Initial view, centred on the origin.
        self._set_limits(np.array([-10.0, -10.0, -10.0]),np.array([10.0, 10.0, 10.0]))
        self.fig.canvas.mpl_connect("key_press_event",self._on_key)

    def _set_limits(self, lower: np.ndarray, upper: np.ndarray) -> None:
        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)

        self.ax.set_xlim(lower[0], upper[0])
        self.ax.set_ylim(lower[1], upper[1])
        self.ax.set_zlim(lower[2], upper[2])

        # Preserve geometric proportions in 3D.
        spans = upper - lower

        self.ax.set_box_aspect(
            spans,
            zoom=0.85
        )

        self.lower = lower.copy()
        self.upper = upper.copy()
        self._update_reference_axes()

    def _update_reference_axes(self) -> None:
        if not self.show_origin: return

        xmin, ymin, zmin = self.lower
        xmax, ymax, zmax = self.upper

        self.x_reference.set_data([xmin, xmax],[0, 0])
        self.x_reference.set_3d_properties([0, 0])
        self.y_reference.set_data([0, 0],[ymin, ymax])
        self.y_reference.set_3d_properties([0, 0])
        self.z_reference.set_data([0, 0],[0, 0])
        self.z_reference.set_3d_properties([zmin, zmax])

    def _calculate_bounds(self, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate bounds that contain:
          - all fibre points
          - the global origin
          - some padding
        """
        minimum = np.minimum(np.min(pts, axis=0), 0.0)
        maximum = np.maximum(np.max(pts, axis=0),0.0)
        spans = maximum - minimum
        padding = np.maximum(spans * 0.08,1.0)
        return minimum - padding, maximum + padding

    def _update_axes(self, pts: np.ndarray) -> None:
        new_lower, new_upper = self._calculate_bounds(pts)
        if not self.axes_initialised:
            self._set_limits(new_lower, new_upper)
            self.axes_initialised = True
            return

        if not self.auto_expand:return
        # Expand only if the fibre is outside existing limits.
        # Do not shrink continuously, which causes jitter.
        if (np.any(new_lower < self.lower) or np.any(new_upper > self.upper)):
            lower = np.minimum(self.lower,new_lower)
            upper = np.maximum(self.upper,new_upper)

            self._set_limits(lower, upper)

    # -----------------------------------
    # Animation callbacks
    # -----------------------------------
    def _init_plot(self) -> tuple:
        self.line.set_data([], [])
        self.line.set_3d_properties([])
        self.start_marker.set_data([], [])
        self.start_marker.set_3d_properties([])
        self.end_marker.set_data([], [])
        self.end_marker.set_3d_properties([])

        return (self.line,self.start_marker, self.end_marker,self.title)

    def _update(self, frame: int) -> tuple:
        # Read all state values under the same lock.
        with self.state_lock:
            pts = self.state["pts"]
            fiber = self.state["fiber"]
            ts = self.state["ts"]
            err = self.state["err"]
            connected = self.state["connected"]
            frames = self.state["frames"]
            bad_packets = self.state["bad_packets"]

        if pts.shape[0] > 0:
            x = pts[:, 0]
            y = pts[:, 1]
            z = pts[:, 2]

            # Update fibre geometry
            self.line.set_data(x, y)
            self.line.set_3d_properties(z)
            # First point
            self.start_marker.set_data([x[0]], [y[0]])
            self.start_marker.set_3d_properties([z[0]])
            # Last point
            self.end_marker.set_data([x[-1]], [y[-1]])
            self.end_marker.set_3d_properties([z[-1]])

            # Expand axes when needed
            self._update_axes(pts)
        # -----------------------------------
        # Update angle plot and reference shape
        # -----------------------------------
        if self.angle_calc is not None:
            snapshot = self.angle_calc.get_visual_snapshot()
            reference_pts = snapshot["reference_points"]
            # Draw the original fibre geometry
            if reference_pts is not None:
                self.reference_line.set_data(reference_pts[:, 0],reference_pts[:, 1])
                self.reference_line.set_3d_properties(reference_pts[:, 2])
            # Update angle-versus-time curves
            times = snapshot["times"]
            angles = snapshot["angles"]
            signed_angles = snapshot["signed_angles"]

            if times:
                self.angle_line.set_data(times, angles)
                self.signed_line.set_data(times, signed_angles)
                window = snapshot["history_seconds"]
                right = max(window, times[-1] + 1.0)
                left = max(0.0, right - window)

                self.angle_ax.set_xlim(left, right)
                valid_values = [
                    v for v in angles + signed_angles
                    if np.isfinite(v)
                ]
                if valid_values:
                    lower = min(-5.0, min(valid_values) * 1.15)
                    upper = max(5.0, max(valid_values) * 1.15)
                    self.angle_ax.set_ylim(lower, upper)

            # Live numerical readout
            tip = snapshot["latest_angle"]
            signed = snapshot["signed_angle"]
            speed = snapshot["angular_velocity"]

            def display_number(value):
                return f"{value:.2f}" if np.isfinite(value) else "--"

            self.angle_text.set_text(
                f"Tip: {display_number(tip)}°    "
                f"Signed: {display_number(signed)}°    "
                f"Speed: {display_number(speed)}°/s"
            )
        
        status = (
            "CONNECTED"
            if connected
            else "DISCONNECTED"
        )

        self.title.set_text(
            f"{status} | Fibre={fiber} | "
            f"t={ts:.3f}s | err={err}\n"
            f"Points={pts.shape[0]} | "
            f"Saved={frames} | "
            f"Bad packets={bad_packets}"
        )

        return (self.line,self.start_marker,self.end_marker,self.title)

    # -----------------------------------
    # Interactive controls HOW TO NAVIAGTE THE GRAPHIGN
    # -----------------------------------
    def _on_key(self, event) -> None:
        key = (event.key or "").lower()
        if key == "r":
            if self.angle_calc is not None:
                if self.angle_calc.reset_reference():
                    print("[ANGLE] Reference reset")
            else:
                self.reset_camera()
        elif key == "c":
            self.reset_camera()
        elif event.key == "f":
            self.fit_to_fiber()
        elif event.key == "a":
            self.auto_expand = not self.auto_expand
            print("axis automatically expands:",self.auto_expand)

        elif event.key == "g":
            self.ax.grid(not self.ax._axis3don) if False else None
            self._grid_visible = not getattr(self, "_grid_visible", True)
            self.ax.grid(self._grid_visible)
            self.fig.canvas.draw_idle()

    def reset_camera(self) -> None:
        self.ax.view_init(elev=self.view_elev,azim=self.view_azim)
        self.fig.canvas.draw_idle()

    def fit_to_fiber(self) -> None:
        with self.state_lock: pts = self.state["pts"]
        if pts.shape[0] == 0: return
        lower, upper = self._calculate_bounds(pts)
        self._set_limits(lower, upper)
        self.axes_initialised = True
        self.fig.canvas.draw_idle()

    # -----------------------------------
    # Public methods called from main
    # -----------------------------------
    def start(self) -> "CableVisualisation":
        self.animation = FuncAnimation(
            self.fig,self._update,init_func=self._init_plot,
            interval=1000 / self.fps,blit=False,cache_frame_data=False
        )
        return self

    def show(self) -> None:
        plt.show()