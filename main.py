import requests
import json
import time
import os
from fastapi import FastAPI
from apify_client import ApifyClient

app = FastAPI()

# Configuración (Railway tomará estas de las variables de entorno)
MY_TOKEN = os.getenv("APIFY_TOKEN", "tu_token_aqui")

def obtener_datos(placa):
    url = "https://tenencia.edomex.gob.mx/TenenciaIndividual/tenencia/calculaTenencia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tenencia.edomex.gob.mx",
    }
    try:
        response = requests.post(url, files={'placa': (None, placa)}, headers=headers, timeout=15)
        return response.json()
    except:
        return None

def disparar_apify(linea):
    if not linea or linea == "N/A": return
    nueve_digitos = linea[10:19]
    client = ApifyClient(MY_TOKEN)
    target_url = f"https://sfpya.edomexico.gob.mx/bancos/bbvabancomer.jsp?HdClaveOperacionServ={nueve_digitos}&HdOrigen=1&HdTipoPago=01&HdTipoEnvio=2&HdTipoImpuesto=3"
    
    run_input = {
        "startUrls": [{"url": target_url}],
        "waitUntil": ["domcontentloaded"],
        "maxPagesPerCrawl": 1,
        "pageFunction": "async function pageFunction(context) { return { status: 'ok' }; }"
    }
    client.actor("apify/puppeteer-scraper").start(run_input=run_input)

@app.get("/consultar/{placa}")
def consultar_placa(placa: str):
    # 1. Primera consulta
    data_1 = obtener_datos(placa)
    if not data_1:
        return {"error": "No se pudo conectar con el Edomex"}
    
    linea = data_1.get("linea", "N/A")
    
    # 2. Si hay línea, disparar Apify y esperar
    if linea and linea != "N/A":
        disparar_apify(linea)
        time.sleep(5) # Pausa para que el servidor registre
        # 3. Consulta final
        data_final = obtener_datos(placa)
    else:
        data_final = data_1

    # Extraer info técnica para el reporte final limpio
    info_vehiculo = {}
    if "tenencia" in data_final:
        val = data_final["tenencia"]
        info_vehiculo = json.loads(val) if isinstance(val, str) else val

    # Estructura de respuesta limpia
    return {
        "Placa": info_vehiculo.get("placa", placa),
        "Modelo": info_vehiculo.get("modeloVehi", "N/A"),
        "Vehículo": info_vehiculo.get("vehiculo", "N/A"),
        "Clave Vehicular": info_vehiculo.get("claveVehicular", {}).get("claveVehicular") if isinstance(info_vehiculo.get("claveVehicular"), dict) else "N/A",
        "Capacidad Carga": info_vehiculo.get("capacidadCarga", "N/A"),
        "Fecha Factura": info_vehiculo.get("fechaFacturaFormat", "N/A"),
        "Importe Factura": info_vehiculo.get("importeFacturaFormat", "N/A"),
        "Cilindros": info_vehiculo.get("numCilindros", "N/A"),
        "CC Moto": info_vehiculo.get("ccMoto", "N/A"),
        "Linea Captura": data_final.get("linea", "N/A"),
        "Importe Maximo": info_vehiculo.get("totalString", "N/A")
    }
