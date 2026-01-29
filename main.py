import requests
import json
import time
import os
from fastapi import FastAPI
from apify_client import ApifyClient

app = FastAPI()

# Railway lee esto de la pestaña 'Variables'. Si no existe, usa tu token por defecto.
MY_TOKEN = os.getenv("APIFY_TOKEN", "apify_api_OwqaDMqG4TeoOeuGd7DVU9flKaRchO04LOKJ")

def realizar_peticion(placa):
    url = "https://tenencia.edomex.gob.mx/TenenciaIndividual/tenencia/calculaTenencia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tenencia.edomex.gob.mx",
    }
    try:
        # Enviamos la placa como multipart/form-data
        response = requests.post(url, files={'placa': (None, placa)}, headers=headers, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": f"Fallo de conexion: {str(e)}"}

@app.get("/")
def home():
    """Ruta para verificar que el servidor esta vivo"""
    return {
        "status": "Online",
        "mensaje": "Servidor de Tenencia Activo",
        "instrucciones": "Usa /consultar/TU_PLACA para obtener datos"
    }

@app.get("/consultar/{placa}")
def api_consultar(placa: str):
    # Aseguramos que la placa este en mayusculas
    placa = placa.upper()
    
    # 1. Primera consulta: Obtener Linea de Captura
    data_1 = realizar_peticion(placa)
    
    if not data_1 or "error" in data_1:
        return {"error": "No se pudo obtener respuesta del Edomex"}

    linea = data_1.get("linea", "N/A")

    # 2. Proceso Apify: Solo si hay una linea de captura valida
    if linea and linea != "N/A":
        client = ApifyClient(MY_TOKEN)
        # Extraemos digitos 11 al 19 (indice 10 al 19)
        nueve_digitos = linea[10:19]
        target_url = f"https://sfpya.edomexico.gob.mx/bancos/bbvabancomer.jsp?HdClaveOperacionServ={nueve_digitos}&HdOrigen=1&HdTipoPago=01&HdTipoEnvio=2&HdTipoImpuesto=3"
        
        run_input = {
            "startUrls": [{"url": target_url}],
            "waitUntil": ["domcontentloaded"],
            "maxPagesPerCrawl": 1,
            "pageFunction": "async function pageFunction(context) { return { status: 'ok' }; }"
        }
        
        # Disparo asincrono (sin esperar a que termine el navegador)
        try:
            client.actor("apify/puppeteer-scraper").start(run_input=run_input)
        except:
            pass # Si falla Apify, intentamos seguir
        
        # Espera de 5 segundos para que el sistema del gobierno procese el 'clic'
        time.sleep(5)
        
        # 3. Consulta final para traer la ficha tecnica completa
        data_final = realizar_peticion(placa)
    else:
        data_final = data_1

    # 4. Extraer el objeto 'tenencia' que viene como String en el JSON original
    info_interna = {}
    if "tenencia" in data_final:
        val = data_final["tenencia"]
        try:
            info_interna = json.loads(val) if isinstance(val, str) else val
        except:
            info_interna = {}

    # 5. Respuesta JSON final con tus etiquetas personalizadas
    return {
        "Placa": info_interna.get("placa", placa),
        "Modelo": info_interna.get("modeloVehi", "N/A"),
        "Vehiculo": info_interna.get("vehiculo", "N/A"),
        "Clave Vehicular": info_interna.get("claveVehicular", {}).get("claveVehicular") if isinstance(info_interna.get("claveVehicular"), dict) else "N/A",
        "Capacidad Carga": info_interna.get("capacidadCarga", "N/A"),
        "Fecha Factura": info_interna.get("fechaFacturaFormat", "N/A"),
        "Importe Factura": info_interna.get("importeFacturaFormat", "N/A"),
        "Cilindros": info_interna.get("numCilindros", "N/A"),
        "CC Moto": info_interna.get("ccMoto", "N/A"),
        "Linea_Captura": data_final.get("linea", "N/A"),
        "Importe_Maximo": info_interna.get("totalString", "N/A")
    }
