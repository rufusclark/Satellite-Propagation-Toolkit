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

if __name__ == "__main__":
    obs_mecd = wgs84.latlon(53.46998696814808, -2.233615253169161)

    # load all sat data
    sats = load_and_update_all_sats()

    # sats.print_all_tags()

    # define matrix size
    matrix = Matrix(16, 16, pixel_modifiers=cat5)

    # define grid model
    cell_width, cell_height = TopocentricProjectionModel.width_and_height_from_FoV(
        matrix, 60)
    projection_model = TopocentricProjectionModel(
        matrix, obs_mecd, cell_width, cell_height)

    print(projection_model.info())

    # init connection to pico
    pc = PC()

    print(get_estimated_latlon())

    update_pico_live(sats, matrix, projection_model, pc)

    # while True:
    #     generate_image(sats, matrix, projection_model, ts.now())
