# SPEC — Pantalla única y rutas FastAPI

Documento de contrato entre `ui/mockup.html` y el backend (`src/agent/ui.py`).
El mockup es la referencia visual; esta spec fija los nombres, los payloads y los
estados que la implementación tiene que respetar.

- **Pantalla:** una sola. Sin router de frontend, sin build, sin JS de aplicación.
- **Interacción:** HTML + atributos HTMX (`hx-post`, `hx-get`, `hx-target`, `hx-swap`,
  `hx-trigger`, `hx-indicator`, `hx-vals`, `hx-encoding`, `hx-swap-oob`).
- **Servidor:** FastAPI + Jinja2. Cada ruta devuelve **fragmentos HTML**, no JSON,
  salvo `/health` y el modo `Accept: application/json` de `/ask` (para la eval).
- **Privacidad:** ninguna ruta hace requests salientes. No hay CDN, ni fuentes
  remotas, ni telemetría. `Network requests: 0` es un valor renderizado por el
  servidor, no un contador que se pueda "resetear".

---

## 1. Archivos

| Archivo | Rol |
| --- | --- |
| `ui/mockup.html` | Pantalla completa con estados de ejemplo. Referencia visual y de marcado. |
| `ui/styles.css` | Única hoja de estilos. Sin `@import`, sin webfonts. |
| `src/agent/ui.py` | App FastAPI, monta `/static`, define las rutas de §3. |
| `src/agent/templates/index.html` | Shell completo (el `mockup.html` con Jinja en los puntos de datos). |
| `src/agent/templates/partials/*.html` | Fragmentos que devuelven las rutas POST. |

Convención de nombres de parciales:

```
partials/answer.html        respuesta del agente + bloque OOB de fuentes
partials/answer_error.html  error recuperable de /ask
partials/sources.html       lista de fuentes (también se usa OOB)
partials/source_detail.html texto completo de un chunk
partials/doc_item.html      una fila de la lista de documentos
partials/draft.html         contenido de #draft-panel
partials/health.html        widget de estado
```

---

## 2. Mapa de componentes

IDs estables. El backend no inventa selectores nuevos: si hace falta otro target,
se agrega acá primero.

| ID | Elemento | Lo escribe |
| --- | --- | --- |
| `#chat-log` | Contenedor `role="log"` con los turnos | `/ask` (append) |
| `#doc-list` | `<ul>` de documentos | `/ingest` (append + OOB) |
| `#sources-list` | Lista de fuentes de la última respuesta | `/ask` (OOB) |
| `#src-detail-{chunk_id}` | Detalle expandido de una fuente | `/sources/{chunk_id}` |
| `#draft-panel` | Cuerpo del panel de borrador | `/draft` |
| `#health` | Widget de estado | `/health` (poll 30 s) |
| `#ingest-progress` | Indicador de ingesta | HTMX (`.htmx-indicator`) |
| `#ask-indicator`, `#draft-indicator` | Spinners | HTMX |
| `#delete-dialog` | `<dialog>` de confirmación | estático |

Regla: **un id, un dueño**. `#chat-log` sólo recibe appends; `#sources-list` se
reemplaza entero con cada respuesta para que nunca queden citas de una pregunta
anterior.

---

## 3. Rutas

| Método | Ruta | Devuelve | Target / swap |
| --- | --- | --- | --- |
| `GET` | `/` | Página completa | — |
| `POST` | `/ingest` | Fragmentos `doc_item` + OOB | `#doc-list` / `beforeend` |
| `POST` | `/ask` | `answer` + OOB `sources-list` | `#chat-log` / `beforeend` |
| `POST` | `/draft` | Contenido de `#draft-panel` | `#draft-panel` / `innerHTML` |
| `GET` | `/sources/{chunk_id}` | `source_detail` | `#src-detail-{id}` / `innerHTML` |
| `POST` | `/delete` | `204` + `HX-Redirect: /` | — |
| `GET` | `/health` | JSON o fragmento `health` | `#health` / `outerHTML` |

