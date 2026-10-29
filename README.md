# Impact Lab 3D

Simulador de impacto veicular para o navegador (Chrome). Renderização em **WebGPU + WGSL**, física em **C compilado para WebAssembly**, deformação de carroceria calculada na GPU.

> **Aviso sobre o modelo físico:** é um modelo **simplificado** de corpo rígido com esmagamento (lei força × deformação com histerese). **Não é** análise por elementos finitos. Os picos de desaceleração (em g) são de corpo rígido e **não** representam o que ocupantes sofreriam. Use para estudo e demonstração, nunca para engenharia ou segurança real.

## Como executar

Requisitos: Chrome 113+ (desktop) com WebGPU ativo e um servidor HTTP local (`file://` não funciona: módulos ES, `fetch` de shaders e WASM).

```bash
cd impact-lab-3d
python3 serve.py                 # http://localhost:8000  (MIME correto para .wasm/.wgsl, sem cache)
# alternativa simples: python3 -m http.server 8000
```

O binário `wasm/sim.wasm` já acompanha o projeto. Para recompilar a física:

```bash
cd physics
make          # clang --target=wasm32 (sem libc) -> ../wasm/sim.wasm
make test     # 89 verificações nativas
make emcc     # alternativa com Emscripten (não testada neste ambiente)
```

Se o Chrome não mostrar WebGPU: verifique `chrome://gpu`; em Linux use `--enable-unsafe-webgpu --enable-features=Vulkan`. O jogo exibe uma tela de erro explicando a causa (sem WebGPU, sem adaptador, erro de shader, WASM ausente) e recupera-se de perda de dispositivo gráfico.

## Celular (Chrome Android)

