# Testing a real Android node over Wi-Fi

The application intentionally supports Wi-Fi only. Do not expose ADB or the control plane to the public internet; use a trusted LAN or a private overlay such as Tailscale.

## Classic ADB over TCP on rooted Android

This method also uses no cable. In a local terminal app on the rooted Android device, enable the TCP listener:

```bash
su -c 'setprop service.adb.tcp.port 5555'
su -c 'stop adbd'
su -c 'start adbd'
```

Then verify connectivity from a trusted administrative machine:

```bash
adb connect DEVICE_IP:5555
adb devices
adb shell su -c 'whoami'
```

The final command should report `root` when Magisk root is available. Register the same host and port in the application. You may need to repeat the local listener commands after restarting Android. Production does not require ADB on ZimaOS: the container has its own binary.

## Android 11+ wireless pairing

Open **Developer options → Wireless debugging → Pair device with pairing code** on Android. In the application, choose **Pair wirelessly** and enter the temporary pairing host, pairing port, and code.

Pairing does not enroll the device. After pairing succeeds, return to the main Wireless debugging screen and note its separate IP address and connection port. Choose **Add device** and register that connection endpoint.

ADB authorization keys are stored under the persistent `/app/data` volume, so rebuilding the application container does not discard the pairing.
