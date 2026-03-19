import streamlit as st
import re

# Lista de municipios de Durango (para verificación opcional)
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
        partes = fecha_evento.split(' ')
        if len(partes) >= 2:
            datos['fecha'] = partes[0]
            datos['hora'] = partes[1]
        else:
            datos['fecha'] = fecha_evento
            datos['hora'] = ''
    else:
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
    desc_match = re.search(r'Descripción\s*Buscar\s*(.*?)(?=\n\s*Folio:|\Z)', bloque, re.DOTALL)
    if desc_match:
        bitacora = desc_match.group(1)
        lineas = bitacora.strip().split('\n')
        for linea in lineas:
            linea = linea.strip()
            if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*/\s*\w+\s*/', linea):
                # Eliminar el prefijo de timestamp y usuario
                linea_limpia = re.sub(r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*/\s*\w+\s*/\s*', '', linea)
                datos['reporte'] = linea_limpia.strip()
                break
        else:
            datos['reporte'] = ''
    else:
        datos['reporte'] = ''

    return datos

def limpiar_incidente(incidente):
    """Quita el número de catálogo del incidente."""
    return re.sub(r'^\d+\.\s*', '', incidente).strip()

def limpiar_ubicacion(ubicacion, municipio):
    """Limpia la ubicación para mostrarla sin coordenadas ni localidad redundante."""
    # Quitar LATITUD y LONGITUD
    ubicacion = re.sub(r'LATITUD:[-.\d]+\s+LONGITUD:[-.\d]+', '', ubicacion)
    ubicacion = re.sub(r'LATITUD:[-.\d]+', '', ubicacion)
    ubicacion = re.sub(r'LONGITUD:[-.\d]+', '', ubicacion)
    # Si el municipio es Durango, quitar "LOCALIDAD: VICTORIA DE DURANGO (CIUDAD)"
    if municipio.upper() == "DURANGO":
        ubicacion = re.sub(r'LOCALIDAD:\s*VICTORIA DE DURANGO\s*\(CIUDAD\)', '', ubicacion, flags=re.IGNORECASE)
    # Limpiar espacios múltiples
    ubicacion = re.sub(r'\s+', ' ', ubicacion).strip()
    return ubicacion

def formatear_reporte(datos):
    """Convierte los datos extraídos al formato deseado."""
    municipio = datos.get('municipio', '').upper()
    if municipio and municipio not in [m.upper() for m in MUNICIPIOS]:
        municipio += " (NO LISTADO)"

    fecha = datos.get('fecha', '').upper()
    hora = datos.get('hora', '').upper()
    folio = datos.get('folio', '').upper()
    incidente = limpiar_incidente(datos.get('motivo', '')).upper()
    telefono = datos.get('telefono', '').upper()
    ubicacion = limpiar_ubicacion(datos.get('direccion', ''), municipio).upper()
    reporte = datos.get('reporte', '').upper()
    maps = datos.get('maps_link', '')

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

# Configuración de la página sin título visible
st.set_page_config(page_title="Formateador 911", page_icon="📋")

# CSS para ocultar el botón de submit
st.markdown("""
<style>
    /* Oculta el botón de submit */
    div[data-testid="stFormSubmitButton"] > button {
        display: none;
    }
    /* Opcional: reducir espacio del formulario */
    .stForm {
        border: none !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Formulario con el área de texto (sin etiqueta) y botón oculto
with st.form("entrada_form"):
    texto_entrada = st.text_area(
        label="",  # Sin etiqueta
        placeholder="...",
        height=300,
        label_visibility="collapsed"
    )
    # Botón invisible que se activa con Ctrl+Enter
    procesado = st.form_submit_button("Procesar")

if procesado and texto_entrada.strip():
    # Dividir en reportes individuales por "Folio:"
    bloques = re.split(r'(?=Folio:)', texto_entrada)
    salida_total = ""
    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque:
            continue
        datos = extraer_reporte(bloque)
        if datos.get('folio'):
            salida_total += formatear_reporte(datos) + "\n\n"
        else:
            continue

    if salida_total:
        # Mostrar solo el resultado con botón de copiar nativo
        st.code(salida_total, language="text", line_numbers=False)
    else:
        st.text("No se pudo extraer ningún reporte. Revisa el formato.")
