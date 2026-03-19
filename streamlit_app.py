import streamlit as st
import re

# Lista de municipios de Durango
MUNICIPIOS = [
    "Canatlán", "Canelas", "Coneto de Comonfort", "Cuencamé", "Durango",
    "General Simón Bolívar", "Gómez Palacio", "Guadalupe Victoria", "Guanaceví",
    "Hidalgo", "Indé", "Lerdo", "Mapimí", "Mezquital", "Nazas", "Nombre de Dios",
    "Ocampo", "El Oro", "Otáez", "Pánuco de Coronado", "Peñón Blanco", "Poanas",
    "Pueblo Nuevo", "Rodeo", "San Bernardo", "San Dimas", "San Juan de Guadalupe",
    "San Juan del Río", "San Luis del Cordero", "San Pedro del Gallo", "Santa Clara",
    "Santiago Papasquiaro", "Súchil", "Tamazula", "Tepehuanes", "Tlahualilo",
    "Topia", "Vicente Guerrero", "Nuevo Ideal"
]

def extraer_reporte(bloque):
    """Extrae los campos de un bloque de reporte individual."""
    datos = {}

    # Folio
    folio_match = re.search(r'Folio:\s*(.+)', bloque)
    datos['folio'] = folio_match.group(1).strip() if folio_match else ''

    # Fecha Inicio (por si acaso)
    fecha_inicio_match = re.search(r'Fecha Inicio:\s*(.+)', bloque)
    if fecha_inicio_match:
        datos['fecha_inicio'] = fecha_inicio_match.group(1).strip()

    # Teléfono
    tel_match = re.search(r'Teléfono:\s*(.+)', bloque)
    datos['telefono'] = tel_match.group(1).strip() if tel_match else 'NO PROPORCIONADO'

    # Fecha evento
    fecha_evento_match = re.search(r'Fecha evento:\s*(.+)', bloque)
    if fecha_evento_match:
        fecha_evento = fecha_evento_match.group(1).strip()
        # Separar fecha y hora
        partes = fecha_evento.split(' ')
        if len(partes) >= 2:
            datos['fecha'] = partes[0]
            datos['hora'] = partes[1]
        else:
            datos['fecha'] = fecha_evento
            datos['hora'] = ''
    else:
        # Si no hay fecha evento, usar fecha inicio
        if 'fecha_inicio' in datos:
            partes = datos['fecha_inicio'].split(' ')
            datos['fecha'] = partes[0] if len(partes) >= 1 else ''
            datos['hora'] = partes[1] if len(partes) >= 2 else ''
        else:
            datos['fecha'] = ''
            datos['hora'] = ''

    # Motivo
    motivo_match = re.search(r'Motivo\s*(.*?)(?=\n\s*Dirección)', bloque, re.DOTALL)
    if motivo_match:
        datos['motivo'] = motivo_match.group(1).strip().replace('\n', ' ').replace('\r', '')
    else:
        datos['motivo'] = ''

    # Dirección
    direccion_match = re.search(r'Dirección\s*(.*?)(?=\n\s*Escriba aquí|\n\s*INSTITUCIÓN:)', bloque, re.DOTALL)
    if direccion_match:
        direccion = direccion_match.group(1).strip()
        # Limpiar saltos de línea y espacios extras
        direccion = ' '.join(direccion.split())
        datos['direccion'] = direccion
    else:
        datos['direccion'] = ''

    # Extraer municipio de la dirección (MUNICIPIO:XXXX)
    mun_match = re.search(r'MUNICIPIO:\s*([A-Za-zÁÉÍÓÚÑ ]+?)(?=\s+LATITUD|\s+LONGITUD|\s+$|\s+DETALLE)', datos['direccion'])
    if mun_match:
        datos['municipio'] = mun_match.group(1).strip().upper()
    else:
        datos['municipio'] = ''

    # Extraer latitud y longitud
    lat_match = re.search(r'LATITUD:\s*([-\d.]+)', datos['direccion'])
    lon_match = re.search(r'LONGITUD:\s*([-\d.]+)', datos['direccion'])
    if lat_match and lon_match:
        lat = lat_match.group(1)
        lon = lon_match.group(1)
        datos['maps_link'] = f"https://www.google.com/maps?q={lat},{lon}"
    else:
        datos['maps_link'] = ''

    # Reporte (primera línea de bitácora después de "Descripción")
    # Buscamos el bloque de Descripción y tomamos la primera línea que tenga timestamp
    desc_match = re.search(r'Descripción\s*Buscar\s*(.*?)(?=\n\s*Folio:|\Z)', bloque, re.DOTALL)
    if desc_match:
        bitacora = desc_match.group(1)
        # Buscar primera línea con formato de timestamp
        lineas = bitacora.strip().split('\n')
        for linea in lineas:
            linea = linea.strip()
            if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*/\s*\w+\s*/', linea):
                # Extraer texto después de la segunda barra
                partes = linea.split('/')
                if len(partes) >= 3:
                    texto = '/'.join(partes[2:]).strip()
                    datos['reporte'] = texto
                else:
                    datos['reporte'] = linea
                break
        else:
            datos['reporte'] = ''
    else:
        datos['reporte'] = ''

    return datos

def formatear_reporte(datos):
    """Convierte los datos extraídos al formato deseado."""
    municipio = datos.get('municipio', '').upper()
    # Verificar si el municipio está en la lista (opcional)
    if municipio and municipio not in [m.upper() for m in MUNICIPIOS]:
        municipio += " (NO LISTADO)"

    fecha = datos.get('fecha', '').upper()
    hora = datos.get('hora', '').upper()
    folio = datos.get('folio', '').upper()
    incidente = datos.get('motivo', '').upper()
    telefono = datos.get('telefono', '').upper()
    ubicacion = datos.get('direccion', '').upper()
    reporte = datos.get('reporte', '').upper()
    maps = datos.get('maps_link', '')

    # Construir salida
    salida = f"""*MUNICIPIO*: {municipio}
*FECHA*: {fecha}
*HORA*: {hora}
*FOLIO*: {folio}
*INCIDENTE*: {incidente}
*TELÉFONO*: {telefono}
*UBICACIÓN*: {ubicacion}
*REPORTE A TRAVÉS DEL 9-1-1*: {reporte}

*UBICACIÓN EN GOOGLE MAPS*: {maps}
"""
    return salida

# Interfaz Streamlit
st.set_page_config(page_title="Formateador de Reportes 9-1-1")
st.title("Formateador de Reportes 9-1-1 para WhatsApp")

texto_entrada = st.text_area("Pega aquí los reportes completos (desde 'Folio:' hasta el final):", height=300)

if st.button("Procesar"):
    if not texto_entrada.strip():
        st.warning("Pega algún texto.")
    else:
        # Dividir en reportes individuales por "Folio:"
        bloques = re.split(r'(?=Folio:)', texto_entrada)
        salida_total = ""
        for bloque in bloques:
            bloque = bloque.strip()
            if not bloque:
                continue
            datos = extraer_reporte(bloque)
            if datos.get('folio'):  # si se encontró un folio
                salida_total += formatear_reporte(datos) + "\n---\n\n"
            else:
                # Posiblemente texto basura
                continue

        if salida_total:
            st.markdown("### Resultado (copiar y pegar en WhatsApp)")
            st.text_area("Salida", salida_total, height=400)
            st.info("Los campos se han puesto en mayúsculas. Verifica que la información sea correcta.")
        else:
            st.error("No se pudo extraer ningún reporte. Revisa el formato.")
