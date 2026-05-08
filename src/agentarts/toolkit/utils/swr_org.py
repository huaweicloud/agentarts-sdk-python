"""SWR organization name generator."""

import hashlib
import random
import string

from agentarts.sdk.utils.constant import get_ak


def shorten_region(region: str) -> str:
    """
    Shorten region name to a compact form.

    Examples:
        cn-southwest-2 -> cnsw2
        cn-north-4 -> cnno4
        ap-southeast-1 -> apse1

    Args:
        region: Full region name (e.g., 'cn-southwest-2')

    Returns:
        Shortened region name (max 6 chars)
    """
    parts = region.split("-")
    if len(parts) >= 3:
        provider = parts[0][:2]
        area = parts[1][:2]
        num = parts[2] if len(parts) > 2 else ""
        if len(num) > 2:
            num = num[:2]
        return f"{provider}{area}{num}"
    return region.replace("-", "")[:6]


def generate_ak_identifier(ak: str | None = None, length: int = 8) -> str:
    """
    Generate identifier from AK (Access Key).

    If AK is available, uses hash of AK to generate consistent identifier.
    If AK is not available, generates random identifier.

    Args:
        ak: Access Key string. If None, will try to get from environment.
        length: Length of identifier to generate (default 8)

    Returns:
        Identifier string of specified length
    """
    if ak is None:
        ak = get_ak()

    if ak and len(ak) > 0:
        hash_obj = hashlib.md5(ak.encode(), usedforsecurity=False)
        hash_hex = hash_obj.hexdigest()
        return hash_hex[:length].lower()

    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def generate_random_suffix(length: int = 6) -> str:
    """
    Generate random suffix for uniqueness.

    Args:
        length: Length of random suffix (default 6)

    Returns:
        Random string of lowercase letters and digits
    """
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def generate_default_agent_name(base_name: str = "myagent", suffix_length: int = 5) -> str:
    """
    Generate default agent name with random suffix.

    Args:
        base_name: Base name for the agent (default: 'myagent')
        suffix_length: Length of random suffix (default 5)

    Returns:
        Agent name with random suffix (e.g., 'myagent-abc12')
    """
    suffix = generate_random_suffix(suffix_length)
    return f"{base_name}-{suffix}"


def generate_swr_org_name(
    region: str | None = None,
    ak: str | None = None,
    max_length: int = 64,
) -> str:
    """
    Generate unique SWR organization name.

    Format: agentarts-{region_short}-{ak_identifier}-org

    The generated name is designed to be:
    1. Unique per account (based on AK hash)
    2. Consistent per account (same AK generates same name)
    3. Within max_length constraint (default 64 chars)

    Args:
        region: Huawei Cloud region (e.g., 'cn-southwest-2')
                 If None, uses 'default' as placeholder
        ak: Access Key for account identification
                 If None, will try to get from environment
        max_length: Maximum length of organization name (default 64)

    Returns:
        Unique SWR organization name

    Examples:
        >>> generate_swr_org_name("cn-southwest-2", "ABCDEFGHIJKLMNOP")
        'agentarts-cnso2-19fc8eff-org'

        >>> generate_swr_org_name("cn-southwest-2")  # AK from env
        'agentarts-cnso2-<ak_hash>-org'
    """
    prefix = "agentarts-"
    suffix = "-org"

    region_short = shorten_region(region or "default")

    ak_identifier = generate_ak_identifier(ak, length=8)

    base_name = f"{prefix}{region_short}-{ak_identifier}{suffix}"

    if len(base_name) > max_length:
        excess = len(base_name) - max_length
        ak_identifier = generate_ak_identifier(ak, length=8 - min(excess, 8))
        base_name = f"{prefix}{region_short}-{ak_identifier}{suffix}"

        if len(base_name) > max_length:
            region_short = region_short[: len(region_short) - min(len(base_name) - max_length, len(region_short))]
            base_name = f"{prefix}{region_short}{suffix}"

    return base_name.lower()
