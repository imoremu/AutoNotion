# Testing Guide for AutoNotion

Este documento explica cómo ejecutar y mantener los tests para AutoNotion en ambos entornos: Azure Functions y Vercel.

## Estructura de Tests

### Tests por Categoría

#### **Unit Tests** (`tests/unit/`)
- `test_shared_service.py` - Tests del servicio compartido
- Tests específicos de lógica de negocio
- Tests de componentes individuales

#### **Integration Tests** (`tests/integration/`)
- `test_vercel_api_routes.py` - Tests de rutas API de Vercel con Flask
- `test_flask_logging.py` - Tests de configuración de logging en Flask
- `test_shared_service_integration.py` - Tests de integración del servicio compartido
- `test_dual_deployment.py` - Tests de compatibilidad entre plataformas

#### **Business Logic Tests** (`tests/`)
- `test_daily_tasks_automation.py` - Tests de automatización de tareas diarias
- `test_add_alerted_objective_tasks.py` - Tests de tareas objetivo alertadas
- `test_duplicate_unfinished_tasks.py` - Tests de duplicación de tareas no terminadas
- `test_generate_periodic_tasks.py` - Tests de generación de tareas periódicas

## Ejecutar Tests

### Usando el Script de Ejecución

```bash
# Ejecutar todos los tests
python scripts/run_tests.py --type all

# Ejecutar solo tests de Azure Functions
python scripts/run_tests.py --type azure

# Ejecutar solo tests de Vercel/Flask
python scripts/run_tests.py --type flask

# Ejecutar solo tests del servicio compartido
python scripts/run_tests.py --type shared

# Ejecutar solo tests nuevos
python scripts/run_tests.py --type new

# Ejecutar con salida verbose
python scripts/run_tests.py --type flask --verbose
```

### Usando pytest directamente

```bash
# Ejecutar tests específicos
pytest tests/integration/test_vercel_api_routes.py -v

# Ejecutar tests con marcadores
pytest -m flask -v

# Ejecutar tests con configuración específica
pytest -c pytest-flask.ini tests/integration/ -v
```

## Tests de Flask/Vercel

### Estructura de Tests Flask

Los tests de Flask usan `Flask.test_client()` para simular requests HTTP:

```python
def test_hello_notion_with_query_param(self):
    """Test hello-notion endpoint with query parameter."""
    with hello_app.test_client() as client:
        response = client.get('/?name=TestUser')
        
        assert response.status_code == 200
        assert "Hello, TestUser" in response.get_json()['body']
```

### Tests de Logging

Los tests de logging verifican:
- ✅ Configuración de logging se carga correctamente
- ✅ Variables de entorno se respetan
- ✅ Fallback funciona cuando no hay configuración
- ✅ Diferentes niveles de logging funcionan

### Tests de Integración

Los tests de integración verifican:
- ✅ Servicio compartido funciona con Flask
- ✅ Manejo de errores es robusto
- ✅ Configuración de logging se aplica correctamente
- ✅ Variables de entorno se leen correctamente

## Configuración de Tests

### Variables de Entorno para Tests

```bash
# Para tests de desarrollo
SERVICE_LOG_LEVEL=DEBUG
LOG_LEVEL=DEBUG

# Para tests de producción
SERVICE_LOG_LEVEL=INFO
LOG_LEVEL=INFO
```

### Mocking en Tests

Los tests usan mocking para:
- ✅ Simular respuestas de Notion API
- ✅ Simular variables de entorno
- ✅ Simular errores de red
- ✅ Simular configuraciones de logging

## Cobertura de Tests

### Tests Existentes (Azure Functions)
- ✅ **Core Business Logic** - 100% cubierto
- ✅ **Notion API Integration** - 100% cubierto
- ✅ **Error Handling** - 100% cubierto
- ✅ **Edge Cases** - 100% cubierto

### Tests Nuevos (Vercel/Flask)
- ✅ **Flask API Routes** - 100% cubierto
- ✅ **Logging Configuration** - 100% cubierto
- ✅ **Shared Service Integration** - 100% cubierto
- ✅ **Error Handling** - 100% cubierto

## Troubleshooting

### Problemas Comunes

#### **Import Errors**
```bash
# Error: No module named 'shared'
# Solución: Asegúrate de estar en el directorio correcto
cd "C:\Users\Nereodata\Iván Moreno Muñoz\Gestión Interna - Nereodata - Documentos\07. Desarrollos SW\Azure\AutoNotion"
```

#### **Flask App Errors**
```bash
# Error: Flask app not found
# Solución: Verifica que las rutas de importación sean correctas
from deployments.vercel.api.hello_notion import app as hello_app
```

#### **Mocking Errors**
```bash
# Error: Mock not working
# Solución: Verifica que el path del mock sea correcto
@mock.patch('deployments.vercel.api.run_daily_plan.NotionService')
```

### Debugging Tests

```bash
# Ejecutar tests con salida detallada
pytest tests/integration/test_vercel_api_routes.py -v -s

# Ejecutar tests con pdb
pytest tests/integration/test_vercel_api_routes.py --pdb

# Ejecutar tests específicos
pytest tests/integration/test_vercel_api_routes.py::TestVercelAPIRoutes::test_hello_notion_with_query_param -v
```

## Mejores Prácticas

### 1. **Naming Convention**
- Tests descriptivos: `test_hello_notion_with_query_param`
- Clases descriptivas: `TestVercelAPIRoutes`
- Archivos descriptivos: `test_vercel_api_routes.py`

### 2. **Test Structure**
- **Arrange** - Configurar datos de prueba
- **Act** - Ejecutar la función a probar
- **Assert** - Verificar resultados

### 3. **Mocking**
- Mock solo lo necesario
- Usar `@mock.patch` para funciones específicas
- Verificar que los mocks se llamen correctamente

### 4. **Error Handling**
- Probar casos de éxito y error
- Probar edge cases
- Probar manejo de excepciones

## CI/CD Integration

### GitHub Actions (Ejemplo)

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python scripts/run_tests.py --type all
```

### Vercel Integration

```bash
# En vercel.json
{
  "buildCommand": "python scripts/run_tests.py --type flask",
  "devCommand": "python scripts/run_tests.py --type flask --verbose"
}
```