**Por que o jogo "não abria":** a WebGPU só existe em *contexto seguro*: `https://…` ou `http://localhost`. Abrir `file://` ou `http://192.168.x.x:8000` no celular desativa a WebGPU (e `file://` ainda bloqueia módulos/`fetch`). O jogo agora detecta isso e mostra uma tela explicando a causa e as soluções. Requisitos do aparelho: **Chrome 121+**, **Android 12+**, GPU **Qualcomm ou ARM (Mali)** ([fonte](https://developer.chrome.com/blog/new-in-webgpu-121)). iPhone/iPad: o Chrome usa o motor do Safari, sem garantia de WebGPU.

Formas de abrir no celular (da mais simples para a mais técnica):

1. **Hospedagem HTTPS gratuita (recomendado, funciona em qualquer lugar).** Envie a pasta inteira (com `.nojekyll`) para GitHub Pages, ou arraste-a em app.netlify.com/drop, ou Cloudflare Pages. Abra o link `https://…` no Chrome do celular. Todos os caminhos são relativos, então funciona em subpastas (`usuario.github.io/repo/`).
2. **Cabo USB + `adb reverse`** (o celular enxerga `localhost` do PC, que é contexto seguro). No celular: Opções do desenvolvedor → Depuração USB. No PC: `python3 serve.py` e, em outro terminal, `adb reverse tcp:8000 tcp:8000`. No Chrome do celular abra `http://localhost:8000`.
3. **Wi-Fi com HTTPS autoassinado.** `python3 serve.py --https` (precisa de `openssl`), abra o endereço `https://<IP-do-PC>:8000` mostrado, e no aviso do Chrome toque em *Avançado → Continuar*. PC e celular na mesma rede; libere a porta no firewall.
4. **Wi-Fi com HTTP + flag.** Em `chrome://flags/#unsafely-treat-insecure-origin-as-secure` do celular, adicione `http://<IP-do-PC>:8000`, ative e reinicie o Chrome.

Abra **`/diagnostico.html`** no mesmo endereço para um relatório (contexto seguro, versão do Chrome, adaptador WebGPU, limites, compilação dos shaders, carga do WASM).

Adaptações para celular: qualidade **Baixa** por padrão (resolução interna limitada por orçamento de pixels, sombras 1024, menos partículas — ajustável em Configurações), pausa automática ao sair do app, tela cheia (⛶) com bloqueio de paisagem, abas na garagem para o carro continuar visível, HUD compacto em paisagem, arrastar com um dedo para girar, **pinça** para zoom (câmera orbital), botões de toque (direção/acelerar/frear) no modo manual, `touch-action`/`overscroll` desativados para não rolar nem dar zoom sem querer, e altura `dvh` para a barra do navegador.

## Como jogar

1. **Garagem**: escolha veículo (Hatch, Sedan, SUV/Picape), cor/acabamento, motorização (Econômica, Esportiva, Alta Potência), carga extra, velocidade-alvo (30/50/80/100/120/150 ou personalizada), obstáculo (parede, barreira deformável, poste, bloco), face do veículo, ângulo e deslocamento lateral, e direção manual opcional.
2. **INICIAR TESTE**: o veículo parte **exatamente a 200 m** do obstáculo. O piloto automático mira a velocidade-alvo; a **velocidade real de impacto é medida** e mostrada separadamente. Para alvos altos o simulador calcula uma *velocidade de lançamento* (visível na garagem e no resultado), pois a aceleração em 200 m é limitada.
3. HUD: velocímetro, distância, tempo, força G, barra de 200 m, mapa de danos com 8 zonas (clique para detalhes), 6 câmeras, telemetria (FPS, CPU/GPU, física).

### Controles

| Entrada | Ação |
|---|---|
| W/↑, S/↓, A D/←→, Espaço | Acelerar, frear, direção, freio (modo manual) |
| P / Esc | Pausar |
| Enter · R · T ou B | Iniciar · Reiniciar · Voltar a 200 m e restaurar carroceria |
| 1–6 · V | Câmeras (Orbital, Interna, Lateral, Fixa na Parede, Perseguição, Cinematográfica) |
| M · `,` `.` | Câmera lenta (0,1×) · Velocidade de reprodução (0,05× a 4×) |
| H · F | Ocultar HUD · Telemetria |
| Arrastar / roda | Câmera orbital e plataforma da garagem |
| Gamepad | RT/LT, analógico esquerdo, A reinicia, B câmera, Start pausa |
| Toque | Arrastar = girar, pinça = zoom, botões na tela (modo manual) |

## Arquitetura

```
index.html            telas e HUD (DOM)
diagnostico.html      relatório de compatibilidade (HTTPS, WebGPU, shaders, WASM)
serve.py              servidor local (MIME, sem cache, --https opcional)
styles/               main.css · garage.css · hud.css
src/
  game.js             boot, laço rAF, passo fixo 1/480 s, gerenciador de simulação, efeitos
  physics-bridge.js   carga/validação do WASM, API tipada, índices de saída
  renderer.js         WebGPU: pipelines, shadow map, MSAA 4x, partículas, timestamps, miniaturas
  vehicle.js          malhas procedurais dos 3 veículos (materiais separados, interior, rodas)
  deformation.js      GPUDeformer (compute) + espelho em CPU para rodas
  scene.js            pista, parede, obstáculos, garagem, cenário
  cameras.js · controls.js · ui.js · damage-map.js · telemetry.js · audio.js · math.js
shaders/              lighting (PBR/sombras/ambiente) · vehicle · scene · deformation · particles (.wgsl)
physics/              sim.c · sim.h · test_sim.c · Makefile   ->  wasm/sim.wasm
tests/                testes WASM, geometria e harness de renderização offscreen
```

**Divisão de trabalho.** O C resolve contato (CCD com sub-passos), impulso/energia (E=½mv²), dinâmica veicular com transferência de carga e calcula **36 valores de esmagamento permanente** com direção. Só esse campo compacto (~1 KB) vai à GPU; um *compute shader* desloca cada vértice a partir da malha de repouso e recalcula normais por adjacência (sem atomics). A geometria deformada nunca volta à CPU, e o despacho só ocorre quando o campo muda. Dano por zona, vidros/faróis quebrados e os percentuais do mapa vêm dessa simulação.

Convenções: SI; parede em z=0, veículo parte de z=-200 rumo a +z; x local positivo = esquerda.

## Limitações conhecidas

- Corpo rígido + esmagamento, sem FEM, sem manequim/airbag; picos de g não são filtrados por ocupante (ex.: ~270 g a 150 km/h).
- Deformação procedural suave: não há rasgo de chapa nem fragmentos reais destacados (apenas partículas).
- Restaurar carroceria e voltar a 200 m são a mesma operação (a simulação reinicia por completo).
- A validação de **apresentação no canvas** não pôde ser feita em Chromium headless (sem tela); o caminho de renderização foi verificado via modo `?offscreen=1`, que desenha em textura e lê os pixels. Teste em Chrome com GPU real.
- `make emcc` não foi testado (o ambiente de desenvolvimento só tinha clang/wasm-ld).
- Sem arquivos de modelo/textura externos: tudo é procedural (`assets/` reservado).

## Plano de testes

Automatizados:
- `cd physics && make test` — 89 verificações (conservação de energia, impulso, CCD, alvos 30–150 km/h, offsets, ângulos, laterais, ré).
- `node tests/run-wasm-tests.mjs` — 29 verificações sobre o `.wasm` real (API, versão, determinismo, reset).
- `node tests/geometry-check.mjs` — malhas: sem NaN, normais para fora, limites.
- Renderização: `tests/harness.html` + Playwright/Chromium (`--enable-unsafe-webgpu`), capturando via `renderer.capture()`; `?offscreen=1` em `index.html` expõe `window.__impactlab` para fluxos completos (garagem → teste → impacto → resultado).

Manuais (Chrome com GPU): percorrer menu → garagem (trocar veículo/cor/motor, miniaturas atualizam) → teste a 30/80/150 km/h em cada obstáculo e face; conferir distância inicial 200 m, alvo × velocidade real, mapa de danos coerente com a região atingida, vidros/faróis quebrados, pausa sem acúmulo de tempo, câmera lenta, reiniciar/voltar a 200 m, 6 câmeras, gamepad/toque, redimensionar a janela, dia/entardecer/noite, qualidade baixa/média/alta, e a tela de erro ao abrir via `file://`.
