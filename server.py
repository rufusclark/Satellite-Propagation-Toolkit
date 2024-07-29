"""This script can be used to control any device that implements the DeviceInterface schema, see supported devices under hardware"""
from src import DeviceInterface, get_estimated_latlon, load_and_update_all_sats, Matrix, TagPixelModifier, RGB, TopocentricProjectionModel, update_device_live

modifier = [
    TagPixelModifier("communications", RGB(100, 0, 0)),
    TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
    TagPixelModifier("navigation", RGB(0, 0, 100))
]

if __name__ == "__main__":
    # set observer location
    obs = get_estimated_latlon()

    # load all sats
    sats = load_and_update_all_sats()

    # connect to device and init
    device = DeviceInterface()
    device.clear()

    # define matrix
    matrix = Matrix(*device.display_dimensions(), pixel_modifiers=modifier)

    # define projection model
    model = TopocentricProjectionModel.from_FoV(matrix, obs, 90)

    # update the device
    update_device_live(device, sats, matrix, model)
