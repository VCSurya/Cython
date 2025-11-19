import os
import shutil
from setuptools import setup
from Cython.Build import cythonize

# === 1. Files to compile ===
files_to_compile = [
    "validation"
]

# === 2. Rename .py to .pyx ===
for file in files_to_compile:
    py_file = f"{file}.py"
    pyx_file = f"{file}.pyx"
    if os.path.exists(py_file):
        print(f"Renaming {py_file} → {pyx_file}")
        os.rename(py_file, pyx_file)

# === 3. Compile using Cython ===
setup(
    ext_modules=cythonize(
        [f"{f}.pyx" for f in files_to_compile],
        compiler_directives={'language_level': "3"},
        build_dir="build"
    ),
    script_args=["build_ext", "--inplace"]
)

# === 4. Cleanup ===
for file in files_to_compile:
    # Delete .pyx
    pyx_file = f"{file}.pyx"
    if os.path.exists(pyx_file):
        os.remove(pyx_file)
    # Delete generated .c files
    c_file = f"{file}.c"
    if os.path.exists(c_file):
        os.remove(c_file)

# Delete build folder
if os.path.exists("build"):
    shutil.rmtree("build")

print("\n✅ Compilation complete. Only .pyd files remain.")