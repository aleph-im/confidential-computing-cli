import subprocess
from typing import Dict, Optional

from pathlib import Path


def get_command_status_code(result: subprocess.CompletedProcess) -> int:
    # sevtool does not return error codes, we must parse them from stdout
    command_result_str = result.stdout.split("\n")[-2]
    if command_result_str == "Command Successful":
        return 0

    error_code = command_result_str.split(": ")[1]
    return int(error_code, 16)


def check_command_result(result: subprocess.CompletedProcess):
    # If sevtool does not understand the command-line arguments, it will write
    # the error to stderr
    if result.stderr:
        raise ValueError(f"Invalid sevtool command: {result.stderr}")

    status_code = get_command_status_code(result)
    if status_code != 0:
        raise ValueError(f"sevtool command failed: {result.stdout}")


def sevtool_cmd(*args, volumes: Optional[Dict[str, str]] = None):
    volumes = volumes or {}

    volume_options = []
    for k, v in volumes.items():
        volume_options.extend(["-v", f"{k}:{v}"])
    result = subprocess.run(
        ["docker", "run", "--rm", *volume_options, "odesenfans/sevtool", *args],
        capture_output=True,
        text=True,
    )

    check_command_result(result)
    return result


def validate_cert_chain(certificates_dir: Path) -> bool:
    # TODO: use the original certificate chain from the AMD website and not the one provided
    #       by the Platform Owner!!! Only use this for demo purposes or on platforms we own.
    container_certificates_dir = "/opt/certificates"

    _ = sevtool_cmd(
        "--ofolder",
        container_certificates_dir,
        "--validate_cert_chain",
        volumes={str(certificates_dir.absolute()): container_certificates_dir},
    )

    return True


def generate_launch_blob(certificates_dir: Path, policy: str) -> None:
    container_certificates_dir = "/opt/certificates"

    _ = sevtool_cmd(
        "--ofolder",
        container_certificates_dir,
        "--generate_launch_blob",
        policy,
        volumes={str(certificates_dir.absolute()): container_certificates_dir},
    )
