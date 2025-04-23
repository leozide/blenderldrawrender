import os
import sys
import pathlib
from shutil import copytree, rmtree
from definitions import APP_ROOT


version = sys.argv[1]
addon_name = sys.argv[2]
type = None
try:
    type = sys.argv[3]
except IndexError as e:
    ...

app_data_dir = os.path.expandvars(r'%APPDATA%\Blender Foundation\Blender')
addons_dir = r'scripts\addons'
if type == "extension":
    addons_dir = r'extensions\user_default'
blender_dir = os.path.join(app_data_dir, version, addons_dir)
target = os.path.join(blender_dir, addon_name)

if not os.path.isdir(blender_dir):
    exit(f"{blender_dir} does not exist")

print(f"deploying to {target}")

if os.path.isdir(target):
    rmtree(target)


# https://stackoverflow.com/a/75453578/30179466
# without this, items like inc/tmp are not ignored
def callbackIgnore(paths):
    def ignoref(directory, contents):
        arr = []
        for f in contents:
            for p in paths:
                if pathlib.PurePath(directory, f).match(p):
                    arr.append(f)
        return arr

    return ignoref


patterns = [
    "__pycache__",
    ".git",
    ".idea",
    ".pytest_cache",
    ".build",
    "brickset",
    "experiments",
    "inc/tmp",
    "*.blend1",
    ".gitattributes",
    ".gitignore",
    "_deploy.py",
    "requirements.txt",
]

copytree(APP_ROOT, target, dirs_exist_ok=True, ignore=callbackIgnore(patterns))
