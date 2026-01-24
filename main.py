from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

@app.route('/consultar', methods=['GET', 'POST'])
def consultar():
    # 1. Obtener parámetros
    if request.method == 'POST':
        data = request.get_json() or {}
        placa = data.get('placa', '').upper().strip()
        serie = data.get('serie', '').upper().strip()
    else:
        placa = request.args.get('placa', '').upper().strip()
        serie = request.args.get('serie', '').upper().strip()
    
    if not placa or not serie:
        return jsonify({"ok": False, "error": "Faltan placa o serie"}), 400

    # 2. Configurar la sesión para manejar Cookies (PHPSESSID)
    session = requests.Session()
    base_url = "https://refrendodigital.michoacan.gob.mx/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": base_url,
        "Origin": "https://refrendodigital.michoacan.gob.mx"
    }

    try:
        # Paso A: Visitar la página inicial para obtener Cookies
        session.get(base_url, headers=headers, timeout=15)

        # Paso B: Enviar el POST como multipart/form-data
        # Al pasar un diccionario al parámetro 'files', requests lo envía como multipart
        form_data = {
            "placa": (None, placa),
            "serie": (None, serie),
            "token": (None, ""),
            "mos": (None, "1")
        }

        response = session.post(base_url, files=form_data, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return jsonify({"ok": False, "error": f"Error portal: {response.status_code}"}), 502

        # 3. Parsear la respuesta
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Verificar si hay error en el HTML (ej. mensaje de "No encontrado")
        if "No se encontraron datos" in soup.get_text() or "error" in soup.get_text().lower():
             return jsonify({"ok": False, "error": "Vehículo no encontrado o datos incorrectos en el portal"}), 404

        datos_finales = {}
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '').upper()
            td = th.find_next_sibling('td')
            if td:
                datos_finales[label] = td.get_text(strip=True)

        # Extraer el Total
        total = None
        for b in soup.find_all('b'):
            texto_b = b.get_text().upper()
            if "TOTAL A PAGAR" in texto_b:
                match = re.search(r'\$\s*[\d,.]+', b.get_text())
                total = match.group(0) if match else b.get_text().strip()

        # Si no hay nombre, algo salió mal en el scrapeo
        if not datos_finales.get("NOMBRE"):
             return jsonify({"ok": False, "error": "No se pudo extraer la información. Estructura HTML cambió."}), 404

        return jsonify({
            "ok": True,
            "data": {
                "Nombre": datos_finales.get("NOMBRE"),
                "Placa": datos_finales.get("PLACA", placa),
                "Serie": datos_finales.get("SERIE", serie),
                "Modelo": datos_finales.get("MODELO"),
                "Marca": datos_finales.get("MARCA"),
                "Total": total
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Usar el puerto que Railway asigne
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
