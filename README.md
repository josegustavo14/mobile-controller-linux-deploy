# Android Server Manager

Android Server Manager is a self-contained control plane for Android devices and rooted compute nodes. It connects over ADB Wi-Fi, offers direct non-root Android controls, manages existing Linux Deploy profiles, operates services inside their chroots, exposes authenticated command terminals, and records an audit trail.

## Features

- Classic ADB TCP and Android 11+ wireless pairing by six-digit code or QR code; USB is intentionally unsupported.
- Persistent device registry with connect, inspect, edit, reboot, disconnect, and remove actions.
- Android manufacturer, model, release, ABI, kernel, and root-capability inspection.
- Android Console with live battery/network telemetry, remote keys, media controls, app launcher, screenshots, and a non-root ADB shell.
- Interactive scrcpy screen control in the browser through a private noVNC session; no USB or root required.
- Read-only Termux:API agent for personal phones, with buttons generated from the sensors and APIs detected on that device; no root required.
- Optional direct Termux command bridge on rooted nodes; opening Termux itself works without root.
- Existing Linux Deploy profile registration, status refresh, start, stop, and removal from the registry.
- SysV service discovery and start, stop, or restart actions inside a chroot.
- Authenticated command execution inside a selected Linux Deploy environment.
- Fleet dashboard, persistent audit log, and read-only runtime diagnostics.
- GitHub version notification and an authenticated in-app update button for ZimaOS deployments.
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

The frontend and API share port `8080`; the optional scrcpy viewer uses port `6080`. All control APIs require `Authorization: Bearer <ADMIN_TOKEN>`. ADB keys, the SQLite database, and audit records live under `/app/data`, which maps to the local `./data` directory.

The application does not install a Linux distribution. Create and configure a profile in Linux Deploy on Android first, then register the same profile name in the control plane. The default CLI path can be changed with `LINUX_DEPLOY_CLI`.

API documentation is available at `/api/docs`. Main API groups include `/api/devices`, `/api/environments`, `/api/scrcpy`, `/api/termux-agent`, `/api/update`, and `/api/system`.

## ZimaOS and Android setup

- [Application icon](assets/android-server-manager-icon.png) — public URL ready for the ZimaOS dashboard.
- [One-click ZimaOS Compose template](docker-compose.zimaos.yml)
- [ZimaOS deployment guide](docs/zimaos-deployment.md)
- [Real Android Wi-Fi guide](docs/real-device-testing.md)
- [Android Console, Termux, and Tailscale guide](docs/android-console.md)

Keep the UI and ADB endpoints on a trusted LAN or private overlay. Never forward ports `8080`, `5555`, or a wireless-debugging connection port directly to the public internet.
