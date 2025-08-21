"""backend for generating csv data for unity

used to generate csv files for unity with ICRS position and velocity relative to IRCS reference frame, where the filename is the unix timestamp of the generation time

please note this method is intended to be called from the project root directory to make root of the same cached files as the rest of the core project
"""
# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from src import *
import math
# fmt: on

if __name__ == "__main__":
    # load all sats
    sats = init_sats()

    # set propogation time
    t = ts.now()
    unix_timestamp = int(t.utc_datetime().timestamp())  # type: ignore

    # define propagation model
    propagation_model = SGP4Propagation()

    # generate path
    dir = "./data/csv/"
    file = f"ITRS{unix_timestamp}.csv"
    filepath = dir + file

    # create path if not exists
    if not os.path.exists(dir):
        os.makedirs(dir)

    # open output file
    with open(filepath, "w") as f:
        f.write(
            "name,launch_date,x[km],y[km],z[km],x_v[km/s],y_v[km/s],z_v[km/s]\n")

        # iterate through and propagate all sats
        for sat in sats.sats:
            position = propagation_model.propagate(sats, t)[0]
            x, y, z, x_v, y_v, z_v = position.geo.cartesian_position_and_velocity()

            # remove invalid projection from data
            valid = True
            for item in [x, y, z, x_v, y_v, z_v]:
                if math.isnan(item):
                    valid = False
                    break
            if not valid:
                continue

            # convert launch_date to string
            launch_date = str(sat.launch_date.date()
                              ) if sat.launch_date else ""

            # write a sat to file
            f.write(
                f"{sat.name},{launch_date},{x},{y},{z},{x_v},{y_v},{z_v}\n")

    print(f"Generated output file: {filepath}")
