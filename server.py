"""This script can be used to control any device that implements the DeviceInterface schema, see supported devices under hardware"""
from time import monotonic
from src.datasources import init_sats
from src.deviceinterface import DeviceInterface
from src.matrix import Matrix, RGB
from src.projectionmodels import TopocentricProjectionModel, GeocentricProjectionModel
from src.utility import get_estimated_latlon
from src.analysis import TagPixelModifier
from src import ts


modifier = [
    TagPixelModifier("communications", RGB(100, 0, 0)),
    TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
    TagPixelModifier("navigation", RGB(0, 0, 100))
]


if __name__ == "__main__":
    # set observer location
    obs = get_estimated_latlon()

    # load all sats
    sats = init_sats()

    # connect to device and init
    device = DeviceInterface()
    device.clear()

    # define matrix
    matrix = Matrix(*device.display_dimensions())

    # define projection model
    model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, 90)

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
            frame = model.generate_sat_frame(t).render(modifier)

            # send to device
            device.upload_frame(frame)

            # timing code
            t1 = monotonic()
            n += 1
            print(
                f"Last: {t1 - t0:.3f}s, Avg: {(t1 - t00)/n:.3f}s, Rate: {(1/((t1 - t00)/n)):.3f}/s {' '*20}", end="\r")

    except KeyboardInterrupt:
        print("\nStopping live update to device")
