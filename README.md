# Portolan Browser Italia

Il [Portolan Browser](https://github.com/portolan-sdi/portolan-browser) con la
veste grafica della pubblica amministrazione italiana, per i cataloghi
Portolan che riguardano l'Italia.

Sito: <https://anncsu-open.github.io/portolan-browser-it/>

Non è un browser diverso. È la release ufficiale, fissata in
`browser.version`, con un tema ispirato a Designers Italia (Bootstrap Italia),
l'italiano come lingua predefinita e una pagina di partenza con i cataloghi
italiani del registro Portolan. Il browser ufficiale resta
<https://browser.portolan-sdi.org>.

## Linkare un catalogo

Chi pubblica un catalogo può affiancare questo link a quello del Portolan
Browser, con l'URL del catalogo senza `https://`:

```text
https://anncsu-open.github.io/portolan-browser-it/#/external/<host e percorso del catalog.json>
```

Per esempio, per ANNCSU:
<https://anncsu-open.github.io/portolan-browser-it/#/external/pub-1e760dc850cb4a5aa5f8afb77713f8cd.r2.dev/catalog.json>

## Quali cataloghi compaiono

Un catalogo del registro compare nella pagina di partenza quando tutti i suoi
produttori hanno un sito con dominio `.it`. Le eccezioni stanno in
`overrides.yaml`: `include` aggiunge un catalogo, `exclude` lo toglie.
L'elenco si aggiorna ogni giorno.

## Come funziona

Il repository contiene solo lo strato che si applica al browser:

- `config.it.js`: le opzioni, passate al browser con `SB_CONFIG`;
- `theme/`: colori, font, scala tipografica e stile dei componenti (link,
  pulsanti, campi, schede, badge, tabelle) di Bootstrap Italia 2.18, aggiunti
  ai file del tema del browser;
- `locales/`: le traduzioni italiane mancanti e le etichette del footer;
- `widgets.config.js`: la riga del footer che dice chi gestisce il sito e che
  non è istituzionale, in italiano o in inglese;
- `public/`: font, logo e favicon.

`scripts/apply_overlay.py` applica lo strato a una copia del browser e si
ferma se un file che modifica è cambiato. `scripts/filter_registry.py`
prepara l'elenco dei cataloghi italiani. Il design è in `docs/design.md`.

## Build locale

Servono `uv`, Node e Git.

```shell
./scripts/build_local.sh
npx -y pnpm@10 --dir .upstream exec vite preview --base /portolan-browser-it/
```

## Aggiornare il browser

Cambia il tag in `browser.version` e rilancia la build. Se la nuova release ha
spostato un punto che lo strato modifica, `apply_overlay.py` lo dice e si
ferma.

## Test

```shell
uv run scripts/test_filter_registry.py
uv run scripts/test_apply_overlay.py
```

Dopo una build locale, con l'anteprima avviata, `tests/visual/check_layout.mjs`
apre il sito in un browser e controlla che:

- l'header parta dal bordo superiore, alto 120px su desktop e 72px quando si
  scorre, con nome e logo più piccoli su telefono;
- il menu della lingua si apra e passi all'inglese;
- il footer dica chi gestisce il sito, in italiano e in inglese;
- la pagina non sbordi in orizzontale;
- font, titoli, link, pulsanti, campi, schede, badge e tabelle abbiano i valori
  di Bootstrap Italia.

Usa il Playwright installato con il browser; `CHROMIUM` indica un eseguibile
alternativo se quello di Playwright manca:

```shell
node tests/visual/check_layout.mjs http://localhost:4173/portolan-browser-it/
```

## Licenza

ISC, come il Portolan Browser. I font Titillium Web e Roboto Mono sono
distribuiti con la SIL Open Font License (`public/fonts/`).
