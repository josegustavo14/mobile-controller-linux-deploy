# Implantação no ZimaOS

Este guia instala o Android Server Manager a partir do código-fonte. O ZimaOS não precisa de Python, Node ou ADB instalados no host; tudo é construído dentro do Docker.

## Importação automática pela interface

O arquivo [`docker-compose.zimaos.yml`](../docker-compose.zimaos.yml) foi preparado para a tela **Importar → Docker Compose** do ZimaOS. Ele baixa a imagem pronta de `ghcr.io/josegustavo14/mobile-controller-linux-deploy:latest` e cria automaticamente o volume persistente `android-server-manager-data`.

O mesmo arquivo inclui os metadados `x-casaos` da WebUI e o ícone do aplicativo. Se precisar informar o ícone manualmente no ZimaOS, use esta URL:

```text
https://raw.githubusercontent.com/josegustavo14/mobile-controller-linux-deploy/main/assets/android-server-manager-icon.png
```

Antes de colar ou enviar o arquivo, substitua os três marcadores por valores diferentes produzidos por `openssl rand -hex 32`: `ADMIN_TOKEN`, `TERMUX_AGENT_TOKEN` e `UPDATER_TOKEN`. O token do Termux deve ser repetido no agente do celular; o token de atualização deve ser repetido no serviço Watchtower.

Depois clique em **Submeter** e aguarde o download. Esta modalidade não precisa criar pastas manualmente: o volume nomeado preserva o banco SQLite, logs e chaves de pareamento ADB entre atualizações.

O template usa `network_mode: host` para permitir a descoberta mDNS exigida pelo pareamento ADB via QR Code. A WebUI continua em `http://IP_DO_ZIMAOS:8080` e o visualizador scrcpy em `http://IP_DO_ZIMAOS:6080`. O servidor ADB interno usa a porta local `5038` para evitar conflito com uma eventual instalação de ADB no host; ela não deve ser exposta no roteador.

O segundo serviço do template é o atualizador local. Algumas versões da tela de importação do ZimaOS avisam que importam somente o primeiro contêiner. Nesse caso o aplicativo funciona, mas mostra **Updater not configured** e desabilita o botão. Para habilitá-lo, use uma vez a alternativa por SSH abaixo e execute o arquivo completo com `docker compose`; as atualizações seguintes serão feitas pelo botão, sem nova instalação.

As seções abaixo descrevem a alternativa por SSH, útil para repositório privado ou para quem prefere os dados em uma pasta visível dentro de `/DATA/AppData`.

## 1. Preparar o acesso

No painel do ZimaOS, abra **Settings → Developer Mode** e ative **SSH Access** ou o terminal web. Reserve um endereço IP estável para o ZimaOS no DHCP do roteador.

Crie a pasta persistente:

```bash
sudo mkdir -p /DATA/AppData/android-server-manager/data
sudo chown -R "$USER":"$(id -gn)" /DATA/AppData/android-server-manager
```

## 2. Enviar o projeto

No computador que contém o repositório:

```bash
rsync -av \
  --exclude .git \
  --exclude .env \
  --exclude frontend/node_modules \
  --exclude frontend/dist \
  --exclude data \
  ./ USUARIO@IP_DO_ZIMAOS:/DATA/AppData/android-server-manager/
```

Também é possível clonar um repositório Git remoto diretamente nessa pasta.

## 3. Configurar

No ZimaOS:

```bash
cd /DATA/AppData/android-server-manager
cp .env.example .env
nano .env
```

Use uma configuração equivalente a esta:

```dotenv
APP_HOST=0.0.0.0
APP_PORT=8080
DATABASE_URL=sqlite:///./data/app.db
ADB_PATH=/opt/android-platform-tools/adb
ADB_SERVER_PORT=5037
ADB_TIMEOUT=20
SCRCPY_PATH=/opt/scrcpy/scrcpy
SCRCPY_VIEWER_PORT=6080
TERMUX_AGENT_PORT=8765
TERMUX_AGENT_TOKEN=COLOQUE_AQUI_OUTRO_TOKEN_LONGO_E_ALEATORIO
UPDATE_MANIFEST_URL=https://raw.githubusercontent.com/josegustavo14/mobile-controller-linux-deploy/main/version.json
UPDATER_URL=
UPDATER_TOKEN=
UPDATER_IMAGE=ghcr.io/josegustavo14/mobile-controller-linux-deploy:latest
ADMIN_TOKEN=COLOQUE_AQUI_UM_TOKEN_LONGO_E_ALEATORIO
LINUX_DEPLOY_CLI=/data/user/0/ru.meefik.linuxdeploy/files/bin/linuxdeploy
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://IP_DO_ZIMAOS:8080
```

Gere o token em uma máquina administrativa com `openssl rand -hex 32`. Não reutilize uma senha pessoal. Se acessar por mais de um endereço, separe as origens por vírgula.

O processo da aplicação usa UID/GID `999`. Garanta acesso ao volume:

