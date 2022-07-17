from typing import Optional, Tuple


def generate_policy(
    enable_debug: bool,
    enable_key_sharing: bool,
    require_sev_es: bool,
    enable_send: bool,
    limit_to_domain: bool,
    limit_to_sev: bool,
    minimum_firmware_version: Optional[Tuple[int, int]] = None,
) -> int:
    policy = 0x0

    if not enable_debug:
        policy |= 1

    if not enable_key_sharing:
        policy |= 1 << 1

    if require_sev_es:
        policy |= 1 << 2

    if not enable_send:
        policy |= 1 << 3

    if limit_to_domain:
        policy |= 1 << 4

    if limit_to_sev:
        policy |= 1 << 5

    if minimum_firmware_version is not None:
        api_major, api_minor = minimum_firmware_version
        policy |= (api_major & 0xFF) << 16
        policy |= (api_minor & 0xFF) << 24

    return policy
