from skyfield.api import wgs84

from src import *


cat0 = [
    AlwaysPixelModifier(RGB(255, 255, 255))
]

cat1 = [
    TagPixelModifier("communications", RGB(100, 0, 0)),
    TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
    TagPixelModifier("navigation", RGB(0, 0, 100))
]

cat2 = [
    TagPixelModifier("debis", RGB(100, 0, 0)),
    TagPixelModifier("rocket body", RGB(0, 100, 0)),
    NotTagPixelMofidier(["debris", "rocket body"], RGB(0, 0, 100))
]


if __name__ == "__main__":
    obs_mecd = wgs84.latlon(53.46998696814808, -2.233615253169161)

    # load all sat data
    sats = load_and_update_all_sats()

    # sats.print_all_tags()

    # define matrix size
    matrix = Matrix(16, 16, pixel_modifiers=cat1)

    # define grid model
    cell_width, cell_height = TopocentricProjectionModel.width_and_height_from_FoV(
        matrix, 60)
    projection_model = TopocentricProjectionModel(
        matrix, obs_mecd, cell_width, cell_height)
    print(projection_model.info())

    # init connection to pico
    pc = PC()

    update_pico_live(sats, matrix, projection_model, pc)

    # while True:
    #     generate_image(sats, matrix, projection_model, ts.now())
