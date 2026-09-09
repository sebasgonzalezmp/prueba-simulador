import json
import os
import random
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from google import genai

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA WEB
# ==========================================
st.set_page_config(
    page_title="Plataforma BPO Multichat",
    page_icon="🌐",
    layout="wide"
)

# ==========================================
# BASE DE DATOS Y PERSISTENCIA
# ==========================================
ARCHIVO_HISTORIAL = "historial.json"

ESCENARIOS_PARTNER = {
    "Orden Demorada": "El rider asignado lleva 40 minutos de retraso y la comida del partner se está enfriando.",
    "Falta de Producto / Stock": "El partner aceptó la orden pero no tiene un insumo clave para la preparación.",
    "Cobro Incorrecto": "El partner afirma que en la última liquidación le descontaron una comisión errónea.",
    "Local Cerrado": "El partner requiere apagar la app de inmediato por una emergencia en cocina."
}

RESPUESTAS_RESPALDO_PARTNER = [
    "¡Sigo esperando una solución concreta! La orden no puede quedarse así.",
    "Necesito que aceleren el proceso o me asignen una solución de inmediato.",
    "Por favor verifica bien en el sistema, no puedo perder más tiempo.",
    "De acuerdo, pero confírmame el procedimiento exacto antes de finalizar."
]

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    return []

def guardar_registro(registro):
    historial = cargar_historial()
    historial.append(registro)
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as archivo:
        json.dump(historial, archivo, indent=4, ensure_ascii=False)

def emitir_alerta_sonora():
    """Genera un tono suave tipo 'ping' usando la Web Audio API nativa del navegador"""
    js_sound = """
    <script>
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // Tono D5 suave
    gain.gain.setValueAtTime(0.05, ctx.currentTime); // Volumen bajo (5%)
    gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 0.5);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.5);
    </script>
    """
    components.html(js_sound, height=0, width=0)

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.title("⚙️ Configuración BPO")
agente_activo = st.sidebar.text_input("Nombre del Agente", value="Sebastián")
api_key_input = st.sidebar.text_input("Google AI API Key", type="password", help="Obtén tu clave en Google AI Studio")

st.sidebar.markdown("---")
st.sidebar.title("📌 Navegación")
menu_principal = st.sidebar.radio("Ir a:", options=["🛠️ Herramienta Operativa (Multichat)", "📊 Panel Supervisor"])

