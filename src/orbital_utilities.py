import numpy as np
from .const import *

def true_to_mean_anomaly(nu, e):
    """
    Convert true anomaly (nu) to mean anomaly (M) for elliptical orbits.
    nu and e may be scalars or numpy arrays.
    Angles must be in radians.
    """
    # Step 1: Eccentric anomaly from true anomaly
    E = 2 * np.arctan2(
        np.sqrt(1 - e) * np.sin(nu / 2),
        np.sqrt(1 + e) * np.cos(nu / 2)
    )

    # Step 2: Mean anomaly from eccentric anomaly
    M = E - e * np.sin(E)

    return M


def sso_inclination(alt_km, e=0.0):
    """
    Compute the inclination (degrees) of a Sun-Synchronous Orbit (SSO) for a given altitude (km) and eccentricity.

    Parameters:
        alt_km : float or array_like
            Altitude above Earth's surface in kilometers.
        e : float, optional
            Eccentricity of the orbit (default=0 for circular orbit).

    Returns:
        i_deg : float or ndarray
            Inclination in degrees.
    """
    # Constants
    omega_dot_sun = 0.9856 * np.pi/180  # desired nodal precession, rad/day
    omega_dot_sun_rad = omega_dot_sun / 86400  # rad/sec

    # Semi-major axis
    a = EARTH_RADIUS + alt_km  # km

    # Compute inclination
    cos_i = -2 * omega_dot_sun_rad * \
        a**(7/2) * (1 - e**2)**2 / (3 * J2 * EARTH_RADIUS**2 * np.sqrt(MU))

    # Ensure valid range for arccos
    cos_i = np.clip(cos_i, -1.0, 1.0)

    i_rad = np.arccos(cos_i)
    i_deg = np.degrees(i_rad)

    return i_deg

def find_clusters(orbital_positions, threshold_km) -> None:
    """print a list of all satellites within a threshold number of km of each other

    this function is slow and not optimised

    Args:
        orbital_positions: set of orbital positions, `list[OrbitalPosition]` object
        threshold_km: distance km
    """
    print(f"Searching {len(orbital_positions)} satellite positions for cluster groups with {threshold_km}km")

    pairs = []
    paired: list[str] = []
    for i in range(len(orbital_positions)):
        pairs_temp = [orbital_positions[i]]
        for j in range(i + 1, len(orbital_positions)):
            p0 = orbital_positions[i]
            p1 = orbital_positions[j]
            if p1.sat.name in paired:
                continue
            if p0.geo.distance(p1.geo) <= threshold_km:
                pairs_temp.append(p1)
                paired.append(p1.sat.name)
        if len(pairs_temp) > 1:
            pairs.append(pairs_temp)
        n = len(pairs_temp)
        end = "\r" if n == 1 else "\n"
        print(
            f"sat n={i}, pairs={len(pairs_temp)-1} {"names=" if n>1 else ""}{[s.sat.name for s in pairs_temp] if n > 1 else ""} {"ids=" if n>1 else ""}{[s.sat.norad_cat_id for s in pairs_temp] if n > 1 else ""}",
            end=end
        )

    print(f"Found {len(pairs)} cluster groups within {threshold_km}km")
