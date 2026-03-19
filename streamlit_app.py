import streamlit as st
import re

# ========== CONSTANTES ==========
MUNICIPIOS = {
    m.upper() for m in [
        "Canatlán", "Canelas", "Coneto de Comonfort", "Cuencamé", "Durango",
        "General Simón Bolívar", "Gómez Palacio", "Guadalupe Victoria", "Guanaceví",
        "Hidalgo", "Indé", "Lerdo", "Mapimí", "Mezquital", "Nazas", "Nombre de Dios",
        "Ocampo", "El Oro", "Otáez", "Pánuco de Coronado", "Peñón Blanco", "Poanas",
        "Pueblo Nuevo", "Rodeo", "San Bernardo", "San Dimas", "San Juan de Guadalupe",
        "San Juan del Río", "San Luis del Cordero", "San Pedro del Gallo", "Santa Clara",
        "Santiago Papasquiaro", "Súchil", "Tamazula", "Tepehuanes", "Tlahualilo",
        "Topia", "Vicente Guerrero", "Nuevo Ideal"
    ]
}

# Patrones compilados
PATRON_FOLIO = re.compile(r'Folio:\s*(.+)')
PATRON_FECHA_INICIO = re.compile(r'Fecha Inicio:\s*(.+)')
PATRON_TELEFONO = re.compile(r'Teléfono:\s*(.+)')
PATRON_FECHA_EVENTO = re.compile(r'Fecha evento:\s*(.+)')
PATRON_MOTIVO = re.compile(r'Motivo\s*(.*?)(?=\n\s*Dirección)', re.DOTALL)
PATRON_DIRECCION = re.compile(r'Dirección\s*(.*?)(?=\n\s*Escriba aquí|\n\s*INSTITUCIÓN:)', re.DOTALL)
PATRON_MUNICIPIO = re.compile(r'MUNICIPIO:\s*([A-Za-zÁÉÍÓÚÑ ]+?)(?=\s+(?:LATITUD|LONGITUD|DETALLE|PUNTO DE INTERÉS|$))', re.IGNORECASE)
PATRON_LAT = re.compile(r'LATITUD:\s*([-\d.]+)', re.IGNORECASE)
PATRON_LON = re.compile(r'LONGITUD:\s*([-\d.]+)', re.IGNORECASE)
PATRON_BITACORA = re.compile(r'Descripción\s*Buscar\s*(.*?)(?=\n\s*Folio:|\Z)', re.DOTALL)
PATRON_TIMESTAMP = re.compile(r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*/\s*\w+\s*/\s*')
PATRON_FILTRAR = re.compile(r'\*\*ACTUALIZADO\*\*|LLAMADA RECURRENTE|HA CAMBIADO SU DETALLE', re.IGNORECASE)

# ========== FUNCIONES DE EXTRACCIÓN ==========
def extraer_reporte(bloque):
    """Extrae los campos de un bloque de reporte individual."""
    datos = {}

    # Folio
    if m := PATRON_FOLIO.search(bloque):
        datos['folio'] = m.group(1).strip()

    # Fecha Inicio (respaldo)
    fecha_inicio = None
    if m := PATRON_FECHA_INICIO.search(bloque):
        fecha_inicio = m.group(1).strip()

    # Teléfono
    if m := PATRON_TELEFONO.search(bloque):
        datos['telefono'] = m.group(1).strip()
    else:
        datos['telefono'] = 'NO PROPORCIONADO'

    # Fecha evento (principal)
    if m := PATRON_FECHA_EVENTO.search(bloque):
        fecha_evento = m.group(1).strip()
        partes = fecha_evento.split()
        datos['fecha'] = partes[0] if len(partes) > 0 else ''
        datos['hora'] = partes[1] if len(partes) > 1 else ''
    elif fecha_inicio:
        partes = fecha_inicio.split()
        datos['fecha'] = partes[0] if len(partes) > 0 else ''
        datos['hora'] = partes[1] if len(partes) > 1 else ''
    else:
        datos['fecha'] = datos['hora'] = ''

    # Motivo
    if m := PATRON_MOTIVO.search(bloque):
        datos['motivo'] = ' '.join(m.group(1).strip().split())
    else:
        datos['motivo'] = ''

    # Dirección
    if m := PATRON_DIRECCION.search(bloque):
        datos['direccion'] = ' '.join(m.group(1).strip().split())
    else:
        datos['direccion'] = ''

    # Municipio
    if m := PATRON_MUNICIPIO.search(datos['direccion']):
        datos['municipio'] = m.group(1).strip().upper()
    else:
        datos['municipio'] = ''

    # Coordenadas y link de Maps
    lat = PATRON_LAT.search(datos['direccion'])
    lon = PATRON_LON.search(datos['direccion'])
    if lat and lon:
        datos['maps_link'] = f"https://www.google.com/maps?q={lat.group(1)},{lon.group(1)}"
    else:
        datos['maps_link'] = ''

    # Bitácora (reporte)
    if m := PATRON_BITACORA.search(bloque):
        lineas = m.group(1).strip().split('\n')
        lineas_limpias = []
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            # Quitar timestamp y usuario
            linea_limpia = PATRON_TIMESTAMP.sub('', linea).strip()
            if not linea_limpia:
                continue
            # Filtrar líneas no deseadas
            if PATRON_FILTRAR.search(linea_limpia):
                continue
            lineas_limpias.append(linea_limpia)
        datos['reporte'] = ' | '.join(lineas_limpias) if lineas_limpias else ''
    else:
        datos['reporte'] = ''

    return datos

# ========== FUNCIONES DE LIMPIEZA ==========
def limpiar_incidente(incidente):
    """Quita el número de catálogo del incidente."""
    return re.sub(r'^\d+\.\s*', '', incidente).strip()

def limpiar_ubicacion(ubicacion, municipio):
    """Limpia la ubicación: quita coordenadas y texto redundante."""
    # Eliminar coordenadas
    ubicacion = re.sub(r'LATITUD:[-.\d]+\s+LONGITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)
    ubicacion = re.sub(r'LATITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)
    ubicacion = re.sub(r'LONGITUD:[-.\d]+', '', ubicacion, flags=re.IGNORECASE)

    # Si es Durango, quitar localidad redundante
    if municipio.upper() == "DURANGO":
        ubicacion = re.sub(
            r'LOCALIDAD:\s*VICTORIA DE DURANGO\s*\(CIUDAD\)',
            '',
            ubicacion,
            flags=re.IGNORECASE
        )

    # Quitar "MUNICIPIO: NOMBRE" (ya se muestra aparte)
    ubicacion = re.sub(
        r'MUNICIPIO:\s*' + re.escape(municipio.upper()),
        '',
        ubicacion,
        flags=re.IGNORECASE
    )

    # Limpiar espacios y comas sobrantes
    ubicacion = re.sub(r'\s+', ' ', ubicacion).strip().strip(', ')
    return ubicacion

def formatear_reporte(datos):
    """Construye el string final con el formato deseado."""
    municipio = datos.get('municipio', '').upper()
    if municipio and municipio not in MUNICIPIOS:
        municipio += " (NO LISTADO)"

    fecha = datos.get('fecha', '').upper()
    hora = datos.get('hora', '').upper()
    # Eliminar segundos si existen
    if hora and len(hora) >= 8 and hora[2] == ':' and hora[5] == ':':
        hora = hora[:5]

    folio = datos.get('folio', '').upper()
    incidente = limpiar_incidente(datos.get('motivo', '')).upper()
    telefono = datos.get('telefono', '').upper()
    ubicacion = limpiar_ubicacion(datos.get('direccion', ''), municipio).upper()
    reporte = datos.get('reporte', '').upper()
    maps = datos.get('maps_link', '')

    return f"""*MUNICIPIO*: {municipio}
*FECHA*: {fecha}
*HORA*: {hora}
*FOLIO*: {folio}
*INCIDENTE*: {incidente}
*TELÉFONO*: {telefono}
*UBICACIÓN*: {ubicacion}
*REPORTE A TRAVÉS DEL 9-1-1*: {reporte}

*UBICACIÓN EN GOOGLE MAPS*: {maps}
"""

# ========== INTERFAZ STREAMLIT ==========
st.set_page_config(page_title="...", page_icon="")

# Estado de sesión
if "texto_entrada" not in st.session_state:
    st.session_state.texto_entrada = ""
if "salida" not in st.session_state:
    st.session_state.salida = ""

# CSS para ocultar botón de submit, el mensaje de Ctrl+Enter y dar estilo
st.markdown("""
<style>
    div[data-testid="stFormSubmitButton"] > button {
        display: none;
    }
    .stForm {
        border: none !important;
        padding: 0 !important;
    }
    /* Ocultar el mensaje "Press Ctrl+Enter to submit" */
    div[data-testid="stForm"] div[data-baseweb="textarea"] + div {
        display: none !important;
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

# Formulario de entrada (Ctrl+Enter envía)
with st.form("entrada_form"):
    texto_entrada = st.text_area(
        label="",
        placeholder="...",
        height=150,
        value=st.session_state.texto_entrada,
        label_visibility="collapsed"
    )
    procesado = st.form_submit_button("Procesar")

# Procesar
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
    st.session_state.salida = salida_total or "No se pudo extraer ningún reporte. Revisa el formato."
    st.rerun()

# Mostrar resultado
st.markdown("---")
if st.session_state.salida:
    st.code(st.session_state.salida, language="text", line_numbers=False)
else:
    st.info("...")

# Botón de reinicio
col1, _, _ = st.columns([1, 1, 8])
with col1:
    if st.button("..."):
        st.session_state.texto_entrada = ""
        st.session_state.salida = ""
        st.rerun()
