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

### Sensores e Termux:API sem root

Para um celular pessoal sem root, o projeto inclui `termux/asm-agent.py`. Ele deve ser executado **dentro do Termux**, usando o mesmo UID autorizado pelo plug-in Termux:API. O agente é somente leitura: lista sensores e expõe bateria, Wi-Fi, localização, informações de câmera e áudio quando os comandos correspondentes estiverem instalados. Ele não aceita comandos arbitrários.

No Termux do celular:

```sh
pkg update
pkg install python termux-api curl
mkdir -p "$HOME/.local/share/android-server-manager"
curl -fL https://raw.githubusercontent.com/josegustavo14/mobile-controller-linux-deploy/main/termux/asm-agent.py \
  -o "$HOME/.local/share/android-server-manager/asm-agent.py"
chmod 700 "$HOME/.local/share/android-server-manager/asm-agent.py"
```

Gere um segredo com pelo menos 16 caracteres e use exatamente o mesmo valor em `TERMUX_AGENT_TOKEN` no ZimaOS:

```sh
export ASM_AGENT_TOKEN='COLOQUE_UM_TOKEN_LONGO_E_ALEATORIO'
python "$HOME/.local/share/android-server-manager/asm-agent.py"
```

Mantenha essa sessão aberta durante o teste. Para rodar em segundo plano após validar:

```sh
termux-wake-lock
nohup env ASM_AGENT_TOKEN='COLOQUE_O_MESMO_TOKEN' \
  python "$HOME/.local/share/android-server-manager/asm-agent.py" \
  > "$HOME/.local/share/android-server-manager/agent.log" 2>&1 &
```

Cadastre no painel um endereço do telefone que o ZimaOS consiga alcançar — IP da LAN ou IP Tailscale. Abra **Android console → Termux:API sensors → Connect and detect sensors**. O painel consulta `termux-sensor -l` e cria um botão para cada sensor realmente anunciado pelo aparelho. O Android pode pedir permissões na primeira leitura.

Proteja a porta TCP `8765`: deixe-a apenas na LAN/Tailnet e mantenha o token longo. O agente compara o token em tempo constante, não segue redirecionamentos no backend e limita o tamanho das respostas.

## Controle de tela com scrcpy

Abra **Screen control**, selecione um dispositivo ADB já conectado e pressione **Start screen control**. O servidor inicia scrcpy 4.1 numa tela virtual, publica essa tela por noVNC e gera uma senha nova de oito caracteres para a sessão. Digite a senha mostrada pelo painel quando o visualizador solicitar.

Esse fluxo permite imagem, mouse, teclado e toque pelo navegador usando somente a conexão ADB Wi-Fi existente; não precisa de USB, root nem aplicativo extra no Android. Somente uma sessão pode ficar ativa. A porta TCP `6080` deve permanecer restrita à LAN ou Tailnet. Se o painel estiver atrás de HTTPS, publique também `6080` em HTTPS por um proxy reverso; navegadores bloqueiam um iframe HTTP dentro de uma página HTTPS.

## Tailscale: o que funciona e o que exige cuidado

O painel web funciona normalmente pelo Tailnet. Instale Tailscale no ZimaOS, acesse `http://NOME-MAGICDNS-DO-ZIMA:8080` ou `http://IP-TAILSCALE-DO-ZIMA:8080` e permita na política ACL somente os usuários/dispositivos administrativos para as portas TCP `8080` e, se usar scrcpy, `6080`. Para o agente Termux, permita que o ZimaOS alcance o telefone na porta `8765`.

O ADB possui dois cenários diferentes:

1. **ADB clássico na porta 5555, aparelho com root:** depois de configurar o `adbd` para escutar em TCP, use o IP Tailscale do Android no cadastro. A ACL também precisa permitir que o ZimaOS alcance o aparelho na porta TCP `5555`. Teste a rota diretamente no ZimaOS antes de cadastrar. Esse é o modo mais previsível para uso entre redes.
2. **Depuração sem fio do Android 11+, sem root:** o fluxo oficial pressupõe que computador e telefone estejam na mesma rede Wi-Fi e usa descoberta mDNS, além de portas que podem mudar. O pareamento pode funcionar informando IP e porta manualmente, mas não é seguro prometer reconexão perfeita apenas pelo Tailscale. Faça o primeiro pareamento e o uso normal com ZimaOS e telefone na mesma LAN.

O aplicativo Tailscale para Android não oferece o mesmo CLI disponível no Linux. O painel apenas detecta o endereço `100.64.0.0/10` observado no Android; ele não configura rotas nem altera a política do Tailnet. Veja as orientações oficiais de [ADB sem fio](https://developer.android.com/tools/adb), [serviços no Tailscale](https://tailscale.com/kb/1552/tailscale-services) e [disponibilidade do CLI](https://tailscale.com/kb/1080/cli).

Nunca publique `8080`, `5555` ou portas dinâmicas de depuração no roteador. Use ACL, `ADMIN_TOKEN` longo e uma rede privada.
