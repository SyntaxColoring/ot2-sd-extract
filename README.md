# Introduction

This is a script to extract troubleshooting information (logs, etc.) from [OT-2](https://opentrons.com/products/robots/ot-2/) SD card images. It operates on *full* SD card images, like the kind created by `dd if=/dev/diskN of=sd.img`.

This is probably only useful on macOS. On Linux, just loop-mount the partitions directly. On Windows, WSL might be easier.

# Disclaimer

Although I am an Opentrons employee, this is not an official Opentrons product, and it's not supported or endorsed by them.

# Setup

1. Install Docker.
2. Clone this repo.
3. `cd` into this repo and run:

   ```
   docker build . -t ot2-sd-extract
   ```

# Usage

1. Create an empty directory somewhere.

2. Place your SD card image inside it. It must be named `sd.img`.

3. Run:

   ```
   docker \
       -v /path-to-your-data:/data \
       --privileged \
       --pull=never \
       ot2-sd-extract \
   ```

   Replace `/path-to-your-data` with the absolute path to the directory that you created, containing `sd.img`.

   `--privileged` lets the container mount filesystems. **Unfortunately, it also gives it privileged access to your machine.** `--pull=never` mitigates that a little bit by making sure you're running the thing that you just built with `docker build`, instead of some other random thing from the Internet.

4. If everything worked, you'll see a bunch of directories like `1/`, `2/`, and so on inside your data directory. Each one corresponds to a partition that the script was able to mount. They will contain any interesting files that the script could find.

   Note that the OT-2 has two root partitions: an active and a standby, for atomic updates. So some of the files will appear twice and have different contents.
