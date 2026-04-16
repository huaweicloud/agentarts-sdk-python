"""
Common utility functions
"""

import random
import string


def generate_random_string(length: int = 4) -> str:
    """Generate a random string of specified length

    Args:
        length: Length of the random string, default is 4, must be between 4 and 64

    Returns:
        str: Random string containing letters and digits

    Raises:
        ValueError: If length is less than 4 or greater than 64
    """
    if length < 4 or length > 64:
        msg = f"Length must be between 4 and 64, got {length}"
        raise ValueError(msg)
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
