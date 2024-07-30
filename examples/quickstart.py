from src import *

lat = 53.46998696814808
lon = -2.233615253169161

observer = wgs84.latlon(lat, lon)

sats = init_sats()

px_width = 32
px_height = 32
modifers = [AlwaysPixelModifier(RGB(255, 255, 255))]
matrix = Matrix(px_width, px_height, pixel_modifiers=modifers)

FoV = 100
cell_width, cell_height = TopocentricProjectionModel.width_and_height_from_FoV(
    matrix, FoV)

projection_model = TopocentricProjectionModel(
    matrix, observer, cell_width, cell_height)

print(projection_model.info())

generate_image(sats, matrix, projection_model)

# TODO: Test
# TODO: Write documentation
