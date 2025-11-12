"""
Simple web application to test Notion API queries.
Run with: python notion_query_tester.py
"""
import json
import os
import logging
import requests
from flask import Flask, request, render_template_string, jsonify
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from local.settings.json if it exists
def load_local_settings():
    """Load environment variables from config/local.settings.json"""
    settings_path = Path(__file__).parent / 'config' / 'local.settings.json'
    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                values = settings.get('Values', {})
                for key, value in values.items():
                    if key.startswith('NOTION_') and key not in os.environ:
                        os.environ[key] = value
                        logger.info(f'Loaded {key} from local.settings.json')
        except Exception as e:
            logger.warning(f'Could not load local.settings.json: {e}')

# Load settings at startup
load_local_settings()

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notion API Query Tester</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
            transition: border-color 0.3s;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .method-selector {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .method-selector label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            padding: 10px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .method-selector input[type="radio"] {
            margin: 0;
        }
        .method-selector input[type="radio"]:checked + span {
            color: #667eea;
        }
        .method-selector label:has(input:checked) {
            border-color: #667eea;
            background: #f0f4ff;
        }
        .endpoint-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .endpoint-input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .result-container {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .result-header h2 {
            color: #333;
            font-size: 1.3em;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }
        .status-success {
            background: #d4edda;
            color: #155724;
        }
        .status-error {
            background: #f8d7da;
            color: #721c24;
        }
        .result-content {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }
        .error-message {
            color: #f44336;
            padding: 15px;
            background: #ffebee;
            border-left: 4px solid #f44336;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .info-box code {
            background: rgba(0,0,0,0.1);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Notion API Query Tester</h1>
            <p>Prueba queries de la API de Notion y visualiza los resultados completos</p>
        </div>
        <div class="content">
            <div class="info-box">
                <strong>💡 Instrucciones:</strong><br>
                • <strong>Método GET:</strong> Ingresa solo el endpoint (ej: <code>/v1/databases/{database_id}</code>)<br>
                • <strong>Método POST:</strong> Selecciona POST primero, luego ingresa el endpoint y el body JSON aparecerá debajo (ej: <code>/v1/databases/{database_id}/query</code> con el filtro en el body)
            </div>
            
            <form id="queryForm" onsubmit="submitQuery(event)">
                <div class="method-selector">
                    <label>
                        <input type="radio" name="method" value="GET" checked>
                        <span>GET</span>
                    </label>
                    <label>
                        <input type="radio" name="method" value="POST">
                        <span>POST</span>
                    </label>
                </div>
                
                <div class="form-group">
                    <label for="endpoint">Endpoint:</label>
                    <input 
                        type="text" 
                        id="endpoint" 
                        name="endpoint" 
                        class="endpoint-input"
                        placeholder="/v1/databases/{database_id} o /v1/databases/{database_id}/query"
                        required
                    >
                </div>
                
                <div class="form-group" id="bodyGroup" style="display: none;">
                    <label for="body">Body (JSON): <span style="color: #667eea; font-weight: normal;">(Requerido para POST)</span></label>
                    <textarea 
                        id="body" 
                        name="body" 
                        placeholder='{"filter": {"property": "Status", "select": {"equals": "Done"}}}'
                        style="min-height: 150px;"
                    ></textarea>
                </div>
                
                <button type="submit" id="submitBtn">Ejecutar Query</button>
            </form>
            
            <div id="resultContainer" class="result-container" style="display: none;">
                <div class="result-header">
                    <h2>Resultado</h2>
                    <span id="statusBadge" class="status-badge"></span>
                </div>
                <div id="errorMessage" class="error-message" style="display: none;"></div>
                <pre id="resultContent" class="result-content"></pre>
            </div>
        </div>
    </div>

    <script>
        // Show/hide body textarea based on method
        function toggleBodyField() {
            const method = document.querySelector('input[name="method"]:checked').value;
            const bodyGroup = document.getElementById('bodyGroup');
            bodyGroup.style.display = method === 'POST' ? 'block' : 'none';
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            toggleBodyField();
        });
        
        // Update when method changes
        document.querySelectorAll('input[name="method"]').forEach(radio => {
            radio.addEventListener('change', toggleBodyField);
        });

        async function submitQuery(event) {
            event.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const resultContainer = document.getElementById('resultContainer');
            const resultContent = document.getElementById('resultContent');
            const statusBadge = document.getElementById('statusBadge');
            const errorMessage = document.getElementById('errorMessage');
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Ejecutando...';
            resultContainer.style.display = 'none';
            errorMessage.style.display = 'none';
            
            const method = document.querySelector('input[name="method"]:checked').value;
            const endpoint = document.getElementById('endpoint').value;
            const body = document.getElementById('body').value;
            
            try {
                const payload = {
                    method: method,
                    endpoint: endpoint
                };
                
                if (method === 'POST' && body) {
                    try {
                        payload.body = JSON.parse(body);
                    } catch (e) {
                        throw new Error('El body debe ser un JSON válido');
                    }
                }
                
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await response.json();
                
                resultContainer.style.display = 'block';
                
                if (data.success) {
                    statusBadge.textContent = `Status: ${data.status_code}`;
                    statusBadge.className = 'status-badge status-success';
                    errorMessage.style.display = 'none';
                    resultContent.textContent = JSON.stringify(data.result, null, 2);
                } else {
                    statusBadge.textContent = `Error: ${data.status_code || 'N/A'}`;
                    statusBadge.className = 'status-badge status-error';
                    errorMessage.textContent = data.error || 'Error desconocido';
                    errorMessage.style.display = 'block';
                    resultContent.textContent = JSON.stringify(data, null, 2);
                }
            } catch (error) {
                resultContainer.style.display = 'block';
                statusBadge.textContent = 'Error';
                statusBadge.className = 'status-badge status-error';
                errorMessage.textContent = error.message;
                errorMessage.style.display = 'block';
                resultContent.textContent = error.toString();
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Ejecutar Query';
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Render the main page."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/query', methods=['POST'])
def execute_query():
    """Execute a Notion API query."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No se proporcionó ningún dato',
                'status_code': 400
            }), 400
        
        method = data.get('method', 'GET').upper()
        endpoint = data.get('endpoint', '').strip()
        body = data.get('body')
        
        if not endpoint:
            return jsonify({
                'success': False,
                'error': 'El endpoint es requerido',
                'status_code': 400
            }), 400
        
        # Get Notion API key from environment
        api_key = os.environ.get('NOTION_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'NOTION_API_KEY no está configurada en las variables de entorno',
                'status_code': 500
            }), 500
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        # Build full URL
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f'https://api.notion.com{endpoint}'
        
        logger.info(f'Executing {method} request to {url}')
        
        # Execute the request
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            if not body:
                return jsonify({
                    'success': False,
                    'error': 'El body es requerido para requests POST',
                    'status_code': 400
                }), 400
            response = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            return jsonify({
                'success': False,
                'error': f'Método {method} no soportado. Solo GET y POST están disponibles.',
                'status_code': 400
            }), 400
        
        # Get response
        try:
            result = response.json()
        except ValueError:
            result = {'raw_text': response.text}
        
        # Return success or error based on status code
        if response.status_code < 400:
            return jsonify({
                'success': True,
                'status_code': response.status_code,
                'result': result,
                'headers': dict(response.headers)
            }), 200
        else:
            return jsonify({
                'success': False,
                'status_code': response.status_code,
                'error': result.get('message', 'Error en la petición'),
                'result': result
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        logger.error(f'Request error: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error de conexión: {str(e)}',
            'status_code': 500
        }), 500
    except Exception as e:
        logger.error(f'Unexpected error: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error inesperado: {str(e)}',
            'status_code': 500
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f'Starting Notion API Query Tester on port {port}')
    logger.info('Make sure NOTION_API_KEY is set in your environment variables')
    app.run(host='0.0.0.0', port=port, debug=True)

