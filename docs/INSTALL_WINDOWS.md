# Instalação do SFI Desktop no Windows

**Versão:** SFI Desktop 0.1.0  
**Plataforma:** Windows 10/11 x64  
**Pacote:** instalador NSIS (.exe), distribuído dentro do artefato ZIP do GitHub Actions  
**Build:** commit a16e1690ed7bb454e449ece000a7846cea06a69c

## 1. Baixar o pacote

1. Abra a [execução Desktop 44642798669 no GitHub Actions](https://github.com/Lvc4br/SFI/actions/runs/44642798669).
2. Localize a seção **Artifacts** no fim da página.
3. Baixe o artefato sfi-desktop-windows (arquivo ZIP).
4. Extraia o ZIP. O pacote contém instaladores separados:
   - nsis/SFI_0.1.0_x64-setup.exe
   - msi/SFI_0.1.0_x64_en-US.msi

O ZIP extraído possui pastas porque reúne mais de um formato de instalador. **Para a primeira homologação, use somente o instalador NSIS.** Não instale NSIS e MSI na mesma rodada.

## 2. Executar a instalação

Pelo Explorador de Arquivos:

1. Abra a pasta extraída.
2. Entre em nsis.
3. Clique duas vezes em SFI_0.1.0_x64-setup.exe.
4. Siga as instruções apresentadas pelo instalador.
5. Ao terminar, procure SFI no Menu Iniciar e abra o aplicativo.

O usuário final não precisa instalar Python, Node.js, pnpm, Rust ou VS Code para executar o aplicativo empacotado. O frontend é incorporado ao desktop e o backend FastAPI é distribuído como sidecar.

### Executar pelo PowerShell

Ajuste o caminho abaixo para a pasta na qual você extraiu o ZIP:

~~~powershell
$Installer = "$env:USERPROFILE\Downloads\sfi-desktop-windows\nsis\SFI_0.1.0_x64-setup.exe"

if (!(Test-Path $Installer)) {
    throw "Instalador não encontrado. Ajuste a variável Installer para o local extraído."
}

Start-Process -FilePath $Installer -Wait
~~~

O comando acima inicia o instalador e aguarda seu encerramento. Ele não baixa o ZIP automaticamente: o download e a extração são etapas anteriores.

## 3. Avisos de segurança

- Este build não está assinado com certificado de publicação. O Windows pode mostrar aviso de editor desconhecido ou SmartScreen.
- Não desative SmartScreen, antivírus ou outras proteções para contornar avisos. Se houver bloqueio, interrompa e registre a mensagem.
- Use somente dados fictícios durante a homologação.
- Não use dados financeiros reais ou documentos fiscais de terceiros.
- Não teste restauração no perfil que contém dados que deseja preservar.

## 4. Onde ficam programa e dados

O instalador é um único arquivo executável, mas a instalação não transforma todo o aplicativo em um único arquivo.

- Os arquivos do programa e o sidecar são instalados pelo NSIS nos diretórios escolhidos pelo instalador.
- Os dados locais ficam separados dos binários do programa.
- O banco SQLite e os segredos ficam no diretório privado do aplicativo no perfil Windows.
- A chave local protegida por DPAPI é esperada em %LOCALAPPDATA%\com.sfi.desktop\secrets\jwt.key.dpapi.
- Não copie a chave DPAPI para outro computador. Para migração, use o mecanismo de backup criptografado.

A sessão fica em memória; após fechar o SFI, é normal precisar autenticar novamente.

## 5. Primeira validação

Depois de instalar, siga o [Checklist de homologação Windows](WINDOWS_RELEASE_TEST_CHECKLIST.md). No mínimo, valide:

1. O aplicativo abre pelo Menu Iniciar sem ferramentas de desenvolvimento instaladas.
2. O sidecar inicia sem erro.
3. É possível criar uma conta fictícia, sair e entrar novamente.
4. A chave DPAPI é criada e não há chave JWT em texto claro.
5. Os dados permanecem após fechar e reabrir o aplicativo.
6. O núcleo financeiro funciona sem conexão com a internet.
7. Backup e restauração são testados somente em perfil descartável.

## 6. Identificação do artefato

- Workflow: [Desktop 44642798669](https://github.com/Lvc4br/SFI/actions/runs/44642798669)
- Artefato: sfi-desktop-windows
- Instalador recomendado: nsis/SFI_0.1.0_x64-setup.exe
- Commit do build: a16e1690ed7bb454e449ece000a7846cea06a69c
- Expiração informada do artefato: 04/12/2026.

Este artefato é para homologação. Não é uma release pública estável e não possui assinatura de publicação nem mecanismo de atualização automática segura.
