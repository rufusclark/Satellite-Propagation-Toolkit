"""utility functions for quickly charting data"""

import numpy as np

from skyfield.api import Time

from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from .propagation import OrbitalPosition
from .projection import EARTH_RADIUS


def plot_interpolation_analysis(*datasets: tuple[Sequence[Time], list[float], list[float], str]) -> None:
    """plot interpolated vs actual datasets and associated quantifed statistically to access the viability of these methods

    datasets: [Time, actual, interpolated, label]
    """
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    n = len(datasets)

    # setup plot
    fig = plt.figure(figsize=(10, 8))  # type: ignore
    fig.canvas.manager.set_window_title(  # type: ignore
        'Interpolation Analysis')
    fig.suptitle("Interpolation Analysis", fontweight='bold')
    gs = gridspec.GridSpec(n, 3, width_ratios=[4, 4, 1])
    axs: list["Axes"] = [None for _ in range(n*3)]  # type: ignore

    # setup text output
    col_width = 20
    fmt_str = str(col_width)
    fmt_float = f"{col_width-5}.4f"
    fmt_str_plot = "20"
    fmt_float_plot = "10.2f"
    print(f"{'':{fmt_str}} {'max error':{fmt_str}} {'mean absolute error':{fmt_str}} {'root mean squared error':{fmt_str}} {'mean bias error':{fmt_str}}")

    for i, dataset in enumerate(datasets):
        # pre-process data
        raw_t, y_actual, y_interpolated, label = dataset
        t_0 = raw_t[0].utc_datetime().timestamp()  # type:ignore
        t = [item.utc_datetime().timestamp() - t_0 for item in raw_t]  # type:ignore
        t, y_actual, y_interpolated = np.array(
            t), np.array(y_actual), np.array(y_interpolated)

        # process data
        errors = y_interpolated - y_actual
        abs_errors = np.abs(errors)
        squared_errors = errors**2

        max_error = np.max(abs_errors)
        mean_absolute_error = np.mean(abs_errors)
        root_mean_squared_error = np.sqrt(np.mean(squared_errors))
        mean_bias_error = np.mean(errors)

        # print and generate text output
        print(f"{label:25} {max_error:{fmt_float}} {mean_absolute_error:{fmt_float}} {root_mean_squared_error:{fmt_float}} {mean_bias_error:{fmt_float}}")
        plot_text = f"{'max error':{fmt_str_plot}}\n{max_error:{fmt_float_plot}}\n{'mean absolute error':{fmt_str_plot}}\n{mean_absolute_error:{fmt_float_plot}}\n{'root mean squared error':{fmt_str_plot}}\n{root_mean_squared_error:{fmt_float_plot}}\n{'mean bias error':{fmt_str_plot}}\n{mean_bias_error:{fmt_float_plot}}"

        # plot data

        # left plot
        axs[i] = fig.add_subplot(gs[i, 0])
        axs[i].plot(t, y_actual, label="actual")
        axs[i].plot(t, y_interpolated, label="recorded")
        axs[i].set_xlabel("time [s]")
        axs[i].set_ylabel(label)
        axs[i].legend()
        axs[i].grid(True)

        # right plot
        axs[i+1] = fig.add_subplot(gs[i, 1])
        axs[i+1].plot(t, errors)
        axs[i+1].set_xlabel("time [s]")
        axs[i+1].set_ylabel("error")
        axs[i+1].grid(True)

        # text overview
        axs[i+2] = fig.add_subplot(gs[i, 2])
        axs[i+2].axis("off")
        axs[i+2].text(
            0.1, 0.5, plot_text,
            transform=axs[i+2].transAxes,
            ha='left', va='center'
        )

    # show plot
    plt.tight_layout()
    plt.show()


def _center_grid_labels(fig, axes, xlabel, ylabel):
    if xlabel:
        fig.supxlabel(" ")
    if ylabel:
        fig.supylabel(" ")

    # Draw the figure once so layout managers compute positions
    fig.canvas.draw()

    # flatten list of lists
    axes_flat = [item for sublist in axes for item in sublist]

    # Get the bounding box of the entire grid of axes
    bboxes = [ax.get_position() for ax in axes_flat]
    left = min([b.x0 for b in bboxes])
    right = max([b.x1 for b in bboxes])
    bottom = min([b.y0 for b in bboxes])
    top = max([b.y1 for b in bboxes])

    # Compute the center positions
    xcenter = (left + right) / 2
    ycenter = (bottom + top) / 2

    # Add grid-level labels
    if xlabel:
        fig.text(xcenter, 0.01, xlabel, ha='center', va='bottom')
    if ylabel:
        fig.text(0.01, ycenter, ylabel, ha='left',
                 va='center', rotation='vertical')