# ==========================================
# SECCIÓN 1: HERRAMIENTA OPERATIVA (MULTICHAT)
# ==========================================
if menu_principal == "🛠️ Herramienta Operativa (Multichat)":
    st.title("🌐 Plataforma de Gestión BPO")
    modo = st.radio("Interruptor de Modo:", options=["🧠 ENTRENAMIENTO MULTICHAT (3 CHATS)", "🤝 APOYO EN VIVO"], horizontal=True)
    st.markdown("---")

    if modo == "🧠 ENTRENAMIENTO MULTICHAT (3 CHATS)":
        st.header("🧠 Simulación Multitarea: 3 Chats de Partners en Paralelo")
        
        # Inicialización de estado para los 3 chats
        if "chats" not in st.session_state:
            st.session_state.chats = {
                "Chat 1": {"escenario": "Orden Demorada", "mensajes": [], "inicio": datetime.now(), "ultimo_msg_partner": datetime.now()},
                "Chat 2": {"escenario": "Falta de Producto / Stock", "mensajes": [], "inicio": datetime.now(), "ultimo_msg_partner": datetime.now()},
                "Chat 3": {"escenario": "Cobro Incorrecto", "mensajes": [], "inicio": datetime.now(), "ultimo_msg_partner": datetime.now()}
            }

        tabs = st.tabs(["💬 Chat 1 - Orden Demorada", "💬 Chat 2 - Falta de Stock", "💬 Chat 3 - Cobro Incorrecto"])

        for i, tab_name in enumerate(["Chat 1", "Chat 2", "Chat 3"]):
            with tabs[i]:
                chat_data = st.session_state.chats[tab_name]
                
                # Inicializar primer mensaje si está vacío
                if not chat_data["mensajes"]:
                    desc = ESCENARIOS_PARTNER[chat_data["escenario"]]
                    chat_data["mensajes"].append({"role": "assistant", "content": f"¡Hola! Hablas con el Restaurante. {desc}"})

                # Calcular métricas de tiempo
                ahora = datetime.now()
                tiempo_tmr_sec = (ahora - chat_data["ultimo_msg_partner"]).total_seconds()
                tiempo_att_min = (ahora - chat_data["inicio"]).total_seconds() / 60

                # Indicadores visuales y sonoros por chat
                col_m1, col_m2 = st.columns(2)
                
                if tiempo_tmr_sec > 60:
                    col_m1.error(f"🚨 **ALERTA TMR Excedido:** {int(tiempo_tmr_sec)}s sin responder al Partner (> 60s)")
                    emitir_alerta_sonora()
                else:
                    col_m1.success(f"⏱️ **TMR Actual:** {int(tiempo_tmr_sec)}s / 60s max")

                if tiempo_att_min > 5.0:
                    col_m2.error(f"⚠️ **ALERTA ATT Excedido:** {tiempo_att_min:.1f} min de gestión (> 5.0 min)")
                    emitir_alerta_sonora()
                else:
                    col_m2.info(f"⏳ **ATT Total Chat:** {tiempo_att_min:.1f} min / 5.0 min max")

                # Mostrar historial del chat actual
                for msg in chat_data["mensajes"]:
                    if msg["role"] == "user":
                        st.chat_message("user").write(msg["content"])
                    else:
                        st.chat_message("assistant", avatar="🏪").write(msg["content"])

                # Entrada de texto para respuesta en este chat específico
                if resp_user := st.chat_input(f"Responder en {tab_name}...", key=f"input_{tab_name}"):
                    chat_data["mensajes"].append({"role": "user", "content": resp_user})
                    st.chat_message("user").write(resp_user)
                    
                    respuesta_generada = False
                    
                    if api_key_input:
                        with st.spinner("El Partner está respondiendo..."):
                            try:
                                client = genai.Client(api_key=api_key_input)
                                hist_text = "\n".join([f"{'Agente' if m['role']=='user' else 'Partner'}: {m['content']}" for m in chat_data["mensajes"]])
                                
                                prompt_partner = f"""
                                Eres el Administrador de un Restaurante Partner. Atiendes este caso: {chat_data['escenario']}.
                                HISTORIAL DE LA CONVERSACIÓN:
                                {hist_text}
                                Responde directo y exigenete en máximo 2 frases. NUNCA repitas frases anteriores.
                                """
                                response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_partner)
                                resp_partner = response.text.strip()
                                respuesta_generada = True
                            except Exception:
                                pass

                    if not respuesta_generada:
                        resp_partner = random.choice(RESPUESTAS_RESPALDO_PARTNER)

                    chat_data["mensajes"].append({"role": "assistant", "content": resp_partner})
                    chat_data["ultimo_msg_partner"] = datetime.now() # Reiniciar TMR
                    st.rerun()

                st.markdown("---")
                if st.button(f"🏁 Finalizar y Auditar {tab_name}", key=f"btn_{tab_name}", type="primary"):
                    if api_key_input and len(chat_data["mensajes"]) > 1:
                        with st.spinner("Auditando calidad del chat..."):
                            try:
                                client = genai.Client(api_key=api_key_input)
                                conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_data["mensajes"]])
                                prompt_qa = f"""
                                Evalúa esta atención BPO a Partner:
                                {conv_text}
                                Formato JSON estricto:
                                {{"psat_simulado": 85, "empatia": 80, "naturalidad": 85, "claridad": 90, "multitarea": 85, "fortalezas": "...", "oportunidades": "..."}}
                                """
                                res_qa = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_qa)
                                data_qa = json.loads(res_qa.text.strip().replace("```json", "").replace("```", ""))
                                
                                guardar_registro({
                                    "agente": agente_activo,
                                    "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "modo": "ENTRENAMIENTO",
                                    "escenario": f"{tab_name} - {chat_data['escenario']}",
                                    "psat_simulado": data_qa["psat_simulado"],
                                    "empatia": data_qa["empatia"],
                                    "naturalidad": data_qa["naturalidad"],
                                    "claridad": data_qa["claridad"],
                                    "multitarea": data_qa["multitarea"],
                                    "fortalezas": data_qa["fortalezas"],
                                    "oportunidades": data_qa["oportunidades"]
                                })
                                st.success("¡Auditoría QA guardada con éxito!")
                                st.json(data_qa)
                            except Exception as e:
                                st.error(f"Error QA: {e}")

    else:
        st.header("🤝 Modo Apoyo en Vivo con IA")
        cat_p = st.selectbox("Categoría de Incidente Partner:", options=list(ESCENARIOS_PARTNER.keys()))
        msg_p = st.text_input("Mensaje recibido del Partner:", placeholder="Ejemplo: Llevo 30 minutos esperando al rider.")
        
        if st.button("Obtener Respuesta Recomendada", type="primary"):
            if api_key_input and msg_p.strip():
                try:
                    client = genai.Client(api_key=api_key_input)
                    prompt_ap = f"Genera respuesta corta para Partner. Caso: {cat_p}. Mensaje: '{msg_p}'. Formato JSON: {{\"respuesta\": \"...\", \"tip\": \"...\"}}"
                    res_ap = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_ap)
                    data_ap = json.loads(res_ap.text.strip().replace("```json", "").replace("```", ""))
                    st.code(data_ap["respuesta"], language=None)
                    st.warning(f"📌 **Tip:** {data_ap['tip']}")
                    guardar_registro({"agente": agente_activo, "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M"), "modo": "APOYO", "categoria_problema": cat_p})
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# SECCIÓN 2: PANEL DE SUPERVISOR / REPORTES
# ==========================================
else:
    st.title("📊 Panel de Seguimiento y Supervisión BPO")
    historial = cargar_historial()
    
    if historial:
        entrenamientos = [r for r in historial if r.get("modo") == "ENTRENAMIENTO"]
        if entrenamientos:
            st.subheader("📋 Registro de Auditorías Multichat")
            df = pd.DataFrame(entrenamientos)
            df_tabla = df[["fecha_hora", "agente", "escenario", "psat_simulado", "empatia", "multitarea", "fortalezas", "oportunidades"]]
            st.dataframe(df_tabla.tail(10), use_container_width=True)