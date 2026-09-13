# Testing a real Android node

The normal mode is ADB over TCP. Do not expose port 5555 to the public internet; use a trusted LAN or a private overlay such as Tailscale.

Before enrolling a node, verify connectivity from a trusted administrative machine:

```bash
adb connect DEVICE_IP:5555
adb devices
adb shell su -c 'whoami'
```

The final command should report `root` when Magisk root is available. Phase 2 will register the same host and port in the application. Production does not require ADB on ZimaOS: the container has its own binary.
