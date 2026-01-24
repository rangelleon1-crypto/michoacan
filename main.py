from flask import Flask, request, jsonify
from flask_cors import CORS  # Importar CORS
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# CONFIGURACIÓN DE CORS
# Esto permite que solo tus dominios puedan consultar esta API
CORS(app, resources={
    r"/consultar": {
        "origins": [
            "https://michoacan.gob-mx.org",
            "https://www.michoacan.gob-mx.org"
        ]
    }
})

@app.route('/consultar', methods=['GET', 'POST'])
def api_consultar():
    # 1. Obtener parámetros
    if request.method == 'POST':
        # Soporte para JSON o Form Data
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
        return jsonify({"ok": False, "error": "Faltan parámetros"}), 400

    # 2. Configuración del Proxy
    proxy_url = "http://smart-acbga3s2e8o0_area-MX:VGp2kCrlWmUem0b0@proxy.smartproxy.net:3120"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    url = "https://refrendodigital.michoacan.gob.mx/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Origin": "https://refrendodigital.michoacan.gob.mx",
        "Referer": url
    }

    session = requests.Session()
    session.proxies.update(proxies) 

    try:
        # Paso A: Obtener sesión
        session.get(url, headers=headers, timeout=15)

        # Paso B: Consulta de datos
        payload = {
            "placa": placa,
            "serie": serie,
            "token": "",
            "mos": "1"
        }
        
        response = session.post(url, data=payload, headers=headers, timeout=25)
        
        if response.status_code != 200:
            return jsonify({
                "ok": False, 
                "error": f"Error del servidor externo (Status {response.status_code})"
            }), 502

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Procesar tablas
        datos = {}
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '').upper()
            td = th.find_next_sibling('td')
            if td:
                datos[label] = td.get_text(strip=True)

        # Procesar Total
        total = None
        for b in soup.find_all('b'):
            if "TOTAL A PAGAR" in b.get_text().upper():
                total = b.get_text(strip=True).upper().replace("TOTAL A PAGAR", "").strip()
                break

        if not datos.get("NOMBRE") and not total:
            return jsonify({"ok": False, "error": "Datos no encontrados. Revisa placa/serie."}), 404

        # Respuesta estructurada para tu HTML
        return jsonify({
            "ok": True,
            "data": {
                "Nombre": datos.get("NOMBRE"),
                "RFC": datos.get("RFC", "N/D"),
                "Placa": datos.get("PLACA", placa),
                "Serie": datos.get("SERIE", serie),
                "Modelo": datos.get("MODELO"),
                "Marca": datos.get("MARCA"),
                "Tipo": datos.get("TIPO", "PARTICULAR"),
                "Total": total
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Error de conexión: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
