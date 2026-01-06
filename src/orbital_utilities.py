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
