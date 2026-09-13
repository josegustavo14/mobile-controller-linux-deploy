# Android Server Manager

Android Server Manager is a Docker-contained control plane for rooted Android compute nodes using ADB and Linux Deploy chroots. It is designed for ZimaOS without host-installed Python, Node, or ADB.

## Current status

Phase 2 Wi-Fi device management is complete: in addition to the Phase 1 foundation, the control plane pairs Android 11+ wireless debugging, persists Android endpoints and ADB keys, connects through ADB over TCP, records Android hardware, kernel, and root-capability details, and supports editing, rebooting, disconnecting, and removing devices. USB transport is intentionally out of scope. Linux Deploy management is the next phase.

## Run on macOS

```bash
docker compose up --build
```

`docker compose` works with safe defaults. Copy `.env.example` to `.env` only when you need to override them.

Open `http://localhost:8080`. `http://localhost:8080/health` returns `{"status":"ok"}`.

## Checks

No Android hardware is needed:

```bash
make test
make lint
make build
```

`make build` explicitly produces `linux/amd64`, the ZimaCube target. On Apple Silicon Docker uses its standard amd64 emulation during the build.

The device API is available under `/api/devices`: create, list, edit, or remove endpoints; pair modern wireless debugging with `/pair`; and use `/{id}/connect`, `/{id}/refresh`, `/{id}/reboot`, and `/{id}/disconnect`. The interface exposes the same workflow at the root URL.

For a host Python workflow, install `backend/requirements.txt`, then run `pytest -v backend/tests` from the repository root.

## ZimaOS deployment

Build or import this image as a custom Docker application in ZimaOS and use the Compose file. Mount persistent storage at `/app/data` and publish only port `8080` on a trusted network. The image contains FastAPI, the compiled frontend and ADB; ZimaOS itself is not modified. Use the `linux/amd64` image on ZimaCube.

Keep both the interface and ADB TCP off the public internet. Authentication arrives before broader device-control endpoints.

## Real-device validation

See [the real device guide](docs/real-device-testing.md).
