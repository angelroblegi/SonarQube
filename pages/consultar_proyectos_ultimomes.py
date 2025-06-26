import requests
import pandas as pd
from datetime import datetime
import time

# Configuración
TOKEN = 'squ_9d4bf55717f19e3c05a873b1f350b96c07a636a1'
BASE_URL = 'http://hiroshima04s:9000'
AUTH = (TOKEN, '')

def obtener_proyectos():
    proyectos = []
    page = 1
    while True:
        params = {'qualifiers': 'TRK', 'ps': 500, 'p': page}
        response = requests.get(f"{BASE_URL}/api/components/search", params=params, auth=AUTH)
        if response.status_code == 200:
            data = response.json()
            proyectos.extend([comp['key'] for comp in data['components']])
            if data['paging']['total'] > page * 500:
                page += 1
            else:
                break
        else:
            print(f"Error al obtener proyectos: {response.status_code}")
            break
    return proyectos

def obtener_new_lines_y_fecha(proyecto):
    try:
        # Obtener líneas nuevas
        params_metricas = {
            'component': proyecto,
            'metricKeys': 'new_lines'
        }
        r_metricas = requests.get(f"{BASE_URL}/api/measures/component", params=params_metricas, auth=AUTH)
        new_lines = 0
        if r_metricas.status_code == 200:
            data = r_metricas.json()
            for m in data['component'].get('measures', []):
                if m['metric'] == 'new_lines':
                    new_lines = int(float(m['value']))
        else:
            print(f"[!] Error en métricas de {proyecto}: {r_metricas.status_code}")

        if new_lines > 0:
            # Obtener fecha del último análisis
            params_analisis = {
                'project': proyecto,
                'ps': 1
            }
            r_analisis = requests.get(f"{BASE_URL}/api/project_analyses/search", params=params_analisis, auth=AUTH)
            fecha = ''
            if r_analisis.status_code == 200:
                analisis_data = r_analisis.json()
                if analisis_data['analyses']:
                    fecha = analisis_data['analyses'][0]['date']
                    fecha = datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M')
            else:
                print(f"[!] Error en análisis de {proyecto}: {r_analisis.status_code}")

            return {
                'Proyecto': proyecto,
                'Nuevas Lineas': new_lines,
                'Fecha Ultimo Codigo': fecha
            }

    except Exception as e:
        print(f"[!] Error en {proyecto}: {e}")
    return None

def main():
    proyectos = obtener_proyectos()
    print(f"Total de proyectos encontrados: {len(proyectos)}")

    resultados = []
    for p in proyectos:
        print(f"Consultando {p}...")
        datos = obtener_new_lines_y_fecha(p)
        if datos:
            resultados.append(datos)
        time.sleep(0.5)  # evitar sobrecarga del servidor

    if resultados:
        df = pd.DataFrame(resultados)
        nombre_archivo = f"proyectos_con_nuevo_codigo_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        df.to_excel(nombre_archivo, index=False)
        print(f"✅ Archivo generado: {nombre_archivo}")
    else:
        print("⚠️ No se encontraron proyectos con nuevo código.")

if __name__ == '__main__':
    main()
