"""contains useful utilities"""
from skyfield.toposlib import GeographicPosition
from skyfield.api import wgs84
from .projectionmodels import BaseProjectionModel


def dirname(model: BaseProjectionModel) -> str:
    """function for consistent directory naming

    Args:
        matrix: Matrix object
        model: Model object

    Returns:
        formatted directory name
    """
    return f"./images/{model.name}{model.width}x{model.height}({model.x_width}x{model.y_width}deg per cell)/"


def get_estimated_latlon() -> GeographicPosition:
    """return a skyfield GeographicPosition of your estimated location using ip information

    Returns:
        GeographicPosition
    """
    import geocoder
    return wgs84.latlon(*geocoder.ip('me').latlng)


def png_to_gif(png_path: str, gif_filename: str = "./images/out.gif", duration_ms: int = 1000):
    # TODO: Proper support for generating GIF's
    import imageio.v3 as iio
    import numpy as np
    from os import listdir
    from os.path import isfile, join
    from pygifsicle import optimize

    filenames = ["" for _ in range(100)]
    for f in listdir(png_path):
        if isfile(join(png_path, f)):
            filenames[int(f.strip(".png"))] = png_path + "/" + f

    # save frames from images
    frames = np.stack([iio.imread(filename) for filename in filenames])

    # generate gif
    iio.imwrite(gif_filename, frames, duration=duration_ms, loop=0)

    # TODO: Validate that the outputs are actually smaller
    # optimise gif size
    optimize(gif_filename)