```bash
sudo chown -R 999:999 /DATA/AppData/android-server-manager/data
sudo chmod 750 /DATA/AppData/android-server-manager/data
```

## 4. Iniciar

```bash
cd /DATA/AppData/android-server-manager
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100 android-server-manager
```

Se o ZimaOS informar que `/root/.docker` é somente leitura:

```bash
sudo -i
mkdir -p /var/lib/docker/.docker
export DOCKER_CONFIG=/var/lib/docker/.docker
cd /DATA/AppData/android-server-manager
docker compose up -d --build
```

Valide a saúde:

```bash
curl http://127.0.0.1:8080/health
```

A resposta esperada é `{"status":"ok"}`. Abra `http://IP_DO_ZIMAOS:8080` e informe o `ADMIN_TOKEN`.

## 5. Configurar o Android e Linux Deploy

Siga o [guia do Android real](real-device-testing.md) para ativar ou parear o ADB por Wi-Fi. Depois:

1. Cadastre e conecte o Android na tela **Devices**.
2. Confirme que a tela mostra **Root available**.
3. No Android, instale o Linux Deploy, conceda root e crie o perfil desejado.
4. Em Linux Deploy, use **Settings → Update ENV** se o executável CLI ainda não existir.
5. No painel, abra **Environments**, informe o mesmo nome de perfil e registre-o.
6. Use **Services** e **Terminal** somente depois que o ambiente estiver em execução.

Se o Linux Deploy estiver instalado em outro caminho, ajuste `LINUX_DEPLOY_CLI` no `.env` e recrie o contêiner.

## Habilitar atualização pelo painel

O arquivo `docker-compose.zimaos.yml` completo já inclui o serviço auxiliar. Se o importador gráfico tiver ignorado o segundo contêiner, clone ou atualize o repositório por SSH e edite os três tokens dentro desse arquivo. Valide antes de interromper o aplicativo:

```bash
cd /DATA/AppData/android-server-manager
sudo docker compose -f docker-compose.zimaos.yml config --quiet
```

Se a versão anterior foi criada pelo importador gráfico, confirme primeiro que ela usa o volume nomeado esperado:

```bash
sudo docker inspect android-server-manager \
  --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{println}}{{end}}'
```

Deve aparecer `android-server-manager-data -> /app/data`. Depois faça a migração única: remova **somente o contêiner**, nunca o volume, e suba o Compose completo.

```bash
sudo docker stop android-server-manager
sudo docker rm android-server-manager
sudo docker compose -f docker-compose.zimaos.yml up -d
```

Não use `docker compose down -v` e não marque a opção de apagar dados no ZimaOS. O volume nomeado existente será conectado ao novo contêiner.

O painel consulta `version.json` no GitHub. Quando a versão publicada for maior que a instalada, aparece uma faixa **Version … is available**. Clique em **Update now**, confirme e aguarde: o Watchtower baixa somente a imagem `ghcr.io/josegustavo14/mobile-controller-linux-deploy:latest`, recria o contêiner com a mesma configuração e o navegador reconecta quando a versão nova responde.

O banco, as chaves ADB e os logs ficam no volume `android-server-manager-data`, portanto não são substituídos. O atualizador monta `/var/run/docker.sock`, mas sua API usa token, fica vinculada apenas a `127.0.0.1:8090` e monitora somente o contêiner `android-server-manager`.

Confirme que o serviço auxiliar está pronto:

```bash
sudo docker ps --filter name=android-server-manager-updater
sudo docker logs --tail=100 android-server-manager-updater
```

## Atualização manual da instalação por código-fonte

Envie a nova versão dos arquivos e execute:

```bash
cd /DATA/AppData/android-server-manager
sudo docker compose up -d --build
```

As chaves ADB, cadastros, ambientes e logs permanecem em `data/`.

## Backup e restauração

Para obter uma cópia consistente:

```bash
sudo docker compose stop android-server-manager
sudo mkdir -p /DATA/AppData/android-server-manager-backups
sudo cp data/app.db /DATA/AppData/android-server-manager-backups/app.db
sudo cp -a data/.android /DATA/AppData/android-server-manager-backups/android-keys
sudo docker compose start android-server-manager
```

Guarde as cópias fora do disco do sistema. Para restaurar, pare o serviço, recoloque o banco e a pasta de chaves dentro de `data/`, restaure o proprietário `999:999` e inicie novamente.

## Rede e segurança

- Não encaminhe no roteador as portas `8080`, `6080`, `8765`, `5555` ou portas dinâmicas do ADB.
- Use LAN confiável ou uma VPN privada, sem isolamento entre ZimaOS e Android.
- O ADB server usa `5037` apenas dentro do contêiner; essa porta não é publicada.
- O terminal executa comandos no chroot com o usuário selecionado. Proteja o `ADMIN_TOKEN` e bloqueie a sessão ao terminar.
- O contêiner principal roda sem root, sem capabilities, com `no-new-privileges` e filesystem raiz somente leitura. Apenas o Watchtower recebe o socket Docker necessário para recriar o aplicativo durante uma atualização.
