"""backend for generating csv data for unity

used to generate csv files for unity with ICRS position and velocity relative to IRCS reference frame, where the filename is the unix timestamp of the generation time"""
from src import *
import os
import math

if __name__ == "__main__":
    sats = init_sats()

    # set propogation time
    t = ts.now()
    unix_timestamp = int(t.utc_datetime().timestamp())  # type: ignore

    # generate path
    dir = "./data/csv/"
    file = f"ITRS{unix_timestamp}.csv"
    filepath = dir + file

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(filepath, "w") as f:
        f.write(
            "name,launch_date,x[km],y[km],z[km],x_v[km/s],y_v[km/s],z_v[km/s]\n")

        for sat in sats.sats:
            x, y, z, x_v, y_v, z_v = sat.ITRS_cartesian_position_and_velocity_at(
                t)

            # remove invalid projection from data
            valid = True
            for item in [x, y, z, x_v, y_v, z_v]:
                if math.isnan(item):
                    valid = False
                    break
            if not valid:
                continue

            launch_date = str(sat.launch_date.date()
                              ) if sat.launch_date else ""

            f.write(
                f"{sat.name},{launch_date},{x},{y},{z},{x_v},{y_v},{z_v}\n")
