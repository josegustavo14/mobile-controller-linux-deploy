# Android Console, Termux e Tailscale

O **Android console** controla diretamente um aparelho já conectado por ADB Wi-Fi. Ele é independente do terminal de **Environments**: o primeiro executa comandos no Android, normalmente como usuário `shell`; o segundo entra no chroot do Linux Deploy e exige root.

## Controles disponíveis sem root

Um celular original, sem Magisk, pode usar os seguintes recursos depois de autorizar a depuração sem fio:

- Home, Voltar, Recentes, bloquear e despertar a tela;
- aumentar, diminuir ou silenciar o volume;
- reproduzir/pausar, avançar e voltar mídia;
- abrir notificações, configurações rápidas e Configurações;
- listar e abrir aplicativos instalados pelo usuário;
- capturar uma imagem atual da tela;
- consultar bateria, temperatura, armazenamento, uptime e endereços de rede;
- executar comandos no terminal **ADB shell**.

O terminal abre em `shell`, que é o usuário de depuração limitado do Android. O botão `root` só é habilitado quando `su -c id -u` funciona no aparelho. Ainda assim, trate o terminal como acesso administrativo: a depuração ADB concede capacidades relevantes e a API deve permanecer protegida pelo `ADMIN_TOKEN`.

## Termux

O botão **Open Termux** apenas abre o aplicativo e não exige root. Os atalhos Battery JSON, Location, Wi-Fi info, Sensors, Clipboard e Torch preenchem comandos da Termux:API.

Para usar esses atalhos, instale Termux e Termux:API da mesma origem — por exemplo, ambos pelo F-Droid ou ambos pelo GitHub — e no Termux execute:

```sh
pkg update
pkg install termux-api
```

Conceda no Android as permissões solicitadas para localização, notificações, câmera ou sensores conforme o comando usado. Para permitir comandos externos, edite `~/.termux/termux.properties`, adicione a linha abaixo e reinicie o Termux:

```properties
allow-external-apps=true
```

Existe uma limitação de segurança importante: o serviço `RUN_COMMAND` do Termux recusa intents enviados pelo usuário ADB `shell`. Ele aceita o próprio usuário do Termux, um aplicativo Android que declare a permissão apropriada ou root. Por isso, neste projeto:

- abrir o Termux funciona em aparelhos sem root;
- executar comandos Android no terminal ADB funciona sem root;
- iniciar uma sessão dentro do Termux pelo painel só é habilitado em aparelhos com root.

Essa separação é intencional; não há uma configuração legítima do ADB que transforme `shell` no usuário privado do Termux em um aparelho comum. Consulte a documentação oficial do [RUN_COMMAND Intent](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent) e da [Termux:API](https://github.com/termux/termux-api).

## Tailscale: o que funciona e o que exige cuidado

O painel web funciona normalmente pelo Tailnet. Instale Tailscale no ZimaOS, acesse `http://NOME-MAGICDNS-DO-ZIMA:8080` ou `http://IP-TAILSCALE-DO-ZIMA:8080` e permita na política ACL somente os usuários/dispositivos administrativos para a porta TCP `8080`.

O ADB possui dois cenários diferentes:

1. **ADB clássico na porta 5555, aparelho com root:** depois de configurar o `adbd` para escutar em TCP, use o IP Tailscale do Android no cadastro. A ACL também precisa permitir que o ZimaOS alcance o aparelho na porta TCP `5555`. Teste a rota diretamente no ZimaOS antes de cadastrar. Esse é o modo mais previsível para uso entre redes.
2. **Depuração sem fio do Android 11+, sem root:** o fluxo oficial pressupõe que computador e telefone estejam na mesma rede Wi-Fi e usa descoberta mDNS, além de portas que podem mudar. O pareamento pode funcionar informando IP e porta manualmente, mas não é seguro prometer reconexão perfeita apenas pelo Tailscale. Faça o primeiro pareamento e o uso normal com ZimaOS e telefone na mesma LAN.

O aplicativo Tailscale para Android não oferece o mesmo CLI disponível no Linux. O painel apenas detecta o endereço `100.64.0.0/10` observado no Android; ele não configura rotas nem altera a política do Tailnet. Veja as orientações oficiais de [ADB sem fio](https://developer.android.com/tools/adb), [serviços no Tailscale](https://tailscale.com/kb/1552/tailscale-services) e [disponibilidade do CLI](https://tailscale.com/kb/1080/cli).

Nunca publique `8080`, `5555` ou portas dinâmicas de depuração no roteador. Use ACL, `ADMIN_TOKEN` longo e uma rede privada.
