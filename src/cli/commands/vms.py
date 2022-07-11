import base64
import os
from pathlib import Path
from typing import cast
from urllib.parse import urlparse
from zipfile import ZipFile

import requests
import typer
from requests.auth import HTTPBasicAuth

from cli.cli_config import CliConfig
from cli.toolkit.certificates import (
    generate_launch_blob,
    get_vm_certificates_dir,
    get_platform_certificates_dir,
    load_tik_tek_keys,
    compute_measure,
    make_secret_table,
    encrypt_secret_table,
    make_packet_header,
)

vm_ns = typer.Typer()


OVMF_HASH = "7a2f841fe8a61cfdc02a17dd56f01c8c69492d9bb84d0097c7f349fc1d429680"


@vm_ns.command()
def create(ctx: typer.Context):
    cli_config = cast(CliConfig, ctx.obj)
    response = requests.post(
        cli_config.server_url + "/vm",
        auth=HTTPBasicAuth(cli_config.username, cli_config.password),
    )
    response.raise_for_status()

    typer.echo(response.json())


@vm_ns.command()
def get(ctx: typer.Context, vm_id: str):
    cli_config = cast(CliConfig, ctx.obj)
    response = requests.get(
        cli_config.server_url + f"/vm/{vm_id}",
        auth=HTTPBasicAuth(cli_config.username, cli_config.password),
    )
    response.raise_for_status()

    typer.echo(response.json())


@vm_ns.command()
def upload_image(ctx: typer.Context, vm_id: str, tarball_path: Path, image_name: str):
    cli_config = cast(CliConfig, ctx.obj)

    endpoint = f"/vm/{vm_id}/upload-image"

    typer.echo(
        f"Uploading VM image to {cli_config.server_url}. "
        "This may take a while, wait until the process completes."
    )
    with tarball_path.open("rb") as f:
        response = requests.post(
            cli_config.server_url + endpoint,
            params={"image_name": image_name},
            files={"vm_image_tarball": f},
            auth=HTTPBasicAuth(cli_config.username, cli_config.password),
        )

    response.raise_for_status()

    typer.echo(f"Successfully uploaded VM image for VM {vm_id}.")


@vm_ns.command()
def upload_certificates(
    ctx: typer.Context,
    vm_id: str,
    policy: str = typer.Argument(..., help="SEV guest policy."),
):
    cli_config = cast(CliConfig, ctx.obj)
    server_url = cli_config.server_url

    endpoint = f"/vm/{vm_id}/upload-guest-owner-certificates"

    typer.echo("Generating launch blob...")
    generate_launch_blob(policy=policy, server_url=server_url)

    platform_certificates_dir = get_platform_certificates_dir(server_url)
    vm_certificates_dir = get_vm_certificates_dir(vm_id)
    vm_certificates_dir.mkdir(exist_ok=True, parents=True)

    for filename in ("godh.cert", "tmp_tk.bin", "launch_blob.bin"):
        source = platform_certificates_dir / filename
        source.rename(vm_certificates_dir / filename)

    typer.echo("Creating certificates archive for upload...")
    certificates_archive = vm_certificates_dir / "guest-owner-certificates.zip"
    with ZipFile(certificates_archive, "w") as zip_file:
        for filename in ("godh.cert", "launch_blob.bin"):
            zip_file.write(vm_certificates_dir / filename, filename)

    typer.echo(f"Uploading guest owner certificates to {cli_config.server_url}.")
    with certificates_archive.open("rb") as f:
        response = requests.post(
            cli_config.server_url + endpoint,
            files={"guest_owner_certificates": f},
            auth=HTTPBasicAuth(cli_config.username, cli_config.password),
        )

    response.raise_for_status()

    typer.echo(f"Successfully uploaded guest owner certificates for VM {vm_id}.")


@vm_ns.command()
def start(ctx: typer.Context, vm_id: str):
    cli_config = cast(CliConfig, ctx.obj)

    endpoint = f"/vm/{vm_id}/start"

    response = requests.post(
        cli_config.server_url + endpoint,
        auth=HTTPBasicAuth(cli_config.username, cli_config.password),
    )

    response.raise_for_status()


def fetch_measure(vm_id: str, cli_config: CliConfig):
    endpoint = f"/vm/{vm_id}/sev/measure"

    response = requests.get(
        cli_config.server_url + endpoint,
        auth=HTTPBasicAuth(cli_config.username, cli_config.password),
    )

    response.raise_for_status()
    return response.json()


@vm_ns.command()
def measure(ctx: typer.Context, vm_id: str):
    cli_config = cast(CliConfig, ctx.obj)

    measure_data = fetch_measure(vm_id, cli_config)
    typer.echo(measure_data)


@vm_ns.command()
def inject_secret(
    ctx: typer.Context,
    vm_id: str,
    secret: str = typer.Argument(None),
):
    cli_config = cast(CliConfig, ctx.obj)

    typer.echo("Measuring the VM memory...")
    vm_sev_data = fetch_measure(vm_id, cli_config)

    typer.echo("Validating the measurement...")
    tik, tek = load_tik_tek_keys(vm_id)

    launch_measure = base64.b64decode(vm_sev_data["launch_measure"])
    vm_measure = launch_measure[0:32]
    nonce = launch_measure[32:48]

    expected_measure = compute_measure(
        sev_info=vm_sev_data["sev_info"], tik=tik, expected_hash=OVMF_HASH, nonce=nonce
    ).digest()

    if expected_measure != vm_measure:
        typer.echo(
            f"Measures do not match: expected '{expected_measure.hex()}', "
            f"got '{vm_measure.hex()}' instead."
        )
        typer.Exit(1)

    typer.echo("Measures match! Generating secret table...")
    secret_table = make_secret_table(secret)
    iv = os.urandom(16)
    encrypted_secret_table = encrypt_secret_table(
        secret_table=secret_table, tek=tek, iv=iv
    )
    typer.echo("Generating packet header...")
    packet_header = make_packet_header(
        vm_measure=vm_measure,
        encrypted_secret_table=encrypted_secret_table,
        secret_table_size=len(secret_table),
        tik=tik,
        iv=iv,
    )

    typer.echo("Uploading the secret table and launching the VM...")
    endpoint = f"/vm/{vm_id}/sev/inject-secret"

    response = requests.post(
        cli_config.server_url + endpoint,
        params={
            "packet_header": base64.b64encode(packet_header).decode(),
            "secret": base64.b64encode(encrypted_secret_table).decode(),
        },
        auth=HTTPBasicAuth(cli_config.username, cli_config.password),
    )

    response.raise_for_status()
    vm = response.json()

    typer.echo(f"Successfully started VM {vm_id}.")
    typer.echo("Decrypting the OS and booting the disk may take a while.")
    typer.echo(f"SSH: {urlparse(cli_config.server_url).netloc}:{vm['ssh_port']}.")

    # TODO remove
    typer.echo(vm)