Todas las rutas son `async def` y comparten un `AppState` en `app.state`
(conexión SQLite, cliente Ollama, agente smolagents). El índice se abre por
request con `check_same_thread=False` o un pool de 1 conexión con lock: SQLite
en modo WAL alcanza para una usuaria.

### 3.1 `GET /`

Renderiza `index.html` con:

```python
{
  "documents": [...],        # documentos indexados, con conteo de chunks
  "chunks_total": 148,
  "health": {...},           # mismo payload que /health
  "network_requests": 0,
}
```

Si `documents` está vacío, el template renderiza el estado **empty** (§4.1) y
`#chat-log` arranca con el mensaje de bienvenida en vez de sugerencias.

Errores: `500` si la DB no abre → página de error con `Reintentar`
(`hx-get="/"`, `hx-target="body"`).

### 3.2 `POST /ingest`

Sube e indexa uno o varios archivos.

**Request** — `multipart/form-data`

| Campo | Tipo | Reglas |
| --- | --- | --- |
| `files` | `UploadFile[]` | 1..20 archivos; `.pdf`, `.md`, `.markdown`, `.txt`; ≤ 25 MB c/u |

**Proceso**

1. Validar extensión y tamaño. Rechazo por archivo, no por lote.
2. `sha256` del archivo: si ya está en `documents`, se saltea y se marca
   "Ya estaba" (no se reindexa, no se duplica).
3. Extraer texto (`pypdf` página por página / lectura directa para Markdown).
4. Chunking por cláusula (§ `ingest.chunk_by_clause`).
5. Embeddings `bge-m3` en un solo batch por archivo.
6. Insert transaccional: documento + chunks + `chunks_fts` + `chunks_vec`.

**Response `200`** — un `doc_item` por archivo, en el orden de subida:

```html
<li class="doc">
  <span class="doc-icon" aria-hidden="true">…</span>
  <span class="doc-body">
    <span class="doc-name">contrato-boda-marisol-tomas.pdf</span>
    <span class="doc-meta-row">
      <span class="doc-meta">PDF · 6 págs</span>
      <span class="chip chip-ok">Indexado</span>
    </span>
  </span>
</li>
```

Más un bloque OOB con el contador del índice y el widget de estado:

```html
<span id="doc-count" hx-swap-oob="innerHTML">6</span>
<div id="health" hx-swap-oob="outerHTML">…</div>
```

**Errores**

| Código | Cuándo | Qué ve Lucía |
| --- | --- | --- |
| `415` | Extensión no soportada | `doc_item` con chip `No compatible` y el motivo en `title` |
| `422` | PDF sin texto seleccionable | `doc_item` con chip `Escaneado` + texto "Este PDF es una foto. La app sólo lee PDFs con texto seleccionable." |
| `507` | Sin espacio / DB bloqueada | Banda de error bajo el dropzone + `Reintentar` |
| `503` | Ollama caído (falla `embed_texts`) | `doc_item` `Sin indexar` + CTA "Revisá que Ollama esté abierto" |

Nunca se aborta el lote entero por un archivo: cada fila comunica su resultado.
El estado de la ingesta se muestra dentro del dropzone (`#ingest-progress`).

### 3.3 `POST /ask`

**Request** — `application/x-www-form-urlencoded`

| Campo | Tipo | Reglas |
| --- | --- | --- |
| `q` | `str` | 1..500 caracteres, se normaliza (trim, colapsa espacios) |
| `doc_id` | `int?` | filtro opcional a un documento |

**Proceso**

1. `hybrid_search(q, top_k=8)` → BM25 + vec + RRF.
2. Agente smolagents con el prompt que restringe a los chunks y exige JSON
   (`answer`, `citations[]`, `confidence`).
3. Verificación `quote in chunk.text` (normalizado). Un reintento con
   instrucción de copiar textual; si vuelve a fallar → **refusal**.
