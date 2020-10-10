from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import IO, Iterable, List, Optional, Tuple
import zipfile


@dataclass(eq=True, frozen=True)
class LazyFile:
    mod_type: str
    mod_path: Path
    file_path: str

    def open(self) -> IO[bytes]:
        if self.mod_type == "file":
            return (self.mod_path / self.file_path).open("rb")

        elif self.mod_type == "zip":
            with zipfile.ZipFile(str(self.mod_path), "r") as zfile:
                return zfile.open(self.file_path, "r")

        else:
            raise Exception(f"Unknown mod_type: {self.mod_type}")


class Mod:
    # For typing

    name: str

    def files(self, filter: Path) -> Iterable[str]:
        pass

    def lazy_file(self, path: str) -> LazyFile:
        pass


class FileMod(Mod):
    mod_path: Path
    name: str

    def __init__(self, mod_path: Path, full_mod_name: str):
        self.mod_path = mod_path
        self.name = full_mod_name.split("_")[0]

    def files(self, filter: Path) -> Iterable[str]:
        return [
            f.relative_to(self.mod_path).as_posix()
            for f in self.mod_path.glob(str(filter))
        ]

    def lazy_file(self, path: str) -> LazyFile:
        return LazyFile("file", self.mod_path, path)


class ZipMod(Mod):
    mod_path: Path
    zfile: zipfile.ZipFile
    name: str

    def __init__(self, mod_path: Path, full_mod_name: str):
        self.zfile = zipfile.ZipFile(str(mod_path), "r")
        self.mod_path = mod_path
        self.full_mod_name = full_mod_name
        self.name = full_mod_name.split("_")[0]

    def files(self, filter: Path) -> Iterable[str]:
        for f in self.zfile.namelist():
            path_s = f.split("/")
            filter_s = filter.parts

            assert (
                path_s[0].split("_")[0] == self.name
            ), f"Mod {self.name} has file '{f}' with invalid name"

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

            if filter_check(path_s[1:], filter_s):
                yield "/".join(path_s[1:])

    def lazy_file(self, path: str) -> LazyFile:
        return LazyFile("zip", self.mod_path, self.full_mod_name + "/" + path)


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


def open_mod_read(mod_name: str, source_dirs: List[Path]) -> Mod:
    mod_path = find_mod(mod_name, source_dirs)

    if mod_path.is_dir():
        return FileMod(mod_path, mod_path.name)
    else:
        return ZipMod(mod_path, mod_path.stem)
