"""
Global configuration object for the CLI.
"""

from dataclasses import dataclass


@dataclass
class CliConfig:
    server_url: str
    username: str
    password: str
    verbose: bool
