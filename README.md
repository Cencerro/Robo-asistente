# Robo-assistente

Sistema de automatización vía crontab. `automata.py` es el punto de entrada llamado por cron con el nombre de la tarea como argumento.

## Arquitectura

### Estructura de directorios

```
robo-assistente/
├── automata.py                    # Entry point de cron
├── requirements.txt               # Dependencias con versiones exactas
├── .env                           # Secretos (no commitear)
├── .env.example                   # Plantilla de variables de entorno
├── .gitignore
│
├── tasks/
│   ├── __init__.py                # Registro de tareas (diccionario)
│   └── menu/
│       ├── __init__.py
│       ├── task.py                # Orquestador: llama scraper → extractor → sender
│       ├── scraper.py             # Busca URL del PDF en la web
│       ├── extractor.py           # Sube PDF a Claude Files API, extrae menús
│       └── sender.py              # Envía menú del día por Telegram
│
├── lib/
│   ├── __init__.py
│   ├── config.py                  # Pydantic-settings: carga y valida .env
│   ├── logger.py                  # Logger centralizado (RotatingFile + stderr)
│   ├── storage.py                 # Helpers JSON con escritura atómica
│   ├── claude_client.py           # Wrapper Claude API + Files API
│   ├── mistral_client.py          # Wrapper Mistral API (para tareas simples)
│   └── telegram_client.py        # Wrapper Telegram Bot API
│
├── data/
│   └── menus/
│       └── menu_YYYY_MM.json      # Un fichero por mes
│
├── logs/
│   └── automata.log               # Rotación automática (5MB × 3 backups)
│
├── docker/
│   ├── Dockerfile                 # Python slim, instala dependencias
│   └── docker-compose.yml         # Monta .env, data/, logs/ como volúmenes
│
└── tests/
    ├── conftest.py
    ├── test_menu_scraper.py
    ├── test_menu_extractor.py
    └── test_storage.py
```

## Uso

### Requisitos previos

```bash
cp .env.example .env   # rellenar con los valores reales
```

### Desarrollo (local con Docker)

```bash
# Construir imagen
docker compose -f docker/docker-compose.yml build

# Ejecutar una tarea
docker compose -f docker/docker-compose.yml run automata python automata.py menu
```

El bind mount monta el directorio local en `/app`, por lo que los cambios en el código se reflejan sin reconstruir la imagen.

### Producción (Docker)

```bash
# Primera vez — construir imagen
docker compose -f docker/docker-compose.prod.yml build

# Lanzar manualmente
docker compose -f docker/docker-compose.prod.yml run --rm automata python automata.py menu
```

`data/` y `logs/` persisten en volúmenes Docker entre ejecuciones.

**Cron en el servidor host:**
```cron
# Menú escolar — lunes a viernes a las 11:00
0 11 * * 1-5 cd /opt/robo-asistente && docker compose -f docker/docker-compose.prod.yml run --rm automata python automata.py menu
```

### Tests

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar tests
pytest
```

---

### Flujo de la tarea `menu`

```
cron → automata.py menu
         │
         ▼
    tasks/__init__.py  (registry lookup)
         │
         ▼
    tasks/menu/task.py → run()
         │
         ├─ storage.py: ¿existe data/menus/menu_YYYY_MM.json con clave hoy?
         │       YES ──────────────────────────────────────────┐
         │       NO                                            │
         │                                                     │
         ├─ scraper.py: GET página web → extrae URL del PDF    │
         │                                                     │
         ├─ extractor.py:                                      │
         │     ¿json tiene claude_file_id?                     │
         │       NO → httpx descarga PDF → Claude Files upload │
         │       → guarda file_id en json                      │
         │     Claude extract_from_file(file_id, prompt)       │
         │     → parsea JSON de menús → guarda en json         │
         │                                                     │
         └─ sender.py: obtiene menú de hoy ◄────────────────────┘
                       → Telegram send_message()
```

## Diseño

### Despacho de tareas
Diccionario explícito en `tasks/__init__.py`. Cada tarea expone `run()`.

### Web scraping
`httpx` + `BeautifulSoup4` (parser `lxml`) + `tenacity` para reintentos.

### Claude Files API
- Modelo: `claude-sonnet-4-6`
- Beta header: `anthropic-beta: files-2025-04-14`
- Se almacena el `file_id` en el JSON mensual para no re-subir el mismo PDF

### Estructura del menú (JSON)
```json
{
  "period": "2026-03",
  "source_url": "https://...",
  "claude_file_id": "file_abc123",
  "fetched_at": "2026-03-18T08:00:00Z",
  "days": {
    "2026-03-18": {
      "dejeuner": {
        "entree": "Salade de carottes",
        "plat": "Poulet rôti",
        "garniture": null,
        "dessert": "Yaourt"
      },
      "gouter": {
        "composantes": ["Pain", "Beurre", "Pomme"]
      }
    }
  }
}
```

### Logging
- `RotatingFileHandler`: `logs/automata.log` (5MB × 3 backups)
- `StreamHandler` a stderr (para MAILTO de cron)
- Timestamps en UTC

### Jerarquía de excepciones
```
RoboAssistenteError
├── ConfigError
├── ScrapingError
├── ClaudeAPIError
├── MistralAPIError
├── TelegramError
└── StorageError
```

## Próximas funcionalidades

### Arquitectura long-running con bot interactivo

El sistema evolucionará de contenedor efímero (cron) a un **contenedor long-running** con dos componentes internos:

- **APScheduler** — gestiona las tareas programadas (reemplaza el cron del host)
- **Telegram polling** — escucha mensajes y comandos de los usuarios en tiempo real

```
contenedor long-running
├── APScheduler → ejecuta tareas según agenda interna
└── Telegram bot → escucha comandos y responde
```

### Interacción en lenguaje natural vía Mistral

El bot aceptará peticiones en lenguaje natural. El flujo será:

```
usuario → "¿Qué hay de comer el jueves?"
    │
    ▼
Telegram bot recibe el mensaje
    │
    ▼
Mistral recibe: mensaje del usuario + catálogo de acciones disponibles del automata
    │
    ▼
Mistral devuelve: acción estructurada { "task": "menu", "date": "2026-03-19" }
    │
    ▼
automata ejecuta la acción y responde por Telegram
```

Mistral actúa como capa de interpretación: transforma lenguaje libre en llamadas concretas al automata, sin lógica de parsing en el código. Añadir nuevas capacidades al bot solo requiere registrar la acción en el catálogo que se le pasa a Mistral.

---

## Configuración

Variables requeridas en `.env`:
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
