# Dune: Imperium — Tradução pt-BR (Steam)

Tradução não oficial para português do Brasil do **Dune: Imperium** (Dire Wolf Digital) na Steam.

> Projeto de fãs, sem ligação com a Dire Wolf Digital, Asmodee, Legendary ou os detentores de *Duna*. Nenhum arquivo do jogo é distribuído aqui, só o texto traduzido e um instalador que o aplica na sua cópia.

## Como funciona (e uma limitação importante)

O menu de idiomas do jogo **é montado a partir da lista de idiomas da Steam** (inglês, francês, italiano, alemão, espanhol, tcheco, japonês, polonês, coreano, ucraniano e chinês). Português do Brasil não está nessa lista, e não dá para acrescentar um item ao menu só trocando arquivos de dados.

Por isso o instalador troca o **texto do idioma "English"** pelo português. No jogo você continua em *Configurações → Idiomas → English* (é o padrão), e tudo aparece em português. Nenhum outro idioma e nenhum arquivo da pasta da Steam é alterado.

## Instalar (Windows)

1. Abra o jogo **uma vez com internet** até o menu principal e feche. É nesse momento que ele baixa os textos que o instalador modifica.
2. Instale o [Python 3.9+](https://www.python.org/downloads/) (marque *Add Python to PATH*).
3. Baixe este repositório (*Code → Download ZIP*), extraia e dê duplo clique em `install.bat`.
4. Abra o jogo.

## Desinstalar

`restaurar.bat`. O original é restaurado a partir do backup (`__data.original`).

## O que o instalador altera

| Arquivo | O que muda | Backup |
|---|---|---|
| `%USERPROFILE%\AppData\LocalLow\Unity\Dire Wolf Digital_Dune_ Imperium\localization\…\__data` | o texto `en_US` recebe a tradução | `__data.original` |

## Quando o jogo atualizar

Atualizações podem trocar o cache de textos. É só **rodar o instalador de novo**. Textos novos que ainda não foram traduzidos aparecem em inglês; para listá-los:

```
python tools/missing_keys.py
```

## Modo experimental: usar a vaga de outro idioma

`python patcher/dune_ptbr.py --usar-vaga` troca o texto de outro idioma da lista (por padrão o tcheco) em vez do inglês. **O rótulo no menu continua o do idioma original** (por exemplo "Čeština"), porque ele vem da Steam. Esse modo também altera o bundle de idiomas da pasta da Steam (ajustando o CRC para o jogo aceitá-lo) e por isso não é o padrão. `restaurar.bat` desfaz.

## Limitações conhecidas

- O menu mostra "English" mesmo com o jogo em português (veja acima).
- Textos que ficam desenhados nas imagens das cartas e alguns textos embutidos nos prefabs do jogo continuam em inglês.
- O contrato de licença (EULA) foi mantido em inglês de propósito.
- A tradução foi feita com apoio de IA e **sem revisão por falante nativo**. Os termos de regras seguem o manual de *Uprising* da Galápagos ([glossário](translation/GLOSSARIO.md)), mas nomes de cartas e termos de *Ascensão de Ix* e *Imortalidade* não têm referência oficial aqui e podem diferir da edição física. Correções são bem-vindas.
- É uma modificação do lado do cliente, só de texto. Use por sua conta e risco, principalmente no jogo online.
- Só testado no Windows com a versão 4.1.2.1808 do jogo.

## Contribuir

Edite `translation/pt_BR.txt` (formato `chave=valor`, uma por linha) e abra um Pull Request. Regras:

- Mantenha **exatamente** as tags e marcadores: `<b>`, `<sprite name="...">`, `<br>`, `[name]`, `[card]`, `{0}`, `\n`.
- Siga o [glossário](translation/GLOSSARIO.md).
- Tratamento por "você".

## Licença e direitos

- **Código** (`patcher/`, `tools/`, scripts `.bat`): licença MIT (arquivo `LICENSE`).
- **Texto traduzido** (`translation/pt_BR.txt`): obra derivada do texto de *Dune: Imperium*. **Não é licenciada para reutilização**; é fornecida apenas para uso pessoal, com os direitos do texto original preservados para seus detentores (Dire Wolf Digital, Legendary, Herbert Properties e demais).
- Se você é detentor desses direitos e quer a remoção do conteúdo, abra uma issue ou contate o mantenedor, e o texto será retirado.
- O repositório não contém arquivos, imagens, áudios ou código do jogo.
