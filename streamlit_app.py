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
    mun_match = re.search(
        r'MUNICIPIO:\s*([A-Za-zÁÉÍÓÚÑ ]+?)(?=\s+(?:LATITUD|LONGITUD|DETALLE|PUNTO DE INTERÉS|$))',
        datos['direccion'],
        re.IGNORECASE
    )
    if mun_match:
        datos['municipio'] = mun_match.group(1).strip().upper()
    else:
        datos['municipio'] = ''

    # Extraer latitud y longitud
    lat_match = re.search(r'LATITUD:\s*([-\d.]+)', datos['direccion'], re.IGNORECASE)
    lon_match = re.search(r'LONGITUD:\s*([-\d.]+)', datos['direccion'], re.IGNORECASE)
    if lat_match and lon_match:
        lat = lat_match.group(1)
        lon = lon_match.group(1)
        datos['maps_link'] = f"https://www.google.com/maps?q={lat},{lon}"
    else:
        datos['maps_link'] = ''

    # Reporte (todas las líneas de bitácora después de "Descripción", limpias y filtradas)
    desc_match = re.search(r'Descripción\s*Buscar\s*(.*?)(?=\n\s*Folio:|\Z)', bloque, re.DOTALL)
    if desc_match:
        bitacora = desc_match.group(1)
        lineas = bitacora.strip().split('\n')
        lineas_limpias = []
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            # Eliminar timestamp y usuario (formato: DD/MM/AAAA HH:MM:SS / USUARIO / )
            linea_limpia = re.sub(r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*/\s*\w+\s*/\s*', '', linea)
            # Eliminar también posibles variantes con espacios extras
            linea_limpia = linea_limpia.strip()
            if not linea_limpia:
                continue
            # Filtrar líneas que no queremos (actualizaciones, cambios de folio, recurrentes)
            if re.search(r'\*\*ACTUALIZADO\*\*|LLAMADA RECURRENTE|HA CAMBIADO SU DETALLE', linea_limpia, re.IGNORECASE):
                continue
            # Si la línea contiene solo información de folio o cosas así, se puede excluir, pero mejor incluimos todo lo demás
            lineas_limpias.append(linea_limpia)
        # Unir todas las líneas relevantes con un separador (punto y coma o salto de línea)
        datos['reporte'] = ' | '.join(lineas_limpias) if lineas_limpias else ''
    else:
        datos['reporte'] = ''

    return datos

def limpiar_incidente(incidente):
    """Quita el número de catálogo del incidente."""
    return re.sub(r'^\d+\.\s*', '', incidente).strip()

def limpiar_ubicacion(ubicacion, municipio):
    """Limpia la ubicación para mostrarla sin coordenadas ni localidad redundante."""
    # Quitar LATITUD y LONGITUD
    ubicacion = re.sub(r'LATITUD:[-.\d]+\s+LONGITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)
    ubicacion = re.sub(r'LATITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)
    ubicacion = re.sub(r'LONGITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)
    
    # Si el municipio es Durango, quitar "LOCALIDAD: VICTORIA DE DURANGO (CIUDAD)"
    if municipio.upper() == "DURANGO":
        ubicacion = re.sub(
            r'LOCALIDAD:\s*VICTORIA DE DURANGO\s*\(CIUDAD\)',
            '',
            ubicacion,
            flags=re.IGNORECASE
        )
    
    # Quitar "MUNICIPIO: XXXXX" porque ya se muestra en el campo aparte
    patron_municipio = r'MUNICIPIO:\s*' + re.escape(municipio.upper())
    ubicacion = re.sub(patron_municipio, '', ubicacion, flags=re.IGNORECASE)
    
    # Limpiar espacios múltiples y comas sobrantes
    ubicacion = re.sub(r'\s+', ' ', ubicacion).strip()
    ubicacion = ubicacion.strip(', ')
    return ubicacion

def formatear_reporte(datos):
    """Convierte los datos extraídos al formato deseado."""
    municipio = datos.get('municipio', '').upper()
    if municipio and municipio not in [m.upper() for m in MUNICIPIOS]:
        municipio += " (NO LISTADO)"

    fecha = datos.get('fecha', '').upper()
    hora = datos.get('hora', '').upper()
    if hora and len(hora) >= 8 and hora[2] == ':' and hora[5] == ':':
        hora = hora[:5]
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

# Inicializar estado de sesión
if "texto_entrada" not in st.session_state:
    st.session_state.texto_entrada = ""
if "salida" not in st.session_state:
    st.session_state.salida = ""

# Configuración de la página
st.set_page_config(page_title="...", page_icon="")

# CSS para ocultar el botón de submit y dar estilo
st.markdown("""
<style>
    div[data-testid="stFormSubmitButton"] > button {
        display: none;
    }
    .stForm {
        border: none !important;
        padding: 0 !important;
    }
    div.stButton > button {
        background: none;
        border: none;
        color: gray;
        font-size: 1rem;
        padding: 0;
        margin: 0;
    }
    div.stButton > button:hover {
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# Formulario de entrada (solo el textarea)
with st.form("entrada_form"):
    texto_entrada = st.text_area(
        label="",
        placeholder="...",
        height=300,
        value=st.session_state.texto_entrada,
        label_visibility="collapsed"
    )
    procesado = st.form_submit_button("Procesar")

# Procesar si se presionó Ctrl+Enter
if procesado and texto_entrada.strip():
    st.session_state.texto_entrada = texto_entrada
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
    st.session_state.salida = salida_total if salida_total else "No se pudo extraer ningún reporte. Revisa el formato."
    st.rerun()

# Mostrar el área de resultado
st.markdown("---")
if st.session_state.salida:
    st.code(st.session_state.salida, language="text", line_numbers=False)
else:
    st.info("...")

# Botón de reinicio debajo de la segunda ventana
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("..."):
        st.session_state.texto_entrada = ""
        st.session_state.salida = ""
        st.rerun()
