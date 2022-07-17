from typing import cast, Literal, Union
from zipfile import ZipFile

import typer

import cli.toolkit.sev.sevtool as sevtool
from cli.toolkit.sev.policy import generate_policy as generate_sev_policy
from cli.cli_config import CliConfig
from cli.toolkit.certificates import generate_launch_blob, get_platform_certificates_dir
from cli.toolkit.download_file import download_file

platform_ns = typer.Typer()


@platform_ns.command()
def get_certificates(ctx: typer.Context):
    endpoint = "/platform/certificates"

    cli_config = cast(CliConfig, ctx.obj)

    certificates_dir = get_platform_certificates_dir(cli_config.server_url)
    certificates_dir.mkdir(parents=True, exist_ok=True)

    zip_file = certificates_dir / "platform_certificates.zip"
    download_file(cli_config.server_url + endpoint, zip_file)

    with ZipFile(zip_file) as zip_file:
        zip_file.extractall(path=certificates_dir)

    typer.echo(f"Platform certificates written to '{certificates_dir}'.")


@platform_ns.command()
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


@platform_ns.command()
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


BooleanCliInput = str


@platform_ns.command()
def generate_policy(
    enable_debug: BooleanCliInput = typer.Option(..., prompt="Enable debug? [Y/N]"),
    enable_key_sharing: BooleanCliInput = typer.Option(
        ..., prompt="Enable key sharing? [Y/N]"
    ),
    require_sev_es: BooleanCliInput = typer.Option(
        ..., prompt="Require SEV Encrypted State (SEV-ES)? [Y/N]"
    ),
    enable_send: BooleanCliInput = typer.Option(
        ..., prompt="Enable sending the VM? [Y/N]"
    ),
    limit_to_domain: BooleanCliInput = typer.Option(
        ..., prompt="Limit VM to domain? [Y/N]"
    ),
    limit_to_sev: BooleanCliInput = typer.Option(
        ..., prompt="Limit to VM to SEV enabled systems? [Y/N]"
    ),
    minimum_firmware_version: str = typer.Option(
        ..., prompt="Minimum firmware version? [ex: 1.51]"
    ),
):
    def to_bool(cli_input: BooleanCliInput) -> bool:
        return cli_input.lower() == "y"

    if minimum_firmware_version == 0:
        firmware_version = None
    else:
        version_parts = minimum_firmware_version.split(".")
        if len(version_parts) != 2:
            typer.echo(
                "Invalid firmware version format: use MAJOR.MINOR. Ex: 1.51.", err=True
            )

        firmware_version = (int(version_parts[0]), int(version_parts[1]))

    policy = generate_sev_policy(
        enable_debug=to_bool(enable_debug),
        enable_key_sharing=to_bool(enable_key_sharing),
        require_sev_es=to_bool(require_sev_es),
        enable_send=to_bool(enable_send),
        limit_to_domain=to_bool(limit_to_domain),
        limit_to_sev=to_bool(limit_to_sev),
        minimum_firmware_version=firmware_version,
    )

    typer.echo(f"SEV policy: '{hex(policy)}'.")
