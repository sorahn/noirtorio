from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import IO, Iterable, List, Optional, Tuple, Set, Dict
import zipfile


@dataclass(eq=True, frozen=True)
class LazyFile:
    mod_type: str
    mod_path: Path
    file_path: str
    lua_path: str

    def open(self) -> IO[bytes]:
        if self.mod_type == "file":
            return (self.mod_path / self.file_path).open("rb")

        elif self.mod_type == "zip":
            with zipfile.ZipFile(str(self.mod_path), "r") as zfile:
                return zfile.open(self.file_path, "r")

        else:
            raise Exception(f"Unknown mod_type: {self.mod_type}")

class Mod:
    mod_path: Path
    all_files: Set[str]
    name: str
    file_prefix: str
    mod_type: str

    def __init__(self, mod_name: str, mod_path: Path):
        self.mod_path = mod_path

        print(f"Loading: {mod_name} -> {mod_path}")

        if self.mod_path.is_dir():
            # File baised mod
            full_mod_name = self.mod_path.name
            self.file_prefix = ""
            self.mod_type = "file"
            self.all_files = {
                str(p.relative_to(self.mod_path).as_posix())
                for p in self.mod_path.glob("**/*.png")
            }

        else:
            # Zipped baised mod
            full_mod_name = self.mod_path.stem
            self.file_prefix = full_mod_name + "/"
            self.mod_type = "zip"

            zfile = zipfile.ZipFile(str(self.mod_path), "r")

            self.all_files = set()

            for f in zfile.namelist():
                f = str(f)

                if not f.endswith("png"):
                    continue

                assert f.startswith(self.file_prefix), (
                    f"Mod {self.name} has file '{f}' with invalid name"
                    f" (Not starting with '{self.file_prefix}')"
                )

                self.all_files.add(f[len(self.file_prefix) :])

        self.name = full_mod_name.split("_")[0]

    def files(self, filter: Path) -> Iterable[str]:
        for f in self.all_files:
            filter_s = filter.parts

            def filter_check(
                current_path: List[str], current_filter: Tuple[str, ...]
            ) -> bool:
                if len(current_filter) == 0 and len(current_path) == 0:
                    return True

                if len(current_filter) == 0 or len(current_path) == 0:
                    return False

                if current_filter[0] == "**":
                    # recursivly absorb path members
                    # This could get very slow with multiple '**'s
                    for i in range(len(current_path)):
                        if filter_check(current_path[i:], current_filter[1:]):
                            return True
                    return False

                elif fnmatch(current_path[0], current_filter[0]):
                    return filter_check(current_path[1:], current_filter[1:])

                else:
                    return False

            if filter_check(f.split("/"), filter_s):
                yield f

    def lazy_file(self, path: str) -> LazyFile:
        assert path in self.all_files, f"File {path} doesn't exist in mod {self.name}"

        return LazyFile(self.mod_type, self.mod_path, self.file_prefix + path, f"__{self.name}__/{self.mod_path}")


def split_version(version: str) -> Optional[List[int]]:
    try:
        return [int(d) for d in version.split(".")]
    except:
        print(f"Unable to parse version: '{version}'")
        return None


def find_mod(mod_name: str, source_dirs: List[Path]) -> Path:
    for mod_root in source_dirs:
        found_mod_path = None
        found_mod_version = None

        for f in mod_root.iterdir():
            file_name = f.name

            if file_name == mod_name:
                return mod_root / f

            elif file_name == mod_name + ".zip":
                return mod_root / f

            elif "_" in mod_name:
                # Direct match only
                continue

            elif "_" not in file_name:
                continue

            else:
                f_name, f_version = file_name.split("_", 1)

                if "." in f_version:
                    f_version, _ = f_version.split(".", 1)

                if f_name != mod_name:
                    continue

                f_version_split = split_version(f_version)
                if f_version_split is None:
                    continue

                if found_mod_version is None or f_version_split > found_mod_version:
                    found_mod_path = mod_root / f
                    found_mod_version = f_version_split

            if found_mod_path != None:
                return found_mod_path

    raise Exception(f"Failed to find code for mod: {mod_name}")


global_mod_cache: Dict[str, Mod] = {}


def open_mod_read(mod_name: str, source_dirs: List[Path]) -> Mod:
    if mod_name not in global_mod_cache:
        mod_path = find_mod(mod_name, source_dirs)

        global_mod_cache[mod_name] = Mod(mod_name, mod_path)

    return global_mod_cache[mod_name]
