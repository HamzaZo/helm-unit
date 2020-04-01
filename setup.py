import os
from cx_Freeze import setup, Executable

setup(
    name = "unit",
    version = "0.1.0",
    description = "Helm unit plugin",
    executables = [Executable("unit.py")]
    
)