# Dune: Imperium — Tradução pt-BR (Steam)

Tradução não oficial para português do Brasil do **Dune: Imperium** (Dire Wolf Digital) na Steam. Adiciona **Português (Brasil)** à lista de idiomas em *Configurações → Geral → Idiomas*, logo depois de English.

> Projeto de fãs, sem ligação com a Dire Wolf Digital, Asmodee, Legendary ou os detentores de *Duna*. Nenhum arquivo do jogo é distribuído aqui, só o texto traduzido e um instalador que o aplica na sua cópia.

- [Para humanos](#para-humanos) — instalar, desinstalar, limitações, contribuir
- [Para IAs e agentes](#para-ias-e-agentes) — arquitetura, como o menu funciona, o que já foi descartado, como depurar

---

# Para humanos

## Instalar (Windows)

1. Abra o jogo **uma vez com internet** até o menu principal e feche. É nesse momento que ele baixa os textos que o instalador modifica.
2. Instale o [Python 3.9+](https://www.python.org/downloads/) (marque *Add Python to PATH*).
3. Baixe este repositório (*Code → Download ZIP*), extraia e dê duplo clique em `install.bat`.
4. Abra o jogo e escolha **Português (Brasil)** em *Configurações → Geral → Idiomas*.

## Desinstalar

`restaurar.bat`. Ele devolve a `steam_api64.dll` original, restaura o cache de textos a partir do backup (`__data.original`) e remove os arquivos do loader. *Verificar a integridade dos arquivos* na Steam também restaura a DLL original (aí rode o instalador de novo para reativar).

## O que o instalador altera

| Arquivo | O que muda | Backup |
|---|---|---|
| `…\LocalLow\Unity\Dire Wolf Digital_Dune_ Imperium\localization\…\__data` | acrescenta o texto `pt_BR` (nenhum idioma é alterado) | `__data.original` |
| `…\Dune Imperium\DuneImperium_Data\Plugins\x86_64\steam_api64.dll` | vira o proxy do mod loader | original em `…\Dune Imperium\steam_api64_real.dll` |
| `…\Dune Imperium\dune_loader.ini` | configuração do loader | (arquivo novo) |

O loader grava logs de diagnóstico (`dune_loader.log`, `dune_hook.txt`) na pasta do jogo. O `.exe` e a `GameAssembly.dll` não são alterados.

## Quando o jogo atualizar

Atualizações podem trocar o cache de textos ou a `steam_api64.dll`. É só **rodar o instalador de novo**. Textos novos que ainda não foram traduzidos aparecem em inglês; para listá-los:

```
python tools/missing_keys.py
```

Como o loader depende de nomes internos de classes do jogo, uma atualização grande pode quebrá-lo. Nesse caso o jogo continua funcionando, só sem o item novo; o `restaurar.bat` desfaz tudo.

## Modos alternativos (sem mod loader)

- `python patcher/dune_ptbr.py --substituir-ingles`: não instala loader. O texto do idioma "English" passa a ser português (o menu continua mostrando "English").
- `python patcher/dune_ptbr.py --usar-vaga` (experimental): troca o texto de outro idioma e altera o bundle de idiomas da Steam (com ajuste de CRC). O rótulo no menu continua o do idioma original.

## Limitações conhecidas

- É uma modificação do lado do cliente. **Substituir a `steam_api64.dll` pode ser visto como adulteração por ferramentas de verificação.** Use por sua conta e risco, principalmente no jogo online.
- Textos desenhados nas imagens das cartas e alguns textos embutidos nos prefabs do jogo continuam em inglês.
- O contrato de licença (EULA) foi mantido em inglês de propósito.
- A tradução foi feita com apoio de IA e **sem revisão por falante nativo**. Os termos de regras seguem o manual de *Uprising* da Galápagos ([glossário](translation/GLOSSARIO.md)), mas nomes de cartas e termos de *Ascensão de Ix* e *Imortalidade* não têm referência oficial aqui e podem diferir da edição física. Correções são bem-vindas.
- Só testado no Windows com a versão 4.1.2.1808 do jogo.

## Contribuir

Edite `translation/pt_BR.txt` (formato `chave=valor`, uma por linha) e abra um Pull Request. Rode `python tools/validate_translation.py` antes. Regras:

- Mantenha **exatamente** as tags e marcadores: `<b>`, `<sprite name="...">`, `<br>`, `[name]`, `[card]`, `{0}`, `\n`.
- Siga o [glossário](translation/GLOSSARIO.md).
- Tratamento por "você".

## Licença e direitos

- **Código** (`patcher/`, `loader/`, `tools/`, scripts `.bat`): licença MIT (arquivo `LICENSE`).
- **Texto traduzido** (`translation/pt_BR.txt`): obra derivada do texto de *Dune: Imperium*. **Não é licenciada para reutilização**; é fornecida apenas para uso pessoal, com os direitos do texto original preservados para seus detentores (Dire Wolf Digital, Legendary, Herbert Properties e demais).
- Se você é detentor desses direitos e quer a remoção do conteúdo, abra uma issue ou contate o mantenedor, e o texto será retirado.
- O repositório não contém arquivos, imagens, áudios ou código do jogo.

---

# Para IAs e agentes

Contexto técnico para quem for manter ou estender este projeto. Tudo abaixo foi verificado empiricamente neste jogo (Unity 6000.3.17f1, IL2CPP, Windows x64, cliente 4.1.2.1808), exceto onde marcado como *hipótese*.

## Mapa do repositório

| Caminho | Função |
|---|---|
| `translation/pt_BR.txt` | Tradução (`chave=valor`). Fonte da verdade. Só contém chaves traduzidas; as demais caem no inglês. |
| `translation/GLOSSARIO.md` | Termos. Segue o manual de *Uprising* da Galápagos (fonte oficial em pt-BR). |
| `patcher/dune_ptbr.py` | Instalador/restaurador (CLI). Mexe no cache de textos, instala o loader e grava `dune_loader.ini`. |
| `patcher/crcfix.py` | Parser/gravador de bundles UnityFS e forja de CRC32 (só usado pelo modo `--usar-vaga`). |
| `loader/src/loader.c` | O mod loader (C). Proxy da `steam_api64.dll` + hooks IL2CPP. |
| `loader/build_loader.py` | Compila o loader com Zig (`pip install ziglang`), gerando um `.def` com 1.088 forwarders a partir da DLL do usuário. |
| `loader/make_proxy.py` | Fallback sem compilador: monta um PE64 à mão que só devolve a lista de idiomas da Steam (não acrescenta nada ao menu). |
| `tools/missing_keys.py`, `tools/validate_translation.py` | Chaves sem tradução; validação de tags contra o inglês. |

## Como o menu de idiomas funciona (o que realmente importa)

- O dropdown é `boardgames.menus.behaviours.LocaleDropdown` (assembly `dbg-client.dll`). Seu `OnEnable` monta as opções de um `TMP_Dropdown` a partir de **`boardgames.utils.DBGConstants.SupportedLocales`** (propriedade estática, assembly `boardgames.dll`), uma lista dos valores da enum `localization.Locale` (assembly `core-localization.dll`). `pt_BR` = 3, `cs_CZ` = 26, `en_US` = 0.
- O nome exibido de cada item vem do dicionário estático `localization.TextLocalization.localeNames` (`Dictionary<Locale,string>`), via `GetNameForLocale`. Para `pt_BR` o jogo traz "Brasileiro Português"; o loader troca por "Português (Brasil)".
- Ao selecionar, o dropdown dispara `LocaleDropdown.Event_SetLocale(int)` e `LocaleSetting.Event_ChangeLocale(int)`, que validam o índice contra a lista de suportados (erro "Attempting to select a locale that is not supported" se não estiver).
- O texto vem do pacote baixado (AssetBundle em `AppData\LocalLow\Unity\Dire Wolf Digital_Dune_ Imperium\localization\<hash>\__data`), um `TextAsset` por idioma com nome `xx_XX`, formato `chave=valor`. Para o locale `pt_BR` o jogo procura o `TextAsset` `pt_BR`.
- O jogo também precisa de um `UnityEngine.Localization.Locale` com código `pt-BR` em `LocalizationSettings.AvailableLocales`; o loader cria com `Locale.CreateLocale(string)` e adiciona com `AddLocale`.

## Como o loader funciona

1. `steam_api64.dll` do jogo é renomeada para `steam_api64_real.dll` **na raiz do jogo** (ao lado do `.exe`) e o proxy compilado ocupa o lugar original em `DuneImperium_Data\Plugins\x86_64\`. A DLL real precisa estar na raiz porque o Windows resolve os *forwarders* a partir da pasta do executável, não da pasta do proxy (se estiver no mesmo diretório do proxy, o jogo falha com `EntryPointNotFoundException`).
2. `DllMain` cria uma thread que espera `GameAssembly.dll` e usa a API C exportada do IL2CPP (`il2cpp_class_from_name`, `il2cpp_class_get_method_from_name`, `il2cpp_runtime_invoke`, ...) para achar classes e métodos em tempo de execução.
3. **Hook de métodos Unity:** troca-se `MethodInfo.methodPointer` (offset 0, e `virtualMethodPointer` no offset 8 se igual) de `LocaleDropdown.OnEnable`/`Start`/`Event_SetLocale` e `LocaleSetting.Event_ChangeLocale` por funções nossas. Funciona porque a Unity invoca mensagens (`Start`, `OnEnable`, ...) lendo o `MethodInfo` no momento da chamada, e roda **na thread principal**, onde as APIs da engine são permitidas. Não funciona para chamadas diretas entre métodos C# (IL2CPP gera chamadas estáticas) nem para entradas de vtable já montadas.
4. Dentro do hook de `OnEnable`, antes do original: cria o `Locale` pt-BR, renomeia o rótulo, insere `pt_BR` (3) na posição 1 de `SupportedLocales`. O `OnEnable` original então já monta o dropdown com o item.
5. Configuração: `dune_loader.ini` na raiz do jogo (`hook=1`; modos de diagnóstico `probe=1` grava `dune_probe.txt` com todas as classes/métodos/campos dos assemblies do jogo, `diag=1` grava `dune_diag.txt`). Logs: `dune_loader.log`, `dune_hook.txt`.

Para descobrir nomes após uma atualização do jogo, rode com `probe=1` e procure em `dune_probe.txt` (formato `CLASS <assembly> | <ns>.<nome>` seguido de `M método/nº_parâmetros` e `F campo`).

## Becos sem saída já testados (não repita)

- **Nenhum arquivo de dados define a lista de idiomas.** Mudar código/nome/`SortOrder` dos `Locale` do bundle `localization-locales_assets_all.bundle`, e as chaves do `catalog.bin`, não altera o menu. A lista é código (`DBGConstants.SupportedLocales`).
- **A lista de idiomas da Steam (`SteamAPI_ISteamApps_GetAvailableGameLanguages`) não alimenta o menu**, embora coincida com os 12 idiomas atuais. O proxy chegou a devolver `brazilian` sem efeito.
- **Adicionar itens por troca de arquivos** é inviável; só código em execução (o loader) consegue.
- **Addressables confere o CRC32 dos dados descomprimidos de cada bundle** contra o `catalog.bin` e recusa o arquivo (log: `Invalid path in AssetBundleProvider`, loop de erro na tela de carregamento). `patcher/crcfix.py` contorna reservando 4 bytes inertes (`m_CustomFormatCultureCode`) e forjando o CRC. O pacote de textos em cache **não** tem CRC no catálogo (por isso aceita o `TextAsset` novo sem forja). Regrave bundles com `packer="original"` do UnityPy para preservar os flags (`0x243` no Unity 6; o `lz4` padrão quebra).
- **BepInEx 6 (IL2CPP, build #791)** impediu o jogo de abrir; foi descartado e removido.
- `global-metadata.dat` é versão 39 do formato IL2CPP (os dumpers comuns podem não suportar); por isso a descoberta é feita em tempo de execução pelo próprio loader.

## Armadilhas de ambiente

- Não há compilador C na máquina; o loader usa o Zig do PyPI (`python -m ziglang cc -target x86_64-windows-gnu`).
- Nas ferramentas de shell deste ambiente, sequências como `\n` e `\0` dentro de strings Python em heredocs podem ser convertidas em caracteres reais e quebrar o código. Prefira `chr(10)`, `chr(92)`, `bytes([0])` ou grave o arquivo com a ferramenta de escrita.
- Feche o jogo antes de reinstalar (a DLL carregada fica travada). Teste sempre lendo `dune_hook.txt` e `Player.log` (`%USERPROFILE%\AppData\LocalLow\Dire Wolf Digital\Dune Imperium\Player.log`).
- **Não use automação de mouse na tela do usuário** para navegar no jogo: cliques cegos já fecharam o jogo e abriram telas erradas. Peça para o usuário abrir *Configurações → Idiomas* e relatar.
- Para validar a tradução: `python tools/validate_translation.py` (precisa do cache do jogo). Ao traduzir, preserve tags e marcadores idênticos ao original e siga `translation/GLOSSARIO.md`.

## Ideias não implementadas

- Ler a lista da Steam em tempo de execução em vez de fixa (`loader.c` hoje devolve uma string estática).
- Ajustar a posição do item (`PT_BR_INDEX` em `loader.c`) ou torná-la configurável pelo `.ini`.
- Fontes: o jogo usa variantes de fonte por locale (`cs-CZ`, `pl-PL` compartilham uma fonte com diacríticos); `pt-BR` usa a padrão, que gera `ã`, `ç` etc. dinamicamente (modo dinâmico do TMP).
