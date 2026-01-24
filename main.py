from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.get_json()
    
    if not data or 'placa' not in data or 'serie' not in data:
        return jsonify({"ok": False, "error": "Faltan datos: placa y serie son requeridos"}), 400

    placa = data['placa'].upper().strip()
    serie = data['serie'].upper().strip()

    url = "https://refrendodigital.michoacan.gob.mx/"
    payload = {
        "placa": placa,
        "serie": serie,
        "token": "",
        "mos": "1"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://refrendodigital.michoacan.gob.mx",
        "Referer": "https://refrendodigital.michoacan.gob.mx/"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=25)
        if response.status_code != 200:
            return jsonify({"ok": False, "error": f"Error en servidor externo: {response.status_code}"}), 502
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer datos de la tabla th -> td
        datos_extraidos = {}
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '')
            td = th.find_next_sibling('td')
            if td:
                datos_extraidos[label.upper()] = td.get_text(strip=True)

        # Buscar el Total a Pagar
        total = None
        b_tags = soup.find_all('b')
        for b in b_tags:
            if "TOTAL A PAGAR" in b.get_text().upper():
                texto_total = b.get_text().upper().replace("TOTAL A PAGAR", "").strip()
                # Si no está directo, buscar con regex el signo de pesos
                match = re.search(r'\$\s*[\d,.]+', b.get_text())
                total = match.group(0) if match else texto_total

        resultado = {
            "Nombre": datos_extraidos.get("NOMBRE"),
            "RFC": datos_extraidos.get("RFC"),
            "Placa": datos_extraidos.get("PLACA", placa),
            "Serie": datos_extraidos.get("SERIE", serie),
            "Modelo": datos_extraidos.get("MODELO"),
            "Marca": datos_extraidos.get("MARCA"),
            "Tipo": datos_extraidos.get("TIPO"),
            "Total": total
        }

        # Validar si se obtuvo algo
        if not any([resultado["Nombre"], resultado["Modelo"], resultado["Total"]]):
            return jsonify({"ok": False, "error": "No se encontraron datos o placa inválida"}), 404

        return jsonify({"ok": True, "data": resultado})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    import os
    # Railway asigna un puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
