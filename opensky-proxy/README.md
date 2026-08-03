# opensky-proxy

Proxy Vercel (Serverless Functions) para a API do OpenSky Network, usado pela
aba "Mapa ao Vivo" do app Aviso Aéreo. Existe porque o app é um site estático
no GitHub Pages, sem backend — e o `client_secret` do OpenSky **nunca pode**
ir para o navegador (diferente da API key da REDEMET usada nas outras abas,
que é uma chave de baixo privilégio feita pra uso em app cliente).

O navegador chama este proxy; o proxy guarda `client_id`/`client_secret`,
troca por um `access_token` OAuth2 (cacheado em memória por ~25 min) e repassa
a chamada pra API real do OpenSky. O segredo nunca aparece no JS público nem
no repositório.

## Por que Vercel e não Cloudflare Workers

A primeira versão deste proxy foi feita em Cloudflare Workers. Funcionava
(deploy ok, CORS ok), mas toda chamada ao servidor de autenticação do OpenSky
(`auth.opensky-network.org`) retornava **522 (timeout de conexão)** — mesmo
adicionando um `User-Agent` de navegador. Testamos a mesma requisição fora da
rede do Cloudflare e ela funcionou normalmente, então não é um problema no
código: o OpenSky não responde a conexões vindas da rede de saída do
Cloudflare Workers (comportamento comum em APIs que bloqueiam faixas de IP de
provedores de nuvem/CDN como proteção antiabuso). O Vercel roda as funções
sobre infraestrutura AWS, com faixa de IP diferente, e funciona.

## Setup (uma vez)

Nenhum destes comandos expõe o segredo pra mim (Claude) nem pro repositório —
rode-os você mesmo no seu terminal.

```bash
cd opensky-proxy
npm install

npx vercel login
# abre o navegador só pra você autorizar o CLI

npx vercel link
# associa esta pasta a um projeto Vercel (cria um novo se perguntado)

npx vercel env add OPENSKY_CLIENT_ID production
# cola o client_id quando for solicitado (entrada oculta)

npx vercel env add OPENSKY_CLIENT_SECRET production
# cola o client_secret quando for solicitado (idem)

npx vercel env add ALLOWED_ORIGINS production
# valor: https://pabloeduardo89.github.io

npx vercel --prod
# publica e imprime a URL, algo como:
# https://opensky-proxy-xxxx.vercel.app
```

Copie essa URL para a constante `OPENSKY_PROXY_BASE` no `index.html` (as rotas
já incluem o prefixo `/api`, não precisa adicionar nada além da URL base).

## Desenvolvimento local

```bash
npx vercel dev
```

Precisa das env vars configuradas (rode `npx vercel env pull .env.local` para
trazê-las pro ambiente local, se necessário). Teste com:

```bash
curl "http://localhost:3000/api/states?lamin=-30&lomin=-55&lamax=-20&lomax=-45"
```

## Rotas expostas

Todas em `GET`, todas retornam o JSON original da API do OpenSky (repassado sem
transformação, só autenticado).

| Rota | Parâmetros | Endpoint OpenSky | Uso |
|---|---|---|---|
| `/api/states` | `lamin, lomin, lamax, lomax` | `/states/all` | Tráfego ao vivo na área visível do mapa (em uso na aba Mapa ao Vivo) |
| `/api/flights/arrival` | `airport, begin, end` | `/flights/arrival` | Chegadas por aeroporto/período (pronto, ainda não usado na UI) |
| `/api/flights/departure` | `airport, begin, end` | `/flights/departure` | Partidas por aeroporto/período (idem) |
| `/api/track` | `icao24, time` | `/tracks/all` | Histórico de uma aeronave — API do OpenSky limita a 30 dias no passado (idem) |

Lógica compartilhada (autenticação, CORS, proxy genérico) fica em `api/_lib.js`
— arquivos prefixados com `_` não viram rota própria no Vercel, só helper.
Adicionar uma rota nova no futuro é criar um arquivo em `api/` chamando
`proxyToOpenSky(path, params)`.

## Origens permitidas (CORS)

Configurado pela env var `ALLOWED_ORIGINS` (separado por vírgula, sem
espaços). Por padrão (se a variável não existir) só
`https://pabloeduardo89.github.io` — qualquer outro site que tentar chamar o
proxy é bloqueado por CORS, pra ninguém além do seu app consumir sua cota do
OpenSky. `http://localhost:*` e `http://127.0.0.1:*` são sempre liberados,
pra facilitar teste local.

## Cache / cota

- Token OAuth2: cacheado ~25 min em memória do container da função, evita
  pedir um token novo a cada request. Não é persistente entre execuções frias
  (cold start) — se o tráfego crescer muito, dá pra trocar por Vercel KV.
- Resposta de `/api/states`: cacheada ~8s por bbox (arredondado a ~0.1°),
  mesmo princípio. Protege a cota do OpenSky — que é compartilhada entre
  *todos* os visitantes do site — de várias abas/pessoas batendo ao mesmo
  tempo na mesma região.
