from cli.toolkit.sev.policy import generate_policy


def test_basic_policy():
    no_debug_policy = generate_policy(
        enable_debug=False,
        enable_key_sharing=True,
        require_sev_es=False,
        enable_send=True,
        limit_to_domain=False,
        limit_to_sev=False,
        minimum_firmware_version=None,
    )

    assert no_debug_policy == 0x1

    debug_policy = generate_policy(
        enable_debug=True,
        enable_key_sharing=True,
        require_sev_es=False,
        enable_send=True,
        limit_to_domain=False,
        limit_to_sev=False,
        minimum_firmware_version=None,
    )

    assert debug_policy == 0x0

    restrictive_policy = generate_policy(
        enable_debug=False,
        enable_key_sharing=False,
        require_sev_es=True,
        enable_send=False,
        limit_to_domain=True,
        limit_to_sev=True,
        minimum_firmware_version=None,
    )

    assert restrictive_policy == 0x3F


def test_policy_with_firmware_version():
    debug_policy_with_firmware_version = generate_policy(
        enable_debug=True,
        enable_key_sharing=True,
        require_sev_es=False,
        enable_send=True,
        limit_to_domain=False,
        limit_to_sev=False,
        minimum_firmware_version=(1, 51),
    )

    assert debug_policy_with_firmware_version == 0x33010000, hex(
        debug_policy_with_firmware_version
    )

    restrictive_policy_with_firmware_version = generate_policy(
        enable_debug=False,
        enable_key_sharing=False,
        require_sev_es=True,
        enable_send=False,
        limit_to_domain=True,
        limit_to_sev=True,
        minimum_firmware_version=(1, 51),
    )

    assert restrictive_policy_with_firmware_version == 0x3301003F, hex(
        restrictive_policy_with_firmware_version
    )
