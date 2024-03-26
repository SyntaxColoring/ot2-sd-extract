# Ubuntu is probably overkill, but it has journalctl available to install.
# Ubuntu 23.10 is not LTS, but it has a newer version of `parted` that has --json.
FROM ubuntu:23.10

RUN apt-get update && apt-get install -y \
    systemd \
    parted

COPY --chmod=744 extract_logs.py .

CMD python3 extract_logs.py