4. Render `partials/answer.html` + OOB `partials/sources.html`.

**Response `200`** (fragmento, `hx-target="#chat-log"`, `hx-swap="beforeend"`):

```html
<article class="msg msg-bot" data-confidence="0.86" data-mode="answer">
  <div class="msg-head">
    <span class="avatar" aria-hidden="true">…</span>
    <span class="msg-author">Nido</span>
    <span class="msg-time">09:41</span>
    <span class="chip chip-ok chip-dot">3 citas verificadas</span>
  </div>
  <div class="msg-body">
    <p>Tenés dos pagos pendientes…</p>
    <ul class="answer-list">
      <li>…<a class="cite" href="#src-1"
             hx-get="/sources/128" hx-target="#src-detail-1"
             hx-swap="innerHTML" aria-label="Ver fuente 1">1</a>…</li>
    </ul>
  </div>
  <div class="msg-actions">
    <button class="btn btn-primary btn-sm" hx-post="/draft"
            hx-vals='{"client":"marisol-ruiz","mode":"preview"}'
            hx-target="#draft-panel" hx-swap="innerHTML">Preparar recordatorio</button>
  </div>
</article>

<div id="sources-list" hx-swap-oob="innerHTML">…partials/sources.html…</div>
```

Cada `citations[i]` genera `#src-{i+1}` y `#src-detail-{chunk_id}`; los números de
las citas en el texto coinciden con `src-num`. `data-mode` ∈
`answer | refusal`, `data-confidence` es el `confidence` del JSON.

**Variante JSON** (para `eval/run_eval.py` y tests): si
`Accept: application/json`, devuelve directamente

```json
{
  "answer": "string",
  "citations": [
    {"chunk_id": 128, "document": "factura-2026-014.pdf",
     "page": 1, "clause": "Condiciones de pago", "quote": "texto exacto"}
  ],
  "confidence": 0.86,
  "mode": "answer",
  "latency_ms": 2140
}
```

**Errores**

| Código | Cuándo | Qué ve Lucía |
| --- | --- | --- |
| `422` | `q` vacío o > 500 | El composer marca el borde y muestra "Escribí una pregunta." |
| `503` | Ollama no responde | Fragmento `answer_error`: "Ollama no está respondiendo. Abrí la app desde el Dock y volvé intentar." + `Reintentar` (`hx-post="/ask"` con la misma `q`) |
| `500` | Excepción no prevista | "Algo falló al leer tus documentos. Probá de nuevo." + `Reintentar`; el traceback va sólo al log local |

Un refusal **no** es un error HTTP: es `200` con `data-mode="refusal"` (§4.4).

### 3.4 `POST /draft`

Genera (y opcionalmente guarda) el recordatorio de pago en Markdown.

**Request** — `application/x-www-form-urlencoded`

| Campo | Tipo | Reglas |
| --- | --- | --- |
| `client` | `str?` | slug del cliente (`marisol-ruiz`). Alternativa: `chunk_id` |
| `chunk_id` | `int?` | fuente ancla si no hay slug |
| `mode` | `"preview" \| "save"` | default `preview` |
| `overwrite` | `bool` | default `false` |

**Proceso**

1. Reunir la evidencia: factura (monto, número, vencimiento) + cláusula de plazo.
   Si falta monto o vencimiento → `422`, no se inventa nada.
2. Redactar el cuerpo con el modelo, con la plantilla de §3.4.1.
3. Render `partials/draft.html` dentro de `#draft-panel` (`innerHTML`).
4. Si `mode="save"`: escribir `output/recordatorios/<YYYY-MM-DD>-<slug>.md` y,
   si `OBSIDIAN_VAULT` está configurado, copiar a `<vault>/Nido/`. El frontmatter
   lleva `fuente:` con el chunk de origen.

**Archivo generado**

