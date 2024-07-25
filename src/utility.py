"""contains useful utilities"""
import geocoder
from skyfield.timelib import Time
from skyfield.toposlib import GeographicPosition
from skyfield.api import wgs84
from typing import Literal
from .matrix import Matrix, MatrixFrame
from .projectionmodels import BaseProjectionModel
from .models import ts, Sats
from .datasources import NORAD, SATCAT
from .picointerface import PC


def load_and_update_all_sats() -> Sats:
    """load and sats, update data from CelesTrak (NORAD) and add metadata from SATCAT

    Note this function also removes all sats with data older than 14 days as they will give inaccurate propogation data

    Returns:
        Sats object containing all objects
    """
    # load all sats and update if old
    norad = NORAD()
    norad.update_sources()
    sats = norad.load_all_sats().filter_old()

    # load all SATCAT data and update if old
    satcat = SATCAT()
    satcat.update_sources()
    satcat_data = satcat.load()

    # add tags to sats from SATCAT
    sats.add_tags_from_SATCAT(satcat_data)
    del satcat_data

    return sats


def dirname(model: BaseProjectionModel) -> str:
    """function for consistent directory naming

    Args:
        matrix: Matrix object
        model: Model object

    Returns:
        formatted directory name
    """
    return f"./images/{model.name}{model.width}x{model.height}({model.x_width}x{model.y_width}deg per cell)/"


def generate_image(sats: Sats, matrix: Matrix, model: BaseProjectionModel, t: Time = ts.now(), filename: str = "live capture.png"):
    # create frame for image
    frame = MatrixFrame(matrix, t)
    # propogate sats and populate frame
    model.compute_sat_position(sats, frame.handle_pixel_modifiers, t)
    # save image
    frame.to_png(filename)


def generate_images(sats: Sats, matrix: Matrix, model: BaseProjectionModel, t_start: Time = ts.now(), interval: float = 1, n: int = 0):
    """generate a series of images starting at the start time and with an interval of interval seconds. If n is set this will limit the number of images created otherwise it will run indefinately

    Args:
        sats: Sats objects
        matrix: Matrix object
        model: Project Grid object
        t_start: start time. Defaults to ts.now().
        interval: interval in seconds. Defaults to 1.
        n: max images. Defaults to 0.
    """
    from time import monotonic
    from datetime import timedelta

    # overwrite root directory
    matrix.path = dirname(model)

    # init
    count = 0
    t = t_start
    time_interval = timedelta(seconds=interval)

    # timing code
    t00 = monotonic()

    while True:
        # timing code
        t0 = monotonic()

        # stop if n reached - ignore if n == 0
        count += 1
        if n == count:
            break

        # create frame
        frame = MatrixFrame(matrix, t)
        # propogate model and fill frame
        model.compute_sat_position(sats, frame.handle_pixel_modifiers, t)
        # save frame
        frame.to_png(f"{frame.unix_timestamp_seconds}.png")

        # increment time
        t += time_interval

        # timing code
        t1 = monotonic()
        print(
            f"Last: {t1 - t0:.3f}s, Avg: {(t1 - t00)/count:.3f}s, Rate: {(1/((t1 - t00)/count))}/s")


def REWRITE_frame_to_pico(f: MatrixFrame, pc: PC):
    """hacky script to update matrix with data from matrix frame

    Args:
        f: matrix frame
        p: serial connection to pc
    """
    # TODO: Rewrite to send image to pico as png file???

    def update_px(x, y):
        rgb = f.get_pixel(x, y)
        if not rgb.is_off():
            pc.set_pixel_buffer(x, y, rgb)

    pc.clear_matrix()
    f._for_grid(update_px)
    pc.update_matrix()


def REWRITE_frame_to_pico_2(f0: MatrixFrame, f1: MatrixFrame, pc: PC):
    """hacky script to update matrix with data compared to last frame

    Args:
        f0: last matrix frame
        f1: next matrix frame
        pc: serial connection to pc
    """

    def update_px(x, y):
        rgb0 = f0.get_pixel(x, y)
        rgb1 = f1.get_pixel(x, y)

        if rgb0 != rgb1:
            # TODO: Implement update pixel and buffer
            pc.set_pixel_buffer(x, y, rgb1)
            pc.update_matrix()

    f0._for_grid(update_px)


def update_pico_live(sats: Sats, matrix: Matrix, model: BaseProjectionModel, pc: PC):
    """update pico with live data computed on pc

    Args:
        sats: Sats objects
        matrix: Matrix object
        model: Propogation model object
        pc: PC Pico interface object
    """
    from time import monotonic
    try:
        print("Starting live update to pico")

        # timing code
        t00 = monotonic()
        n = 0

        # empty frame for comparison
        last_frame = MatrixFrame(matrix, ts.now())

        while True:
            # timing code
            t0 = monotonic()

            # time of propogation
            t = ts.now()
            # create frame
            frame = MatrixFrame(matrix, t)
            # popogate model and fill frame
            model.compute_sat_position(sats, frame.handle_pixel_modifiers, t)
            # send to pico
            REWRITE_frame_to_pico_2(last_frame, frame, pc)

            # save last frame
            last_frame = frame

            # timing code
            t1 = monotonic()
            n += 1
            print(
                f"Last: {t1 - t0:.3f}s, Avg: {(t1 - t00)/n:.3f}s, Rate: {(1/((t1 - t00)/n))}/s")

    except KeyboardInterrupt:
        print("Stopping live update to pico")


def get_estimated_latlon() -> GeographicPosition:
    """return a skyfield GeographicPosition of your estimated location using ip information

    Returns:
        GeographicPosition
    """
    import geocoder
    return wgs84.latlon(*geocoder.ip('me').latlng)
