import os
from cx_Freeze import setup, Executable

setup(
    name = "unit",
    version = "0.1.1",
    description = "Helm unit plugin",
    executables = [Executable("helm-unit.py")]
    
)