```markdown
---
tipo: recordatorio-pago
cliente: Marisol Ruiz
factura: 2026-014
monto: 480000
moneda: ARS
vencimiento: 2026-11-10
estado: vencida
fuente: factura-2026-014.pdf#p1
creado: 2026-11-18
---

# Recordatorio de pago — Marisol Ruiz

Hola Marisol,
…
```

**Errores**

| Código | Cuándo | Qué ve Lucía |
| --- | --- | --- |
| `422` | Faltan monto/vencimiento en la evidencia | "No encontré el monto en la factura. Revisá que esté subida." |
| `409` | `overwrite=false` y el archivo existe | Aviso con dos botones: `Abrir el existente` / `Reemplazar` (`overwrite=true`) |
| `503` | Ollama caído | Igual que `/ask` |
| `500` | No se pudo escribir en `output/` | "No pude guardar el archivo. Revisá los permisos de la carpeta." |

**Regla:** `mode="save"` sólo escribe dentro de `output/` y del vault configurado.
Nunca sobrescribe un `.md` ajeno sin `overwrite=true` explícito.

### 3.5 `GET /sources/{chunk_id}`

Devuelve el texto completo del chunk, con el quote resaltado, para el botón
"Ver página completa".

**Request:** path `chunk_id: int`. Sin body.

**Response `200`** (`#src-detail-{id}`, `innerHTML`):

```html
<p class="src-page">Página 1 · Condiciones de pago</p>
<blockquote class="quote">
  …texto del chunk, con <mark>el fragmento citado</mark>…
</blockquote>
<p class="src-origin">factura-2026-014.pdf · indexado el 18 nov 2026</p>
```

**Errores:** `404` → `<p class="src-empty">Ese fragmento ya no está en el índice.
Volvé a subir el documento.</p>` (código `404`, cuerpo HTML igual).

### 3.6 `POST /delete`

Borra **todo** lo que generó la app. Nunca los archivos originales de Lucía.

**Request** — `application/x-www-form-urlencoded`

| Campo | Tipo | Reglas |
| --- | --- | --- |
| `confirm` | `str` | obligatorio, valor exacto `borrar-todo` |

**Borra:** `data/index.db` (+ `-wal`, `-shm`), `output/` completo, logs de
consulta (`data/private/queries.log` si existe), y cualquier caché de embeddings.

**No borra:** los PDFs y `.md` que Lucía subió (viven fuera del proyecto), ni el
vault de Obsidian.

**Response `204`** con `HX-Redirect: /`. El HTML del diálogo ya pidió confirmación,
así que no hace falta un segundo prompt del navegador.

**Errores**

| Código | Cuándo |
| --- | --- |
| `400` | Falta `confirm` o el valor no coincide → `{"detail": "confirmación inválida"}` |
| `500` | Algún archivo no se pudo borrar → lista de rutas fallidas en el log |

Tras el borrado, `GET /` renderiza el estado **empty** y `/health` reporta
`index.ready=false`.

### 3.7 `GET /health`

**Response `200`** — `application/json`:

```json
{
  "status": "ok",
  "ollama": {"reachable": true, "model": "gemma4:12b", "latency_ms": 42},
  "index": {"ready": true, "documents": 5, "chunks": 148,
            "updated_at": "2026-11-18T12:04:11-03:00"},
  "output": {"drafts": 3},
  "network_requests": 0,
  "version": "0.1.0"
}
```

`status` ∈ `ok | degraded | down`:

- `ok`: Ollama responde y el índice abre.
- `degraded`: el índice está bien pero Ollama no (se puede consultar nada nuevo,
  se puede ver lo ya respondido).
- `down`: no abre la DB → la UI muestra el estado **error**.

**Variante HTML** — si viene `HX-Request: true` o `Accept: text/html`, devuelve el
fragmento `#health` para el poll de 30 s:

