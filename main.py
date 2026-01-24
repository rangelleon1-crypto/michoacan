from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

@app.route('/consultar', methods=['GET', 'POST'])
def api_consultar():
    # Obtener parámetros
    if request.method == 'POST':
        data = request.get_json() or {}
        placa = data.get('placa', '').strip().upper()
        serie = data.get('serie', '').strip().upper()
    else:
        placa = request.args.get('placa', '').strip().upper()
        serie = request.args.get('serie', '').strip().upper()

    if not placa or not serie:
        return jsonify({"ok": False, "error": "Faltan parámetros"}), 400

    # USAR UNA SESIÓN PARA MANTENER COOKIES
    session = requests.Session()
    url = "https://refrendodigital.michoacan.gob.mx/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-419,es;q=0.9",
        "Origin": "https://refrendodigital.michoacan.gob.mx",
        "Referer": url
    }

    try:
        # 1. Primero visitamos la web para obtener la cookie de sesión inicial
        session.get(url, headers=headers, timeout=15)

        # 2. Enviamos los datos
        payload = {"placa": placa, "serie": serie, "token": "", "mos": "1"}
        
        # Enviamos como data (form-encoded) tal cual tu script funcional
        response = session.post(url, data=payload, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return jsonify({"ok": False, "error": f"Bloqueo del portal (Status {response.status_code})"}), 502

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verificación de datos
        datos = {}
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '').upper()
            td = th.find_next_sibling('td')
            if td:
                datos[label] = td.get_text(strip=True)

        total = None
        for b in soup.find_all('b'):
            if "TOTAL A PAGAR" in b.get_text().upper():
                total = b.get_text(strip=True).upper().replace("TOTAL A PAGAR", "").strip()
                break

        if not datos.get("NOMBRE") and not total:
            return jsonify({"ok": False, "error": "No se encontraron datos en la respuesta"}), 404

        return jsonify({
            "ok": True, 
            "data": {
                "Nombre": datos.get("NOMBRE"),
                "Placa": datos.get("PLACA", placa),
                "Serie": datos.get("SERIE", serie),
                "Modelo": datos.get("MODELO"),
                "Total": total
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
