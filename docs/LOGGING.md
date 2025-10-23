# Logging Configuration for AutoNotion

Este documento explica cómo configurar el logging para que funcione correctamente en ambos entornos: Azure Functions y Vercel.

## Problema Común: Logs DEBUG no aparecen en Vercel

### Causas del problema:

1. **Configuración de logging no se carga correctamente** en Vercel
2. **Nivel de logging por defecto** en Vercel es INFO, no DEBUG
3. **Archivos de configuración** no se encuentran en la ruta correcta
4. **Loggers específicos** no están configurados para DEBUG

### Solución Implementada:

#### 1. Configuración de Logging para Vercel

Hemos creado `config/logging_vercel.json` que:
- ✅ Configura nivel DEBUG para todos los loggers
- ✅ Incluye formateo detallado con número de línea
- ✅ Configura loggers específicos para cada módulo
- ✅ Usa solo console handler (no archivos en Vercel)

#### 2. Inicialización de Logging en Funciones Vercel

Cada función de Vercel ahora:
- ✅ Carga la configuración de logging al inicio
- ✅ Tiene fallback a logging básico con DEBUG
- ✅ Configura loggers específicos para cada módulo

#### 3. Configuración del NotionDailyPlanner

El `NotionDailyPlanner` ahora:
- ✅ Se configura con el mismo sistema de logging
- ✅ Usa el logger `autonotion.notion_registry_daily_plan`
- ✅ Nivel DEBUG configurado correctamente

## Archivos de Configuración

### `config/logging_vercel.json`
```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "detailed": {
      "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
      "formatter": "detailed",
      "stream": "ext://sys.stdout"
    }
  },
  "loggers": {
    "shared.notion_service": {
      "handlers": ["console"],
      "level": "DEBUG",
      "propagate": false
    },
    "autonotion.notion_registry_daily_plan": {
      "handlers": ["console"],
      "level": "DEBUG",
      "propagate": false
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": ["console"]
  }
}
```

## Cómo Verificar que Funciona

### 1. En Vercel Dashboard:
- Ve a tu proyecto en Vercel
- Ve a la pestaña "Functions"
- Ejecuta una función manualmente
- Revisa los logs en tiempo real

### 2. Logs que deberías ver:
```
2025-01-23 10:30:15 DEBUG [shared.notion_service:45] Starting daily plan execution.
2025-01-23 10:30:15 DEBUG [autonotion.notion_registry_daily_plan:307] Starting periodic task generation.
2025-01-23 10:30:15 DEBUG [autonotion.notion_registry_daily_plan:315] Found 3 periodic tasks in the main tasks database.
2025-01-23 10:30:15 DEBUG [autonotion.notion_registry_daily_plan:325] Processing periodic task with title property: Daily Standup
```

### 3. Si no ves logs DEBUG:
1. **Verifica que el archivo de configuración existe** en `config/logging_vercel.json`
2. **Revisa que la función carga la configuración** correctamente
3. **Verifica que el logger se inicializa** antes de usar el NotionDailyPlanner

## Troubleshooting

### Problema: "No module named 'shared'"
**Solución:** Asegúrate de que el directorio `shared` esté en el PYTHONPATH o en la raíz del proyecto.

### Problema: "Config file not found"
**Solución:** Verifica que la ruta al archivo de configuración sea correcta:
```python
config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "logging_vercel.json")
```

### Problema: "Logs aparecen pero no en DEBUG"
**Solución:** Verifica que el nivel del logger esté configurado correctamente:
```python
logger = logging.getLogger('autonotion.notion_registry_daily_plan')
logger.setLevel(logging.DEBUG)
```

## Configuración por Entorno

### Azure Functions
- Usa `config/logging.json` (configuración original)
- Incluye file handler para `local_debug.log`
- Configuración automática via `function_app.py`

### Vercel
- Usa `config/logging_vercel.json` (configuración específica)
- Solo console handler (no archivos)
- Configuración manual en cada función

## Variables de Entorno

### Configuración en Vercel Dashboard

Puedes controlar el nivel de logging con dos variables de entorno:

1. **Ve a tu proyecto en Vercel Dashboard**
2. **Settings > Environment Variables**
3. **Añade las variables:**
   - **Name:** `LOG_LEVEL` (logging general del sistema)
   - **Value:** `INFO` (o `DEBUG`, `WARNING`, `ERROR`)
   - **Name:** `SERVICE_LOG_LEVEL` (logging específico del negocio)
   - **Value:** `INFO` (o `DEBUG`, `WARNING`, `ERROR`)

### Niveles Disponibles

- `DEBUG` - Muestra todos los logs (incluyendo DEBUG del NotionDailyPlanner)
- `INFO` - Solo logs INFO y superiores
- `WARNING` - Solo logs WARNING y ERROR
- `ERROR` - Solo logs ERROR

### Configuración Automática

El código ahora:
- ✅ **Lee automáticamente** la variable `LOG_LEVEL`
- ✅ **Aplica el nivel** a todos los loggers
- ✅ **Sobrescribe la configuración** del archivo JSON
- ✅ **Funciona en fallback** si no hay archivo de configuración

### Ejemplo de Uso

```bash
# En Vercel Dashboard > Environment Variables
LOG_LEVEL=INFO              # Logging general del sistema
SERVICE_LOG_LEVEL=DEBUG     # Logging específico del negocio (NotionDailyPlanner, etc.)
```

### Separación de Responsabilidades

- **`LOG_LEVEL`** - Controla el logging general del sistema (Vercel, Flask, etc.)
- **`SERVICE_LOG_LEVEL`** - Controla el logging específico del negocio:
  - `autonotion.notion_registry_daily_plan`
  - `shared.notion_service`
  - Funciones de Vercel específicas del servicio

### Verificación

Cuando ejecutes una función, deberías ver en los logs:
```
Vercel logging configured with level: DEBUG
```

O si usa fallback:
```
Vercel logging fallback configured with level: DEBUG
```

### Configuración Recomendada

**Por defecto (sin variables de entorno):**
```bash
# Nivel INFO para ambos (configuración por defecto)
LOG_LEVEL=INFO
SERVICE_LOG_LEVEL=INFO
```

Para desarrollo:
```bash
LOG_LEVEL=DEBUG
SERVICE_LOG_LEVEL=DEBUG
```

Para producción:
```bash
LOG_LEVEL=INFO
SERVICE_LOG_LEVEL=INFO
```

Para debugging específico del negocio:
```bash
LOG_LEVEL=INFO
SERVICE_LOG_LEVEL=DEBUG
```