def plot_orbital_overview(
        orbital_positions: list[OrbitalPosition],
        *,
        _plot: bool = True,
        _filename: str = ""
) -> None:
    """generates an orbital overview of all provided orbital_positions using matplotlib

    Args:
        _plot: whether to plot (popout). Defaults to True.
        _filename: filename to save (if provided it will be saved). Defaults to "".
    """
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib.ticker import MaxNLocator
    import textwrap

    fig = plt.figure(figsize=(10, 8), constrained_layout=True)
    fig.canvas.manager.set_window_title('Orbital Overview')  # type: ignore
    fig.suptitle(
        f"Orbital Overview ({len(orbital_positions)} Satellites)", fontweight='bold'
    )

    outer = gridspec.GridSpec(2, 1, height_ratios=[2, 1], figure=fig)

    # top: 3x2 grid of histograms
    top = gridspec.GridSpecFromSubplotSpec(2, 3, subplot_spec=outer[0])
    top_axes: list[list["Axes"]] = [[None]*3 for _ in range(2)]  # type: ignore
    def idx(i): return i//3, i % 3  # returns the grid position # type: ignore
    def sub_cap(i): return chr(i + ord('a'))  # type: ignore
    for i, data, label, limit in zip(
        [0, 1, 2, 3, 4, 5],
        [[pos.geo.alt for pos in orbital_positions],
         [pos.sat.eccentricity for pos in orbital_positions],
         [np.rad2deg(pos.sat.inclination)
          for pos in orbital_positions],
         [np.rad2deg(pos.sat.right_ascension_of_ascending_node)
          for pos in orbital_positions],
         [np.rad2deg(pos.sat.argument_of_perigee)
          for pos in orbital_positions],
         [pos.sat.launch_age.days / 365.25 for pos in orbital_positions]],
        ["altitude [km]", "eccentricity", "inclination [°]",
            "RAAN [°]", "argument of perigee [°]", "age [years]"],
        [(0, 42000), (0, 1), (0, 180), (0, 360), (0, 360), (0, None)]
    ):
        row, col = idx(i)
        if row == 0:
            axis = fig.add_subplot(top[row, col])
        else:
            axis = fig.add_subplot(
                top[row, col], sharey=top_axes[0][col])

        axis.hist(data, bins=200, log=True)
        axis.set_xlabel(f"({sub_cap(i)}) {label}")
        axis.grid(which="both", linestyle="-", linewidth=0.3, alpha=0.7)
        axis.set_xlim(*limit)
        axis.xaxis.set_major_locator(MaxNLocator(nbins=6, prune=None))

        if col > 0:
            plt.setp(axis.get_yticklabels(), visible=False)
        top_axes[row][col] = axis

    # make all y-axis the same
    axes_list = [ax for row in top_axes for ax in row if ax is not None]
    max_height = max(max(patch.get_height()  # type: ignore
                     for patch in ax.patches) for ax in axes_list)
    for ax in axes_list:
        ax.set_ylim(1, max_height*1.2)  # 1 instead of 0 because log scale

    _center_grid_labels(fig, top_axes, "", "frequency")

    # bottom: 3x1 grid of pie charts
    bottom = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[1])
    bottom_axes: list[list["Axes"]] = [[None]*3]  # type: ignore
    def idx(i): return i//3, i & 3
    def sub_cap(i): return chr(i + ord('g'))
    for i, data, label in zip(
        [0, 1, 2],
        [
            [pos.sat.category for pos in orbital_positions],
            [pos.sat.owner for pos in orbital_positions],
            [pos.sat.launch_country for pos in orbital_positions]
        ],
        ["category", "owner", "launch location"]
    ):
        row, col = idx(i)
        axis = fig.add_subplot(bottom[row, col])

        # data processing
        processed_data: dict[str, int] = {}
        for data_point in data:
            if not data_point:
                data_point = "Unknown"
            processed_data[data_point] = processed_data.get(data_point, 0) + 1

        total = sum(processed_data.values())
        threshold_deg = 8
        threshold_fraction = threshold_deg / 360
        threshold_number = threshold_fraction * total

        for key, val in list(processed_data.items()):
            if val < threshold_number:
                processed_data["Other"] = processed_data.get("Other", 0) + val
                del processed_data[key]

        # sort
        processed_data = dict(
            sorted(processed_data.items(), key=lambda item: item[1], reverse=True))

        # move "Other" to the end
        if "Other" in processed_data:
            processed_data["Other"] = processed_data.pop("Other")

        values = list(processed_data.values())
        labels = list(processed_data.keys())

        # wrap long labels
        labels = ["\n".join(textwrap.wrap(
            label.strip(), width=18, break_long_words=False, replace_whitespace=False)) for label in labels]

        # end of data processing

        # plot
        axis.set_xlabel(f"({sub_cap(i)}) {label}")
        axis.pie(
            values,
            labels=labels,
            textprops={'fontsize': 6},
            autopct=lambda pct: str(int(round(pct*sum(values)/100))),
            pctdistance=0.85,
        )

        # _piechart_2(axis, f"({sub_cap(i)}) {label}", counts)

        bottom_axes[row][col] = axis

    if _filename:
        plt.savefig(_filename)
    if _plot:
        plt.show()


def plot_on_Earth(orbital_positions: list[OrbitalPosition]) -> None:
    import matplotlib.pyplot as plt

    x = np.array([position.geo.x for position in orbital_positions])
    y = np.array([position.geo.y for position in orbital_positions])
    z = np.array([position.geo.z for position in orbital_positions])

    # setup graph
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})

    # plot satellite data
    ax.scatter(x, y, z, s=3)

    # Create sphere for Earth
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    earth_x = EARTH_RADIUS * np.outer(np.cos(u), np.sin(v))
    earth_y = EARTH_RADIUS * np.outer(np.sin(u), np.sin(v))
    earth_z = EARTH_RADIUS * np.outer(np.ones(np.size(u)), np.cos(v))

    # plot "Earth"
    ax.plot_surface(earth_x, earth_y, earth_z,
                    color='green', alpha=0.3)  # 30% opaque

    # Set labels
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    # Set equal aspect ratio
    ax.set_box_aspect([1, 1, 1])

    plt.show()
