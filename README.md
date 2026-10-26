# Dune: Imperium — Tradução pt-BR (Steam)

Tradução não oficial para português do Brasil do **Dune: Imperium** (Dire Wolf Digital) na Steam. Adiciona **Português (Brasil)** à lista de idiomas em *Configurações → Idiomas*.

> Projeto de fãs, sem ligação com a Dire Wolf Digital, Asmodee, Legendary ou os detentores de *Duna*. Nenhum arquivo do jogo é distribuído aqui — só o texto traduzido e um instalador que o aplica na sua cópia.

## Instalar (Windows)

**Com Python 3.9+:** baixe o repositório (*Code → Download ZIP*), extraia e dê duplo clique em `install.bat`.

Antes: abra o jogo **uma vez com internet** até o menu principal e feche. É nesse momento que ele baixa os textos que o instalador modifica.

Depois, no jogo: **Configurações → Idiomas → Português (Brasil)**.

## Desinstalar

`restaurar.bat` (ou *3) Restaurar* no `.exe`). Também funciona *Verificar integridade dos arquivos* na Steam, mas só restaura o menu; rode o restaurador para limpar tudo.

## O que o instalador mexe

| Arquivo | O que muda | Backup |
|---|---|---|
| `%USERPROFILE%\AppData\LocalLow\Unity\Dire Wolf Digital_Dune_ Imperium\localization\…\__data` | recebe os textos `pt_BR` | `__data.original` |
| `…\Dune Imperium\DuneImperium_Data\StreamingAssets\aa\StandaloneWindows64\localization-locales_assets_all.bundle` | um dos 12 idiomas (por padrão **tcheco**) passa a se chamar "Português (Brasil)" | `….bundle.original` |

O jogo só tem 12 vagas de idioma e não dá para criar uma 13ª sem mexer no código, então o português ocupa a vaga do tcheco. Prefere outra? `python patcher/dune_ptbr.py --slot ko-KR`.

**Não quer mexer na pasta da Steam?** Use `--substituir-ingles` (ou a opção 2 do `.exe`): o idioma "English" do jogo passa a ser português e só o cache em `AppData` é alterado.

## Quando o jogo atualizar

Atualizações podem restaurar o bundle de idiomas ou trocar o cache de textos. É só **rodar o instalador de novo**. Textos novos que ainda não foram traduzidos aparecem em inglês; para listá-los:

```
python tools/missing_keys.py
```

## Limitações conhecidas

- Textos que ficam desenhados nas imagens das cartas e alguns textos embutidos nos prefabs do jogo continuam em inglês.
- O contrato de licença (EULA) foi mantido em inglês de propósito.
- A tradução foi feita com apoio de IA e **sem revisão por falante nativo**. Os termos de regras seguem o manual de *Uprising* da Galápagos ([glossário](translation/GLOSSARIO.md)), mas nomes de cartas e termos de *Ascensão de Ix* e *Imortalidade* não têm referência oficial aqui e podem diferir da edição física. Correções são bem-vindas.
- É uma modificação do lado do cliente, só de texto. Use por sua conta e risco, principalmente no jogo online.
- Só testado no Windows com a versão de outubro/2026 do jogo.

## Contribuir

Edite `translation/pt_BR.txt` (formato `chave=valor`, uma por linha) e abra um Pull Request. Regras:

- Mantenha **exatamente** as tags e marcadores: `<b>`, `<sprite name="...">`, `<br>`, `[name]`, `[card]`, `{0}`, `\n`.
- Siga o [glossário](translation/GLOSSARIO.md).
- Tratamento por "você".

## Licença

O código (`patcher/`, `tools/`, scripts) é MIT. O texto original do jogo pertence aos seus detentores; `translation/pt_BR.txt` é uma obra derivada fornecida para uso pessoal.