```html
<div class="health" id="health" hx-get="/health" hx-trigger="every 30s" hx-swap="outerHTML">
  <p class="health-title">Estado</p>
  <div class="health-row">
    <span class="dot dot-ok" aria-hidden="true"></span>
    <span class="health-label">Ollama corriendo</span>
    <span class="health-detail">gemma4:12b</span>
  </div>
  <div class="health-row">
    <span class="dot dot-ok" aria-hidden="true"></span>
    <span class="health-label">Índice listo</span>
    <span class="health-detail">5 docs · 148</span>
  </div>
</div>
```

El endpoint es de sólo lectura: chequea `ollama.list()` con timeout de 1 s y
`SELECT count(*)` sobre `documents`/`chunks`. No escribe nada.

---

## 4. Estados de la UI

Cada estado tiene marcado propio para que la implementación no improvise copy.

### 4.1 `empty`

Se da cuando `documents = 0`.

- El dropzone pasa a ocupar el bloque central con el título
  "Arrastrá tu primer contrato o factura".
- `#chat-log` muestra un solo mensaje del sistema: "Cuando subas un contrato o una
  factura, puedo responderte con la cita exacta."
- `#sources-list` y `#draft-panel` muestran un placeholder de una línea, no un panel vacío.
- `#health` sigue visible (Ollama puede estar corriendo sin índice).

### 4.2 `loading`

Dos variantes, mismo patrón: el contenido viejo no se borra hasta que llega el nuevo.

- **Pregunta:** el turno del usuario se agrega al instante (optimista, lo hace el
  navegador no; lo agrega el server en el mismo fragmento). Debajo, un `article.msg-bot`
  con tres líneas fantasma (`.mini-line`) y el texto "Buscando en 5 documentos…".
  El spinner vive en `#ask-indicator` vía `hx-indicator`; el botón queda `disabled`
  con `aria-busy="true"` en `#chat-log`.
- **Ingesta:** `#ingest-progress` aparece dentro del dropzone: spinner +
  "Leyendo e indexando…". El `<input type="file">` queda `disabled`.

Target de latencia: primer byte del fragmento de carga en < 100 ms; la respuesta
final, < 6 s en la MacBook de referencia. Si pasa de 10 s, se corta con `503` y
mensaje de reintento.

### 4.3 `answer`

`article.msg-bot[data-mode="answer"]` con:

- `answer` en 1–3 párrafos; listas sólo cuando hay 2+ ítems comparables.
- Citas inline como `<a class="cite">` con `aria-label="Ver fuente N: <documento>"`.
- Chip "N citas verificadas" sólo si **todas** las citas pasaron el substring check.
  Si pasó `N-1` de `N`, el chip dice "1 cita sin verificar" y el párrafo afectado
  pierde la cita (nunca se muestra una cita no verificada).
- `#sources-list` se reemplaza completo (OOB) y la primera fuente queda abierta
  (`<details open>`), con `mark` sobre el fragmento citado.
- `#draft-panel` **no** se toca: el borrador se genera sólo con el botón
  "Preparar recordatorio".

### 4.4 `refusal`

`200`, `data-mode="refusal"`, `data-confidence` bajo (< 0.35).

Copy base, sin inventar y sin disculpas vacías:

> No encontré eso en tus documentos.
> Lo que sí está: [tema más cercano].
> ¿Querés que busque en [otro documento]?

Reglas:

- Nunca se muestran citas "de relleno". Si hay un chunk cercano sin respaldo, se
  menciona como "lo más parecido" **sin** afirmarlo y sin número de cita.
- El chip del encabezado dice "Sin cita" (chip `chip-neutral`), no "0 citas".
- Se ofrecen hasta 2 preguntas reformuladas como `.suggestion` dentro del mensaje.

### 4.5 `error`

Distinguir tres causas, siempre con una sola acción:

| Causa | Copy | Acción |
| --- | --- | --- |
| Ollama apagado | "Ollama no está respondiendo. Abrí la app desde el ícono del Dock y volvé a intentar." | `Reintentar` (repite la misma request) |
| Índice roto/ausente | "El índice no está disponible. Volvé a subir tus documentos." | `Ir a documentos` |
| Fallo inesperado | "Algo falló al procesar la pregunta. No se envió nada a ningún lado." | `Reintentar` |

