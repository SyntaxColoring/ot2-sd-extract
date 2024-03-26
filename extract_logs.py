import json
import pathlib
import re
import os
import shutil
import subprocess
import sys
import tempfile


DATA_DIR = pathlib.Path("/data")
"""Where we're reading/writing files to communicate with the host."""

IMAGE_FILE = DATA_DIR / "sd.img"
"""This program's input file."""

MOUNT_POINT = pathlib.Path("/mnt")


def get_image_info(image_file):
    result = subprocess.run(
        ["parted", "--machine", "--json", str(image_file), "unit", "b", "print"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)
    # Typical output:
    # {
    #   "disk": {
    #     "path": "/data/sd.img",
    #     "size": "15931539456B",
    #     "model": "",
    #     "transport": "file",
    #     "logical-sector-size": 512,
    #     "physical-sector-size": 512,
    #     "label": "msdos",
    #     "max-partitions": 4,
    #     "partitions": [
    #       {
    #         "number": 1,
    #         "start": "4194304B",
    #         "end": "46137343B",
    #         "size": "41943040B",
    #         "type": "primary",
    #         "type-id": "0x0c",
    #         "filesystem": "fat16",
    #         "flags": [
    #           "boot",
    #           "lba"
    #         ]
    #       }
    #     ]
    #   }
    # }
    # (Except with more partitions.)


def offset_of_partition(partition_info):
    return parse_byte_size(partition_info["start"])


def parse_byte_size(byte_size_str):
    """Parse a string like "1234B" to an int like 1234."""
    match = re.fullmatch("([0-9]+)B", byte_size_str)
    return int(match.group(1))


def mount(file, offset, mount_point):
    subprocess.run(
        ["mount", "-o", "loop", "-o", f"offset={offset}", str(file), str(mount_point)],
        check=True,
        capture_output=True,
    )


def umount(mount_point):
    subprocess.run(["umount", str(mount_point)], check=True)


def extract_stuff(mount_point: pathlib.Path, dest_dir: pathlib.Path) -> None:
    if (mount_point / "log").is_dir():
        # mount_point has /log, but journalctl's --root option expects /var/log.
        with tempfile.TemporaryDirectory() as fake_root:
            fake_var = pathlib.Path(fake_root) / "var"
            fake_var.symlink_to(mount_point)

            with open(dest_dir / "log.txt", "wb") as f:
                subprocess.run(
                    ["journalctl", "--root", fake_root],
                    stdin=subprocess.DEVNULL,
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )

            with open(dest_dir / "log.json", "wb") as f:
                subprocess.run(
                    ["journalctl", "--root", fake_root, "--output=json"],
                    stdin=subprocess.DEVNULL,
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )

    try:
        # /var/machine-info on a fully-mounted OT-2,
        # /machine-info when looking at the partition on its own.
        shutil.copy(mount_point / "machine-info", dest_dir / "machine-info")
    except Exception:
        pass

    try:
        # /var/serial on a fully-mounted OT-2,
        # /serial when looking at the partition on its own.
        shutil.copy(mount_point / "serial", dest_dir / "serial")
    except Exception:
        pass

    try:
        shutil.copy(mount_point / "etc" / "VERSION.json", dest_dir / "VERSION.json")
    except Exception:
        pass


def main():
    if not IMAGE_FILE.exists():
        print(f"Error: Forgot to provide {IMAGE_FILE.name}?", file=sys.stderr)
        return 1

    try:
        image_info = get_image_info(IMAGE_FILE)
    except subprocess.CalledProcessError as e:
        print(f"Error getting partition info from {IMAGE_FILE.name}.", file=sys.stderr)
        print(e.stderr.decode(), file=sys.stderr)
        return 1

    # This lets us use MOUNT_POINT as the root directory for journalctl --root purposes.

    partitions = image_info["disk"]["partitions"]
    mounted_any = False
    for partition in partitions:
        number = partition["number"]
        offset = offset_of_partition(partition)
        try:
            mount(IMAGE_FILE, offset, MOUNT_POINT)
        except subprocess.CalledProcessError as e:
            print(f"Couldn't mount partition {number}. Ignoring it.")
            print(e.stderr.decode())
        else:
            mounted_any = True
            print(f"Successfully mounted partition {number}. Its contents are:")
            for member in MOUNT_POINT.iterdir():
                print(f"\t{member.name}")
            print(f"Extracting stuff from partition {number}...")
            output_dir = DATA_DIR / str(number)
            output_dir.mkdir()
            extract_stuff(MOUNT_POINT, output_dir)
            print(f"Done extracting stuff from partiton {number}.")
            umount(MOUNT_POINT)

    if not mounted_any:
        print(
            "Could not mount any partitions. Do you need to run `docker run` with `--privileged`?"
        )


if __name__ == "__main__":
    main()
