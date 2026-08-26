# opensky-proxy

Proxy Vercel (Serverless Functions) usado pela aba "Mapa ao Vivo". Existe
porque o app é um site estático no GitHub Pages, sem backend próprio — então
qualquer chamada que precise de segredo (OpenSky) ou que esbarre em CORS
(adsb.lol) tem que passar por aqui.

> **Atualização (ago/2026):** a aba "Mapa ao Vivo" usava o
> [airplanes.live](https://airplanes.live/api-guide/) direto do navegador
> (sem proxy, CORS liberado). Em algum momento eles passaram a bloquear
> chamadas não registradas (HTTP 403, "contact us"). A aba foi migrada pra
> **adsb.lol** — agregador comunitário da mesma família de software (mesmo
> formato de resposta, mesmas rotas `/point`, `/callsign`, `/hex`, `/reg`),
> mas que não devolve `Access-Control-Allow-Origin`, então precisa passar
> pela rota `/api/live` deste proxy (ver abaixo). É a rota **em uso hoje**.
> As rotas do OpenSky (`/api/states` e as demais) ficam dormentes no repo,
> prontas caso seja necessário voltar a usá-las — ver "Rotas expostas".

## Setup (uma vez)

Nenhum destes comandos expõe segredo nenhum pra mim (Claude) nem pro
repositório — rode-os você mesmo no seu terminal.

```bash
cd opensky-proxy
npm install

npx vercel login
# abre o navegador só pra você autorizar o CLI

npx vercel link
# associa esta pasta a um projeto Vercel (cria um novo se perguntado)

npx vercel env add ALLOWED_ORIGINS production
# valor: https://pabloeduardo89.github.io

npx vercel --prod
# publica e imprime a URL, algo como:
# https://opensky-proxy-xxxx.vercel.app
```

Copie essa URL para a constante `LIVE_PROXY_BASE` no `index.html` (a rota já
inclui o prefixo `/api`, não precisa adicionar nada além da URL base).

A rota `/api/live` (adsb.lol, em uso hoje) **não precisa** de
`OPENSKY_CLIENT_ID`/`OPENSKY_CLIENT_SECRET` — só `ALLOWED_ORIGINS`. Esses dois
só são necessários se um dia reativar as rotas do OpenSky (ver tabela
abaixo).

## Por que Vercel e não Cloudflare Workers

A primeira versão deste proxy foi feita em Cloudflare Workers, pra atender o
OpenSky. Funcionava (deploy ok, CORS ok), mas toda chamada ao servidor de
autenticação do OpenSky (`auth.opensky-network.org`) retornava **522 (timeout
de conexão)** — mesmo adicionando um `User-Agent` de navegador. Testamos a
mesma requisição fora da rede do Cloudflare e ela funcionou normalmente,
então não é um problema no código: o OpenSky não responde a conexões vindas
da rede de saída do Cloudflare Workers (comportamento comum em APIs que
bloqueiam faixas de IP de provedores de nuvem/CDN como proteção antiabuso).
O Vercel roda as funções serverless sobre infraestrutura AWS, com faixa de IP
diferente, e funciona. Mantivemos a mesma casa (Vercel) pra rota nova do
adsb.lol por simplicidade — ela não tem esse problema específico, mas não há
razão pra espalhar o proxy em dois provedores.

## Desenvolvimento local

```bash
npx vercel dev
```

Teste com:

```bash
curl "http://localhost:3000/api/live?p=point/-15.78/-47.93/50"
```

Para as rotas do OpenSky (dormentes), precisa das env vars
`OPENSKY_CLIENT_ID`/`OPENSKY_CLIENT_SECRET` configuradas (rode
`npx vercel env pull .env.local` pra trazê-las pro ambiente local).

## Rotas expostas

Todas em `GET`, todas retornam o JSON original da API de origem (repassado
sem transformação).

| Rota | Parâmetros | Endpoint de origem | Uso |
|---|---|---|---|
| `/api/live` | `p` (caminho da API adsb.lol, ex.: `point/-15.78/-47.93/50`, `hex/e4803d`, `callsign/TAM8111`, `reg/PR-MHG`) | `api.adsb.lol/v2/{p}` | **Em uso** — tráfego ao vivo e busca por callsign/hex/registro na aba Mapa ao Vivo |
| `/api/states` | `lamin, lomin, lamax, lomax` | OpenSky `/states/all` | Dormente — tráfego ao vivo por bbox (usado antes da migração pro airplanes.live/adsb.lol) |
| `/api/flights/arrival` | `airport, begin, end` | OpenSky `/flights/arrival` | Dormente — chegadas por aeroporto/período, nunca chegou a ser usado na UI |
| `/api/flights/departure` | `airport, begin, end` | OpenSky `/flights/departure` | Dormente — partidas por aeroporto/período, idem |
| `/api/track` | `icao24, time` | OpenSky `/tracks/all` | Dormente — histórico de uma aeronave (OpenSky limita a 30 dias no passado), idem |

Lógica compartilhada (CORS, tratamento de erro) fica em `api/_lib.js` —
arquivos prefixados com `_` não viram rota própria no Vercel, só helper.
`/api/live.js` usa só `handleCorsPreflight`/`describeError` dali (repasse
simples, sem autenticação); as rotas do OpenSky usam também
`proxyToOpenSky`/`makeFlightsHandler` (autenticação OAuth2).

`/api/live.js` valida o parâmetro `p` contra uma lista de formatos permitidos
(`point/.../.../...`, `callsign/...`, `hex/...`, `reg/...`) antes de repassar
— pra este proxy não virar um jeito de bater em qualquer URL através do seu
domínio Vercel.

## Origens permitidas (CORS)

Configurado pela env var `ALLOWED_ORIGINS` (separado por vírgula, sem
espaços). Por padrão (se a variável não existir) só
`https://pabloeduardo89.github.io` — qualquer outro site que tentar chamar o
proxy é bloqueado por CORS, pra ninguém além do seu app consumir sua cota.
`http://localhost:*` e `http://127.0.0.1:*` são sempre liberados, pra
facilitar teste local.

## Cache / cota

- `/api/live`: sem cache próprio hoje — o adsb.lol é gratuito e não pede
  autenticação, então não há cota compartilhada em jogo como havia no
  OpenSky. Se o tráfego do site crescer muito, vale adicionar um cache curto
  (~8s) por caminho, no mesmo princípio usado antes pro OpenSky.
- Token OAuth2 do OpenSky (rotas dormentes): cacheado ~25 min em memória do
  container da função, evita pedir um token novo a cada request. Não é
  persistente entre execuções frias (cold start).
