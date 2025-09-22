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

    # setup plot
    fig = plt.figure(figsize=(10, 8))  # type: ignore
    fig.canvas.manager.set_window_title(  # type: ignore
        'Orbital Overview')
    fig.suptitle(
        f"Orbital Overview ({len(orbital_positions)} Satellites)", fontweight='bold')
    gs = gridspec.GridSpec(3, 3, width_ratios=[1, 1, 1])
    axs: list["Axes"] = []

    axs.append(altitude_histogram(
        fig.add_subplot(gs[0, 0]), orbital_positions)
    )

    axs.append(eccentricity_histogram(
        fig.add_subplot(gs[1, 0]), orbital_positions)
    )

    axs.append(inclination_histogram(
        fig.add_subplot(gs[2, 0]), orbital_positions)
    )

    axs.append(right_ascension_of_ascending_node_histogram(
        fig.add_subplot(gs[0, 1]), orbital_positions)
    )

    axs.append(argument_of_perigee_histogram(
        fig.add_subplot(gs[1, 1]), orbital_positions)
    )

    axs.append(launch_age_histogram(
        fig.add_subplot(gs[2, 1]), orbital_positions)
    )

    axs.append(category_piechart(
        fig.add_subplot(gs[0, 2]), orbital_positions)
    )

    axs.append(owner_piechart(
        fig.add_subplot(gs[1, 2]), orbital_positions)
    )

    axs.append(launch_country_piechart(
        fig.add_subplot(gs[2, 2]), orbital_positions)
    )

    plt.tight_layout()
    if _filename:
        plt.savefig(_filename)
    if _plot:
        plt.show()


def altitude_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="altitude [km]",
        data=[position.geo.alt for position in orbital_positions]
    )


def eccentricity_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="eccentricity",
        data=[position.sat.eccentricity for position in orbital_positions]
    )


def inclination_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="inclination [deg]",
        data=[np.rad2deg(position.sat.inclination)
              for position in orbital_positions]
    )


def right_ascension_of_ascending_node_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="right ascension of ascending node [deg]",
        data=[np.rad2deg(position.sat.right_ascension_of_ascending_node)
              for position in orbital_positions]
    )


def argument_of_perigee_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="argument of perigee [deg]",
        data=[np.rad2deg(position.sat.argument_of_perigee)
              for position in orbital_positions]
    )


def launch_age_histogram(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    return _histogram(
        axes=axes,
        label="launch age [years]",
        data=[position.sat.launch_age.days / 365.25
              for position in orbital_positions]
    )


def category_piechart(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    # compute the number of each category
    counts: dict[str, int] = {}
    for position in orbital_positions:
        cat = position.sat.category
        if cat in counts:
            counts[cat] += 1
        else:
            counts[cat] = 1

    # remove the word satellites from data labels
    for key in list(counts.keys()):
        counts[key.split(" satellites")[0]] = counts.pop(key)

    return _piechart(
        axes=axes,
        label="categories",
        data=counts
    )


def owner_piechart(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    # compute the number of each category
    counts: dict[str, int] = {}
    for position in orbital_positions:
        if position.sat.owner:
            owner = position.sat.owner
        else:
            continue
        if owner in counts:
            counts[owner] += 1
        else:
            counts[owner] = 1

    return _piechart(
        axes=axes,
        label="owner",
        data=counts
    )


def launch_site_piechart(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    # compute the number of each category
    counts: dict[str, int] = {}
    for position in orbital_positions:
        if position.sat.launch_site:
            launch_site = position.sat.launch_site
        else:
            continue
        if launch_site in counts:
            counts[launch_site] += 1
        else:
            counts[launch_site] = 1

    return _piechart(
        axes=axes,
        label="launch site",
        data=counts
    )


def launch_country_piechart(axes: "Axes", orbital_positions: list[OrbitalPosition]) -> "Axes":
    # compute the number of each category
    counts: dict[str, int] = {}
    for position in orbital_positions:
        if position.sat.launch_country:
            launch_country = position.sat.launch_country
        else:
            continue
        if launch_country in counts:
            counts[launch_country] += 1
        else:
            counts[launch_country] = 1

    return _piechart(
        axes=axes,
        label="launch country",
        data=counts
    )


def _histogram(axes: "Axes", label: str, data: list[float]) -> "Axes":
    axes.hist(data, bins=100, log=True)
    axes.set_xlabel(label)
    axes.set_ylabel("frequency")
    axes.set_title(f"{label.split(' [')[0]} histogram")
    axes.grid(False)
    return axes


def _piechart(axes: "Axes", label: str, data: dict[str, int]) -> "Axes":
    # sort dicts and combine smaller terms
    n = 9
    sorted_items = sorted(
        data.items(), key=lambda item: item[1], reverse=True)
    if len(sorted_items) > n:
        sorted_items[n] = ("Other", sum([item[1]
                           for item in sorted_items[n:]]))
        sorted_items = sorted_items[:n+1]
        data = dict(sorted_items)

    # wrap long labels
    for key in list(data.keys()):
        data['\n('.join(',\n'.join(key.split(',', maxsplit=1)).split('(')) if len(
            key) > 20 else key] = data.pop(key)

    # add count to the end of the label
    for key, value in list(data.items()):
        data[f"{key} ({value})"] = data.pop(key)

    # plot
    axes.set_title(f"{label} pie chart")
    wedges, _ = axes.pie(list(data.values()))  # type: ignore
    axes.legend(wedges, list(data.keys()), loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1), fontsize="small")
    return axes


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
