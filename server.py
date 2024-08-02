"""This script can be used to control any device that implements the DeviceInterface schema, see supported devices under hardware"""
from time import monotonic
from src.datasources import init_sats
from src.deviceinterface import DeviceInterface
from src.matrix import Matrix, RGB
from src.projectionmodels import TopocentricProjectionModel, GeocentricProjectionModel
from src.utility import get_estimated_latlon
from src.analysis import TagPixelModifier, LaunchDateModifier
from src import ts


from datetime import datetime

modifier0 = [
    TagPixelModifier("communications", RGB(255, 0, 0)),
    TagPixelModifier("weather & earth resources", RGB(0, 255, 0)),
    TagPixelModifier("navigation", RGB(0, 0, 255))
]

modifier1 = [
    LaunchDateModifier(
        datetime(1960, 1, 1), datetime(2000, 1, 1), RGB(255, 0, 0)
    ),
    LaunchDateModifier(
        datetime(2000, 1, 1), datetime(2020, 1, 1), RGB(0, 255, 0)
    ),
    LaunchDateModifier(
        datetime(2020, 1, 1), datetime(2040, 1, 1), RGB(0, 0, 255)
    )
]


if __name__ == "__main__":
    # set observer location
    obs = get_estimated_latlon()

    # load all sats
    sats = init_sats()

    # connect to device and init
    device = DeviceInterface()

    # define matrix
    matrix = Matrix(*device.display_dimensions())

    # define projection model
    model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, 50)

    try:
        print("Starting live update to device")

        # timing code
        t00 = monotonic()
        n = 0

        while True:
            # timing code
            t0 = monotonic()

            # time of propogation
            t = ts.now()

            # generate image frame
            frame = model.generate_sat_frame(t).render(modifier1)

            # send to device
            device.upload_frame(frame)

            # timing code
            t1 = monotonic()
            n += 1
            print(
                f"Last: {t1 - t0:.3f}s, Avg: {(t1 - t00)/n:.3f}s, Rate: {(1/((t1 - t00)/n)):.3f}/s {' '*20}", end="\r")

    except KeyboardInterrupt:
        print("\nStopping live update to device")
