from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
import warnings

# Suprimir advertencias SSL por el uso de verify=False
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)

# CONFIGURACIÓN DE CORS
CORS(app, resources={
    r"/consultar": {
        "origins": [
            "https://michoacan.gob-mx.org",
            "https://www.michoacan.gob-mx.org"
        ]
    }
})

def extraer_datos_robustos(html_text):
    """
    Usa la lógica de Regex del primer script para extraer datos limpios
    incluso si la estructura de la tabla falla.
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    texto_pagin = soup.get_text(" ", strip=True)

    # Regex para campos específicos
    nombre_match = re.search(r'Nombre\s*:\s*(.*?)(?=RFC)', texto_pagin, re.IGNORECASE)
    rfc_match = re.search(r'RFC\s*:\s*([A-Z0-9]{10,13})', texto_pagin, re.IGNORECASE)
    modelo_match = re.search(r'Modelo\s*:\s*(\d{4})', texto_pagin, re.IGNORECASE)
    marca_match = re.search(r'Marca\s*:\s*([A-Z\s\d]+?)(?=Tipo|Clase|Total|$)', texto_pagin, re.IGNORECASE)
    total_match = re.search(r'Total a pagar:?\s*\$\s*([\d,]+\.\d{2})', texto_pagin, re.IGNORECASE)

    return {
        "Nombre": nombre_match.group(1).strip() if nombre_match else None,
        "RFC": rfc_match.group(1).strip() if rfc_match else "N/D",
        "Modelo": modelo_match.group(1).strip() if modelo_match else None,
        "Marca": marca_match.group(1).strip() if marca_match else None,
        "Total": total_match.group(1) if total_match else "0.00"
    }

@app.route('/consultar', methods=['GET', 'POST'])
def api_consultar():
    # 1. Obtener parámetros (Soporta URL params y JSON/Form)
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        placa = data.get('placa', '').strip().upper()
        serie = data.get('serie', '').strip().upper()
    else:
        placa = request.args.get('placa', '').strip().upper()
        serie = request.args.get('serie', '').strip().upper()

    if not placa or not serie:
        return jsonify({"ok": False, "error": "Faltan parámetros (placa y serie)"}), 400

    # 2. Configuración de Proxy y Sesión
    proxy_url = "http://smart-acbga3s2e8o0_area-MX:VGp2kCrlWmUem0b0@proxy.smartproxy.net:3120"
    proxies = {"http": proxy_url, "https": proxy_url}
    url = "https://refrendodigital.michoacan.gob.mx/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": url,
        "Origin": url
    }

    session = requests.Session()
    session.proxies.update(proxies)

    try:
        # PASO A: Obtener el token CSRF inicial
        r_init = session.get(url, headers=headers, verify=False, timeout=15)
        soup_init = BeautifulSoup(r_init.text, 'html.parser')
        csrf_input = soup_init.find('input', {'id': 'token_csrf'})
        
        if not csrf_input:
            return jsonify({"ok": False, "error": "No se pudo obtener el token de seguridad"}), 502
        
        csrf_value = csrf_input.get('value')

        # PASO B: Realizar el POST con los datos
        # Nota: Usamos 'files' para emular el comportamiento del primer script (multipart/form-data)
        payload = {
            "csrf_token": (None, csrf_value),
            "placa": (None, placa),
            "serie": (None, serie),
            "token": (None, ""),
            "mos": (None, "1")
        }

        response = session.post(url, headers=headers, files=payload, verify=False, timeout=25)

        if response.status_code != 200:
            return jsonify({"ok": False, "error": f"Error externo: {response.status_code}"}), 502

        # PASO C: Extraer información
        datos_extraidos = extraer_datos_robustos(response.text)

        # Si no hay nombre ni total, probablemente los datos son incorrectos
        if not datos_extraidos["Nombre"] and datos_extraidos["Total"] == "0.00":
            return jsonify({"ok": False, "error": "Vehículo no encontrado. Verifique placa y serie."}), 404

        # 3. Respuesta Final
        return jsonify({
            "ok": True,
            "data": {
                "Nombre": datos_extraidos["Nombre"],
                "RFC": datos_extraidos["RFC"],
                "Placa": placa,
                "Serie": serie,
                "Modelo": datos_extraidos["Modelo"],
                "Marca": datos_extraidos["Marca"],
                "Tipo": "AUTO",
                "Total": datos_extraidos["Total"]
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Error interno: {str(e)}"}), 500

if __name__ == "__main__":
    # Compatible con despliegues en la nube (Render, Heroku, etc.)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
