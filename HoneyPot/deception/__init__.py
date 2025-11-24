"""
Honeypot Deception Module
This module provides fake file system and command execution
for SSH honeypot environments.
"""

from .pseudo_fs import PseudoFS, run_command

__version__ = "1.0.0"
__author__ = "Honeypot Team"
__all__ = ['PseudoFS', 'run_command']