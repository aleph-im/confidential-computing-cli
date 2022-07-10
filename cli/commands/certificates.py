import typer

from cli_config import CliConfig
from typing import cast
from pathlib import Path
from urllib.parse import urlparse
from toolkit.download_file import download_file
from zipfile import ZipFile

import sevtool
from toolkit.certificates import generate_launch_blob, get_platform_certificates_dir

certificates_ns = typer.Typer()


@certificates_ns.command()
def get_platform_certificates(ctx: typer.Context):
    endpoint = "/sev/platform/certificates"

    cli_config = cast(CliConfig, ctx.obj)

    certificates_dir = get_platform_certificates_dir(cli_config.server_url)
    certificates_dir.mkdir(parents=True, exist_ok=True)

    zip_file = certificates_dir / "platform_certificates.zip"
    download_file(cli_config.server_url + endpoint, zip_file)

    with ZipFile(zip_file) as zip_file:
        zip_file.extractall(path=certificates_dir)

    typer.echo(f"Platform certificates written to '{certificates_dir}'.")


@certificates_ns.command()
def validate_platform_certificates(ctx: typer.Context):
    cli_config = cast(CliConfig, ctx.obj)

    certificates_dir = get_platform_certificates_dir(cli_config.server_url)
    result = sevtool.validate_cert_chain(certificates_dir)

    if result:
        typer.echo(f"Platform certificates for {cli_config.server_url} are valid.")

    else:
        typer.echo(
            f"Platform certificates for {cli_config.server_url} are invalid!", err=True
        )


@certificates_ns.command()
def generate_guest_owner_certificates(
    ctx: typer.Context,
    policy: str = typer.Argument(None, help="SEV guest policy."),
):
    cli_config = cast(CliConfig, ctx.obj)

    certificates_dir = get_platform_certificates_dir(cli_config.server_url)
    generate_launch_blob(policy, cli_config.server_url)

    typer.echo(
        "Generated guest owner certificates (godh.cert, tmp_tk.bin, launch_blob.bin) "
        f"in '{certificates_dir}'."
    )

    with ZipFile(certificates_dir / "guest-owner-certificates.zip", "w") as zip_file:
        for filename in ("godh.cert", "launch_blob.bin"):
            zip_file.write(certificates_dir / filename, filename)
