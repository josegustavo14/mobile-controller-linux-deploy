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

### Pareamento por QR Code

No painel, escolha **Devices → Pair wirelessly → QR code** e gere uma sessão. No Android, abra **Opções do desenvolvedor → Depuração sem fio → Parear dispositivo com QR Code**, escaneie o código exibido e, quando o scanner fechar, clique em **Complete pairing**.

O QR é temporário: o backend mantém o segredo apenas em memória por dois minutos. Ele não é salvo no banco nem escrito nos logs. Se a descoberta ainda não tiver chegado ao ZimaOS, aguarde alguns segundos e tente concluir novamente; gere outro QR somente depois que a sessão expirar.

Esse método depende de multicast DNS. O telefone e o ZimaOS precisam estar na mesma LAN, sem isolamento de clientes Wi-Fi. O template do ZimaOS usa rede `host` e o backend força o mDNS embarcado do ADB para que o contêiner receba o anúncio `_adb-tls-pairing._tcp`. Para instalações Docker personalizadas, use rede `host` em um servidor Linux ou mantenha o método de seis dígitos.

## Testar um celular pessoal sem root

Depois de autorizar o ADB por Wi-Fi e conectar o aparelho, abra **Android console**. O painel deve indicar **ADB shell available** e **Non-root device**. Nesse modo funcionam o terminal ADB, Home, Voltar, Recentes, bloqueio/despertar, volume, mídia, central de notificações, configurações rápidas, abertura de aplicativos e captura de tela.

Use primeiro um comando somente de leitura:

```sh
getprop ro.build.version.release
```

Depois teste:

```sh
pm list packages -3
df -h /sdcard
dumpsys battery
```

O seletor `root` permanece desativado. Nenhuma dessas verificações instala arquivos, altera o sistema ou depende de Linux Deploy.

Para controles do Termux e acesso remoto por Tailscale, consulte o [guia do Android Console](android-console.md).
