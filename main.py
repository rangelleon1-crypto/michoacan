from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)

@app.route('/consultar', methods=['GET', 'POST'])
def api_consultar():
    # Obtener placa y serie (soporta navegador y post JSON)
    if request.method == 'POST':
        data = request.get_json() or {}
        placa = data.get('placa', '').strip().upper()
        serie = data.get('serie', '').strip().upper()
    else:
        placa = request.args.get('placa', '').strip().upper()
        serie = request.args.get('serie', '').strip().upper()

    if not placa or not serie:
        return jsonify({"ok": False, "error": "Faltan datos: placa y serie"}), 400

    url = "https://refrendodigital.michoacan.gob.mx/"
    
    # Payload exacto de tu script funcional
    payload = {
        "placa": placa,
        "serie": serie,
        "token": "",
        "mos": "1"
    }

    # Headers exactos de tu script funcional
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Origin": "https://refrendodigital.michoacan.gob.mx",
        "Referer": "https://refrendodigital.michoacan.gob.mx/",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # Realizar la petición POST
        response = requests.post(url, data=payload, headers=headers, timeout=25)
        
        if response.status_code != 200:
            return jsonify({"ok": False, "error": f"Error servidor Michoacán: {response.status_code}"}), 502

        soup = BeautifulSoup(response.text, 'html.parser')
        datos_extraidos = {}
        
        # Lógica de extracción de tu script
        for th in soup.find_all('th'):
            label = th.get_text(strip=True).replace(':', '')
            td = th.find_next_sibling('td')
            if td:
                datos_extraidos[label] = td.get_text(strip=True)

        total_pagar = None
        for b in soup.find_all('b'):
            texto_b = b.get_text(strip=True).upper()
            if "TOTAL A PAGAR" in texto_b:
                total_pagar = texto_b.replace("TOTAL A PAGAR", "").strip()
                break

        resultado = {
            "Nombre": datos_extraidos.get("Nombre") or datos_extraidos.get("NOMBRE"),
            "RFC": datos_extraidos.get("RFC"),
            "Placa": datos_extraidos.get("Placa") or datos_extraidos.get("PLACA") or placa,
            "Serie": datos_extraidos.get("Serie") or datos_extraidos.get("SERIE") or serie,
            "Modelo": datos_extraidos.get("Modelo") or datos_extraidos.get("MODELO"),
            "Marca": datos_extraidos.get("Marca") or datos_extraidos.get("MARCA"),
            "Tipo": datos_extraidos.get("Tipo") or datos_extraidos.get("TIPO"),
            "Total": total_pagar
        }

        if not any([resultado["Nombre"], resultado["Modelo"], resultado["Total"]]):
            return jsonify({"ok": False, "error": "No se encontraron datos. Verifica placa/serie."}), 404

        return jsonify({"ok": True, "data": resultado})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    # Importante para Railway: leer el puerto asignado
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
