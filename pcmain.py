import time

from skyfield.api import wgs84

from datasources import NORAD, SATCAT
from ledmatrix import Matrix, MatrixFrame
from models import ts, Orbits
from projectiongrids import TopocentricProjectionGrid, GeocentricProjectionGrid
from picointerface import PC
from analysis import TagPixelModifier, NotTagPixelMofidier
from rgb import RGB
from utility import load_and_update_all_sats, generate_image, generate_images, update_pico_live

cat1 = [
    TagPixelModifier("communications", RGB(100, 0, 0)),
    TagPixelModifier([
        "weather & earth resources", "science", "miscellaneous"
    ], RGB(0, 100, 0)),
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
    cell_width, cell_height = TopocentricProjectionGrid.width_and_height_from_FoV(
        matrix, 60)
    grid_model = TopocentricProjectionGrid(
        matrix, obs_mecd, cell_width, cell_height)
    print(grid_model.info())

    # init connection to pico
    # p = PC()

    while True:
        generate_image(sats, matrix, grid_model, ts.now())
