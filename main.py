from src import *

from src.utility import png_to_gif

from datetime import datetime, timedelta
from time import monotonic

# Set white if any sat is present
cat0 = [
    AlwaysPixelModifier(RGB(255, 255, 255))
]

# set colour and intensity based on category and number of sats
cat1 = [
    TagPixelModifier("communications", RGB(100, 0, 0)),
    TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
    TagPixelModifier("navigation", RGB(0, 0, 100))
]

# highlight debris, rocket bodies and other objects and number of sats
cat2 = [
    TagPixelModifier("debis", RGB(100, 0, 0)),
    TagPixelModifier("rocket body", RGB(0, 100, 0)),
    NotTagPixelMofidier(["debris", "rocket body"], RGB(0, 0, 100))
]

# highlight orbit altitude and number of sats
cat3 = [
    AltitudeModifier(0, 1000, RGB(100, 0, 0)),
    AltitudeModifier(1000, 3000, RGB(0, 100, 0)),
    AltitudeModifier(3000, 100000, RGB(0, 0, 100))
]

# highlight distance from observer and number of sats
cat4 = [
    DistanceModifier(0, 1000, RGB(100, 0, 0)),
    DistanceModifier(1000, 3000, RGB(0, 100, 0)),
    DistanceModifier(3000, 100000, RGB(0, 0, 100))
]

# highlight age of objects
cat5 = [
    LaunchDateModifier(
        datetime(1960, 1, 1), datetime(2000, 1, 1), RGB(100, 0, 0)
    ),
    LaunchDateModifier(
        datetime(2000, 1, 1), datetime(2020, 1, 1), RGB(0, 100, 0)
    ),
    LaunchDateModifier(
        datetime(2020, 1, 1), datetime(2040, 1, 1), RGB(0, 0, 100)
    )
]

# Mega-constallations
cat6 = [
    TagPixelModifier("starlink", RGB(100, 0, 0)),
    TagPixelModifier("oneweb", RGB(0, 100, 0)),
    NotTagPixelMofidier(["starlink", "oneweb"], RGB(0, 0, 100))
]

if __name__ == "__main__":
    obs_mecd = wgs84.latlon(53.46998696814808, -2.233615253169161)
    # obs = get_estimated_latlon()

    # load all sat data
    sats = init_sats()

    # sats.print_all_tags()

    # define matrix size
    matrix = Matrix(128, 128)

    # define grid model
    model = TopocentricProjectionModel.from_FoV(matrix, sats, obs_mecd, 120)

    # # propogate and generate Sat frame
    # sat_frame = model.generate_sat_frame(ts.now())

    # # render image
    # image_frame = sat_frame.render(cat5)

    # image_frame.to_png()

    try:
        print("Starting live update to device")

        # timing code
        t00 = monotonic()
        n = 0

        t = ts.now()

        while True:
            # timing code
            t0 = monotonic()

            # time of propogation
            # t = ts.now()
            t += timedelta(seconds=0.2)

            # generate image frame
            frame = model.generate_sat_frame(t).render(cat5)

            # save
            frame.to_png(f"128 x 128/{n}.png")

            # timing code
            t1 = monotonic()
            n += 1
            print(
                f"Last: {t1 - t0:.3f}s, Avg: {(t1 - t00)/n:.3f}s, Rate: {(1/((t1 - t00)/n)):.3f}/s {' '*20}")

            if n == 100:
                png_to_gif("./images/128 x 128", duration_ms=200)
                print(frame.info())
                break

    except KeyboardInterrupt:
        print("\nStopping live update to device")
