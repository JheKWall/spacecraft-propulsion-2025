"""Derived metrics.

Pure functions only - no I/O, no database, no pandas. Everything here is
computed from collected values rather than read from a source, which is exactly
why it needs tests: a wrong thrust-to-weight ratio has no citation trail that
would reveal the error.
"""
from config import G0, SPEED_OF_LIGHT


def _missing(*values) -> bool:
    """True if any value is None or NaN.

    pandas hands back NaN for empty CSV cells, which is the normal case for
    every theoretical system, so this is the expected path rather than an error.
    """
    for v in values:
        if v is None:
            return True
        if isinstance(v, float) and v != v:   # NaN is the only value unequal to itself
            return True
    return False


def thrust_to_weight(thrust_low, thrust_high, mass_low, mass_high):
    """Thrust-to-weight ratio as a (low, high) range.

    Both inputs are ranges, so the bounds must be paired against each other:
    the worst case is the LEAST thrust over the GREATEST mass, and the best case
    is the MOST thrust over the LEAST mass. Pairing low-with-low and
    high-with-high would understate the true spread.

    Returns (None, None) when either input is absent - which is every
    theoretical system, by design. The absence is a finding, not a gap.
    """
    if _missing(thrust_low, thrust_high, mass_low, mass_high):
        return (None, None)
    if mass_low <= 0 or mass_high <= 0:
        raise ValueError(f"engine mass must be positive, got {mass_low}-{mass_high}")
    return (
        thrust_low / (mass_high * G0),
        thrust_high / (mass_low * G0),
    )


def exceeds_light_speed(isp_seconds) -> bool:
    """True if a specific impulse implies an exhaust velocity above c.

    This is the assertion that would have caught the corrupted figure in the
    original dataset: Starting Notes.txt recorded antimatter annihilation at
    100,000,000 km/s, which is roughly 333 times the speed of light.
    """
    if _missing(isp_seconds):
        return False
    return (isp_seconds * G0) > SPEED_OF_LIGHT