El bloque de error usa `role="alert"` (no `aria-live="polite"`, porque interrumpe).
En el sidebar, `#health` cambia el dot a `dot-bad` y el texto a "Ollama apagado".

### 4.6 `deleting`

- El `<dialog>` se cierra y el botón `Delete everything` pasa a
  "Borrando…" con `aria-busy="true"` y `disabled`.
- Al volver `204` + `HX-Redirect: /`, la página se recarga en estado `empty`.
- Si falla, el diálogo se reabre con la lista de lo que no se pudo borrar.

---

## 5. Reglas de interacción

1. **Un solo request por acción.** Nada de polling salvo `/health` cada 30 s.
2. **OOB para paneles laterales.** `/ask` siempre devuelve `#sources-list` con
   `hx-swap-oob="innerHTML"`; si no hay citas, devuelve la lista vacía con el
   mensaje "Sin fuentes para esta respuesta".
3. **Nada de `hx-confirm`** para borrar: la confirmación es el `<dialog>`, que
   además explica qué se borra y qué no.
4. **`hx-indicator` en todos los POST** para que el spinner no dependa de JS.
5. **Sin `hx-boost`** global: la página no navega.
6. **Foco.** Después de un swap, el foco va al nuevo `article.msg-bot`
   (`tabindex="-1"`) para que un lector de pantalla anuncie la respuesta. Se
   implementa con `hx-on::after-swap` o con un `<script>` de 10 líneas; es la
   única JS de la app y es opcional.
7. **El texto de los documentos es untrusted.** Se pasa entre delimitadores y el
   system prompt ignora instrucciones embebidas. La UI no interpreta el HTML de
   los chunks: se escapa y se renderiza como texto.

---

## 6. Accesibilidad

- Contraste AA verificado sobre la paleta del mockup (mínimo 4.73:1 en texto
  pequeño; ver tabla en el commit de la UI).
- Foco visible en todo elemento interactivo: `outline: 2px solid` con offset, y
  anillo blanco+oliva en los botones de acento.
- `label` real para el input de archivos (`sr-only`) y para el textarea del chat.
  El `<summary>` de cada fuente es el control de expandir/colapsar.
- `role="log"` + `aria-live="polite"` en `#chat-log`; `role="alert"` en errores.
- `aria-busy` en el contenedor mientras se espera respuesta.
- Navegación completa por teclado: dropzone → documentos → chat → fuentes →
  borrador → borrar. `Skip link` al inicio.
- `prefers-reduced-motion` desactiva spinners y transiciones.

---

## 7. Privacidad

- `GET /health` reporta `network_requests: 0` porque no hay ningún cliente HTTP
  en el proceso. El día que se agregue uno, el test `tests/test_no_network.py`
  falla (monkeypatch de `socket.socket.connect`).
- Los documentos no salen de `data/index.db` + `output/`.
- `POST /delete` es la única ruta destructiva y exige confirmación explícita.
- No hay analytics, ni crash reporting, ni "check de actualizaciones".

---

## 8. Decisiones abiertas

1. **Vault de Obsidian:** falta confirmar la ruta real en la Mac de Lucía. Hasta
   entonces `mode="save"` escribe sólo en `output/recordatorios/`.
2. **`<dialog command>`:** el mockup usa `commandfor`/`command` para abrir el
   diálogo sin JS. Si el navegador de Lucía no lo soporta (Safari < 26), hace falta
   un fallback de 6 líneas (`dialog.showModal()`).
3. **Un documento por vez vs. lote:** `/ingest` acepta hasta 20 archivos; si el
   hardware se queda corto con los embeddings, bajar a 5 y encolar el resto.
4. **Idioma:** toda la UI en español rioplatense; el badge "Local. Private. Yours."
   queda en inglés por decisión de marca. Si Lucía lo pide, se traduce sin tocar
   el layout (es un solo string).
