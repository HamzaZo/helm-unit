from cx_Freeze import setup, Executable

setup(
    name="unit",
    version="0.1.4",
    description="Helm unit plugin",
    executables=[Executable("src/helm-unit.py")]
)
