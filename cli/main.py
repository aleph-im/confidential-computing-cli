from pathlib import Path
from typing import Optional

import typer

from cli_config import CliConfig
from commands.certificates import certificates_ns
from commands.vms import vm_ns

app = typer.Typer()


def validate_config_file_path(config: Optional[Path]) -> Optional[Path]:
    if config is not None:
        if not config.is_file():
            raise typer.BadParameter(f"'{config.absolute()}' does not exist")

    return config


def validate_key_dir(key_dir: Optional[Path]) -> Optional[Path]:
    if key_dir is not None:
        if key_dir.exists and not key_dir.is_dir():
            raise typer.BadParameter(
                f"'{key_dir.absolute()}' already exists and is not a directory"
            )

    return key_dir


@app.callback()
def main(
    ctx: typer.Context,
    server_url: str = typer.Option(
        ...,
        help="URL of the confidential VM server.",
    ),
    username: str = typer.Option("odesenfans", help="Username."),
    password: str = typer.Option("4md_s3v", help="Password."),
    verbose: bool = typer.Option(False, help="Show more information."),
):
    cli_config = CliConfig(
        server_url=server_url,
        username=username,
        password=password,
        verbose=verbose,
    )

    ctx.obj = cli_config


app.add_typer(certificates_ns, name="certificate", help="Download and upload SEV certificates from the platform.")
app.add_typer(vm_ns, name="vm", help="Create, start and manage virtual machines (VMs).")
# app.add_typer(migrations_ns, name="migrations", help="Run DB migrations.")


if __name__ == "__main__":
    app()
