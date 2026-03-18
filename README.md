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

## Configuración

Copiar `.env.example` a `.env` y completar las variables:

```bash
cp .env.example .env
```

Variables requeridas:
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Ejecución

### Desarrollo (Docker en Windows)
```bash
docker compose -f docker/docker-compose.yml run --rm automata
```

### Producción (Debian con crontab)
```bash
python automata.py menu
```

### Tests
```bash
pytest -m "not integration"
```

## Crontab (producción)
```cron
# Menú escolar — lunes a viernes a las 8:00
0 8 * * 1-5 /usr/bin/python3 /opt/robo-assistente/automata.py menu >> /dev/null 2>&1
```
