from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

# IMPORTANTE: Añadimos 'GET' para que funcione en el navegador
@app.route('/consultar', methods=['GET', 'POST'])
def consultar():
    # Obtener placa y serie de la URL (navegador) o de un JSON
    if request.method == 'POST':
        data = request.get_json() or {}
        placa = data.get('placa', '').upper().strip()
        serie = data.get('serie', '').upper().strip()
    else:
        placa = request.args.get('placa', '').upper().strip()
        serie = request.args.get('serie', '').upper().strip()
    
    if not placa or not serie:
        return jsonify({"ok": False, "error": "Faltan parámetros: placa y serie"}), 400

    url = "https://refrendodigital.michoacan.gob.mx/"
    payload = {"placa": placa, "serie": serie, "token": "", "mos": "1"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": url
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        datos = {}
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '').upper()
            td = th.find_next_sibling('td')
            if td:
                datos[label] = td.get_text(strip=True)

        total = None
        for b in soup.find_all('b'):
            if "TOTAL A PAGAR" in b.get_text().upper():
                match = re.search(r'\$\s*[\d,.]+', b.get_text())
                total = match.group(0) if match else b.get_text().strip()

        if not datos.get("NOMBRE") and not total:
            return jsonify({"ok": False, "error": "No se encontraron datos"}), 404

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
