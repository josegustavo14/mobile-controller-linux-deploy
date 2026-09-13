# Android Server Manager

Android Server Manager is a self-contained control plane for rooted Android compute nodes. It connects over ADB Wi-Fi, manages existing Linux Deploy profiles, operates services inside their chroots, exposes an authenticated command terminal, and records an audit trail.

## Features

- Classic ADB TCP and Android 11+ wireless pairing; USB is intentionally unsupported.
- Persistent device registry with connect, inspect, edit, reboot, disconnect, and remove actions.
- Android manufacturer, model, release, ABI, kernel, and root-capability inspection.
- Existing Linux Deploy profile registration, status refresh, start, stop, and removal from the registry.
- SysV service discovery and start, stop, or restart actions inside a chroot.
- Authenticated command execution inside a selected Linux Deploy environment.
- Fleet dashboard, persistent audit log, and read-only runtime diagnostics.
- A single non-root `linux/amd64` container with bundled Android Platform Tools and a read-only root filesystem.

## Run locally

Create the runtime configuration and set a long random administrator token:

```bash
cp .env.example .env
```

Then start the application:

```bash
docker compose up --build
```

Open `http://localhost:8080` and enter the `ADMIN_TOKEN` value. The health endpoint remains public at `http://localhost:8080/health`.

## Verification

No Android hardware is required for the automated suite:

```bash
make test
make lint
make build
```

The tests use an in-memory ADB double. `make build` produces the `linux/amd64` ZimaCube target; Apple Silicon uses Docker's normal amd64 emulation.

## Runtime model

The frontend and API share port `8080`. All control APIs require `Authorization: Bearer <ADMIN_TOKEN>`. ADB keys, the SQLite database, and audit records live under `/app/data`, which maps to the local `./data` directory.

The application does not install a Linux distribution. Create and configure a profile in Linux Deploy on Android first, then register the same profile name in the control plane. The default CLI path can be changed with `LINUX_DEPLOY_CLI`.

API documentation is available at `/api/docs`. Main API groups are `/api/devices`, `/api/environments`, and `/api/system`.

## ZimaOS and Android setup

- [One-click ZimaOS Compose template](docker-compose.zimaos.yml)
- [ZimaOS deployment guide](docs/zimaos-deployment.md)
- [Real Android Wi-Fi guide](docs/real-device-testing.md)

Keep the UI and ADB endpoints on a trusted LAN or private overlay. Never forward ports `8080`, `5555`, or a wireless-debugging connection port directly to the public internet.
