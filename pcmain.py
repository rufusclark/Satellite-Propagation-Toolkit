from skyfield.api import wgs84

from src import *

from datetime import datetime

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
    sats = load_and_update_all_sats()

    # sats.print_all_tags()

    # define matrix size
    matrix = Matrix(16, 16, pixel_modifiers=cat0)

    # define grid model
    # projection_model = GeocentricProjectionModel(
    # matrix, obs_mecd, 0.5, 0.5)

    projection_model = TopocentricProjectionModel.from_FoV(
        matrix, obs_mecd, 90)

    print(projection_model.info())

    # init connection to pico and send live projections
    pc = PC()
    pc.clear_matrix()
    update_pico_live_2(sats, matrix, projection_model, pc)

    # while True:
    #     generate_image(sats, matrix, projection_model,
    #                    ts.now())
