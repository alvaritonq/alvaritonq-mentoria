#!/usr/bin/env python3
"""
Envío diario de los 3 reels del día — Telegram + Notion.

Lee la fecha actual (Lima time), mapea al día de la semana,
filtra los 3 reels correspondientes del plan 11-17 may 2026,
envía a Telegram un mensaje formateado por cada reel + crea
la entrada en la database "Ideas de Reels" de Notion.

Uso:
    # Dispara hoy (Lima time):
    python3 envio_reels_diarios.py

    # Dispara un día específico (para tests o reenviar):
    python3 envio_reels_diarios.py --dia lunes
    python3 envio_reels_diarios.py --dia 2026-05-12

Requisitos:
    Variables de entorno (configurar en Render env vars):
      NOTION_TOKEN
      NOTION_DB_IDEAS         (opcional, default ya seteado)
      TELEGRAM_BOT_TOKEN
      TELEGRAM_CHAT_ID
    NUNCA hardcodear tokens en el código — siempre vía env var.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────
# El token de Notion se lee de env var. NUNCA hardcodear.
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_IDEAS = os.environ.get("NOTION_DB_IDEAS", "35d20d07-51c9-819f-9f9d-d202c575611d")
NOTION_API = "https://api.notion.com/v1"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "")

LIMA_TZ = timezone(timedelta(hours=-5))

# Mapeo: lunes=0, martes=1, ..., domingo=6 (formato Python weekday())
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_NUM = {d: i for i, d in enumerate(DIAS_ES)}

# ─── 21 REELS — plan 11-17 may 2026 ───────────────────────────────────────
REELS = {
    "lunes": [
        {
            "id": "1.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "En un mundo donde todos venden cursos, yo solo tradeo",
            "hook_visual": "Cara cómplice + bowl encendido + LED neón + dashboard al lado",
            "texto_sobreimpreso": "en un mundo donde todos venden cursos · yo solo tradeo 🍃",
            "caption": "el mejor curso es el que no se vende. comentá 'sistema' y te paso el bootcamp.",
            "audio": "Beat lo-fi/trap suave, BPM 80-95",
            "duracion": "10-12 seg",
            "score": 90, "target_views": "80k-150k",
            "tips_grabacion": "Ojos medio cerrados, sin remera, sonrisa cómplice mínima. NO sonrisa grande. Vibe relax/elevado. El bowl se enciende EN cámara."
        },
        {
            "id": "1.2", "hora": "15:30", "tipo": "CONVERSIÓN",
            "concepto": "Lunes 9am: bowl + entrada. Lunes 11am: +$600",
            "hook_visual": "Split-screen vertical 50/50. Arriba cara/bowl/setup. Abajo screencast TradingView con entrada + take profit.",
            "texto_sobreimpreso": "9am 🍃 / 11am +$600",
            "caption": "no es suerte. es sistema. el bootcamp empieza el 18.",
            "audio": "Beat con drop sutil al ver el TP",
            "duracion": "12 seg",
            "score": 90, "target_views": "20k-40k",
            "tips_grabacion": "Grabá la cara arriba primero (12 seg), después screencast del trading abajo. Editás split en CapCut. EXACTO 50/50."
        },
        {
            "id": "1.3", "hora": "19:00", "tipo": "IDENTIDAD",
            "concepto": "8am 🛏 → 9am 🍃 → 10am 📈 → 11am 💵",
            "hook_visual": "4 frames cortos, transición seca. Cama → bowl → dashboard → fajo/payout screenshot",
            "texto_sobreimpreso": "8am 🛏 / 9am 🍃 / 10am 📈 / 11am 💵",
            "caption": "rutina simple. resultado simple.",
            "audio": "Trap minimalista, snares marcando cada corte",
            "duracion": "8 seg (4 frames x 2 seg)",
            "score": 78, "target_views": "8k-15k",
            "tips_grabacion": "Grabar cada frame por separado, ediciones rápidas con corte en seco. NO usar transiciones fancy de CapCut."
        },
    ],
    "martes": [
        {
            "id": "2.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "Me decían que iba a terminar siendo un huevoncio en la calle",
            "hook_visual": "Cara directa con diplomas en la pared del fondo + LED gaming + bowl",
            "texto_sobreimpreso": "me decían que iba a terminar siendo un huevoncio en la calle",
            "caption": "el mejor combustible es la duda ajena. dm 'mentoría' si querés el grupo.",
            "audio": "Beat con build-up que rompe en la palabra 'huevoncio'",
            "duracion": "10-12 seg",
            "score": 88, "target_views": "60k-120k",
            "tips_grabacion": "Mostrar diplomas en la pared del fondo cuando se enciende el LED. Animación del texto que aparece progresivo (palabra por palabra)."
        },
        {
            "id": "2.2", "hora": "15:00", "tipo": "CONVERSIÓN",
            "concepto": "Hace 1 año: el ego costaba 1k/mes. Hoy: el sistema da 1k/semana",
            "hook_visual": "Frame 1: pantalla roja, breach. Frame 2: pantalla verde, payout. Tu cara en esquina pequeña en frame 2.",
            "texto_sobreimpreso": "hace 1 año: ego = -1k/mes / hoy: sistema = +1k/semana",
            "caption": "el ego es caro. el sistema barato.",
            "audio": "Transición dramática en el cambio frame 1 → frame 2",
            "duracion": "10 seg",
            "score": 77, "target_views": "20k-35k",
            "tips_grabacion": "La transición frame 1 → frame 2 debe ser dramática. Tu cara en esquina pequeña en frame 2 para sumar viralidad."
        },
        {
            "id": "2.3", "hora": "20:00", "tipo": "IDENTIDAD",
            "concepto": "Setup ASMR — solo el bowl, el LED y el ronroneo del fan",
            "hook_visual": "Plano cerrado del bowl encendiéndose, LED reflejando, sin voz",
            "texto_sobreimpreso": "el silencio antes del NQ",
            "caption": "🍃",
            "audio": "Solo ambiente (ronroneo PC + crepitar bowl). Sin música.",
            "duracion": "12 seg",
            "score": 60, "target_views": "5k-10k",
            "tips_grabacion": "Sin música. El ASMR es la propuesta. Que el bowl se vea encendiéndose lentamente. NO meterle drops ni efectos."
        },
    ],
    "miércoles": [
        {
            "id": "3.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "21 años, sin universidad, sin jefe, sin alarma",
            "hook_visual": "Cara mirando cámara con vibe relax, dashboard al lado",
            "texto_sobreimpreso": "21 / sin universidad / sin jefe / sin alarma",
            "caption": "el lujo no es lo material. es la libertad de tiempo.",
            "audio": "Beat lo-fi calmo",
            "duracion": "10 seg",
            "score": 82, "target_views": "30k-70k",
            "tips_grabacion": "Vibe muy zen. NO postureo. El texto pega solo, no necesitas sobreactuar."
        },
        {
            "id": "3.2", "hora": "15:30", "tipo": "CONVERSIÓN",
            "concepto": "POV: el broker te llama pidiendo verificar tu cuenta",
            "hook_visual": "Screencast email del broker + tu cara reaccionando + screenshot del payout",
            "texto_sobreimpreso": "cuando el broker se pone nervioso ya ganaste",
            "caption": "el sistema escala. el bootcamp el 18.",
            "audio": "Beat trap con drop en el screenshot del payout",
            "duracion": "12 seg",
            "score": 70, "target_views": "12k-25k",
            "tips_grabacion": "Email del broker debe ser legible. Si es muy técnico, agrandar la parte que importa con zoom."
        },
        {
            "id": "3.3", "hora": "19:00", "tipo": "IDENTIDAD",
            "concepto": "La gente cree que tradeo todo el día. Tradeo 2 horas.",
            "hook_visual": "Tu reloj 9:30am → entrada → 11:30am cierro → resto del día relax",
            "texto_sobreimpreso": "tradeo 2h / vivo 22",
            "caption": "el dinero es para tener tiempo, no para perderlo trabajando.",
            "audio": "Beat tranquilo",
            "duracion": "10 seg",
            "score": 72, "target_views": "10k-20k",
            "tips_grabacion": "Mostrar el reloj real, no graphic overlay. Que se vea verídico."
        },
    ],
    "jueves": [
        {
            "id": "4.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "Lo que ningún gurú te dice del trading",
            "hook_visual": "Cara mirando cámara + texto provocador + dashboard al lado",
            "texto_sobreimpreso": "lo que ningún gurú te dice",
            "caption": "el secreto es aburrido. comentá '🍃' y te lo digo.",
            "audio": "Beat con build-up suspense",
            "duracion": "12 seg",
            "score": 80, "target_views": "30k-60k",
            "tips_grabacion": "Hook de curiosidad. NO reveles la respuesta en el reel — que pregunten en comentarios."
        },
        {
            "id": "4.2", "hora": "15:00", "tipo": "CONVERSIÓN",
            "concepto": "Primer payout. Lloré en silencio.",
            "hook_visual": "Screenshot del primer payout + tu cara sin sonido, ojos brillosos",
            "texto_sobreimpreso": "el primero. lloré en silencio.",
            "caption": "no es plata. es prueba de que tu mente puede.",
            "audio": "Beat emocional, piano",
            "duracion": "10 seg",
            "score": 85, "target_views": "25k-50k",
            "tips_grabacion": "MOMENTO REAL. Que la emoción se sienta verdad. Si grabás con la energía equivocada se cae."
        },
        {
            "id": "4.3", "hora": "19:30", "tipo": "IDENTIDAD",
            "concepto": "Time-lapse del trade del día — 6 horas en 8 seg",
            "hook_visual": "Time-lapse de TradingView con tu setup + el trade entrando y cerrando",
            "texto_sobreimpreso": "6h comprimidas en 8 seg",
            "caption": "el sistema trabaja, vos esperás.",
            "audio": "Beat acelerado",
            "duracion": "8 seg",
            "score": 65, "target_views": "8k-15k",
            "tips_grabacion": "Que el time-lapse sea de UN solo trade real. No mezclar varios."
        },
    ],
    "viernes": [
        {
            "id": "5.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "El 95% de los traders pierden. Yo era parte del 95%.",
            "hook_visual": "Cara seria mirando cámara + dashboard del pasado (cuenta perdida) al lado",
            "texto_sobreimpreso": "yo era el 95% / hoy soy el 5%",
            "caption": "el cambio no es magia. es método.",
            "audio": "Beat dramático",
            "duracion": "12 seg",
            "score": 83, "target_views": "30k-70k",
            "tips_grabacion": "Vibe vulnerable. La gente conecta con la versión perdida más que con la versión ganadora."
        },
        {
            "id": "5.2", "hora": "15:30", "tipo": "CONVERSIÓN",
            "concepto": "Cuenta funded $50k → primer payout en 7 días",
            "hook_visual": "Dashboard de la cuenta funded + payout proof + tu cara",
            "texto_sobreimpreso": "$50k funded / 7 días al primer payout",
            "caption": "el grupo arranca el 18. te enseño cómo.",
            "audio": "Beat trap victorioso",
            "duracion": "10 seg",
            "score": 75, "target_views": "15k-30k",
            "tips_grabacion": "Que el dashboard se vea nítido. Si la calidad de pantalla se ve baja, baja el efecto."
        },
        {
            "id": "5.3", "hora": "20:00", "tipo": "IDENTIDAD",
            "concepto": "Viernes 4pm: cerré la semana. Domingo voy a estar igual.",
            "hook_visual": "Tu reloj 4pm + dashboard cerrado + bowl + ventana con vista",
            "texto_sobreimpreso": "viernes / cerré / disfruto",
            "caption": "el sistema te devuelve los findes.",
            "audio": "Lo-fi chill",
            "duracion": "10 seg",
            "score": 68, "target_views": "8k-15k",
            "tips_grabacion": "Mostrar la ventana / contexto de relax. No solo screen del trading."
        },
    ],
    "sábado": [
        {
            "id": "6.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "Sábado 10am — mientras otros laburan, yo escalo",
            "hook_visual": "Tu cara despertando relax + bowl + view del finde",
            "texto_sobreimpreso": "sábado 10am · el resto labura · yo escalo",
            "caption": "los findes no son para descansar, son para acumular ventaja.",
            "audio": "Beat lo-fi sábado vibe",
            "duracion": "10 seg",
            "score": 76, "target_views": "20k-40k",
            "tips_grabacion": "El reloj REAL. No fake. La hora sábado 10am dispara envidia (en buen sentido)."
        },
        {
            "id": "6.2", "hora": "16:00", "tipo": "CONVERSIÓN",
            "concepto": "Quedan X cupos para el grupo del 18",
            "hook_visual": "Tu cara hablando directo a cámara + contador de cupos overlay",
            "texto_sobreimpreso": "quedan X cupos / 18 de mayo",
            "caption": "no quiero llenarlo. quiero gente que vaya en serio. dm 'sistema'.",
            "audio": "Beat directo",
            "duracion": "12 seg",
            "score": 73, "target_views": "12k-25k",
            "tips_grabacion": "Decirlo MIRANDO a cámara, no leyendo de prompt. Que se sienta directo. Actualizar el número real de cupos."
        },
        {
            "id": "6.3", "hora": "19:00", "tipo": "IDENTIDAD",
            "concepto": "Sábado revisión: las 4 entradas de la semana",
            "hook_visual": "Screencast TradingView mostrando los 4 trades de la semana, marcados",
            "texto_sobreimpreso": "revisión semanal · 4 trades · 0 emociones",
            "caption": "el sistema es repetible. la emoción no.",
            "audio": "Lo-fi review vibe",
            "duracion": "12 seg",
            "score": 62, "target_views": "8k-15k",
            "tips_grabacion": "Que se vea claro cada trade marcado. No exceder 4 (más se vuelve confuso)."
        },
    ],
    "domingo": [
        {
            "id": "7.1", "hora": "13:00", "tipo": "VIRAL",
            "concepto": "Domingo, mientras todos tienen ansiedad del lunes — yo no",
            "hook_visual": "Cara tranquila + bowl + vista relax. Contrast con frase 'sunday scaries'",
            "texto_sobreimpreso": "no tengo sunday scaries · tengo sunday strategy",
            "caption": "el lunes empieza el sistema. mañana 9am.",
            "audio": "Beat tranquilo con ligero hype al final",
            "duracion": "12 seg",
            "score": 80, "target_views": "25k-50k",
            "tips_grabacion": "Vibe MUY relax. La diferenciación viene del estado, no del texto."
        },
        {
            "id": "7.2", "hora": "16:00", "tipo": "CONVERSIÓN",
            "concepto": "Tour del bootcamp en 15 seg",
            "hook_visual": "Screen recording del Skool con todos los módulos + tu voz over",
            "texto_sobreimpreso": "lo que vas a recibir el 18",
            "caption": "el grupo del 18. dm 'bootcamp' si querés entrar.",
            "audio": "Beat hype rápido",
            "duracion": "15 seg",
            "score": 55, "target_views": "5k-10k",
            "tips_grabacion": "RAPIDO. NO te quedes mostrando UN módulo más de 2 seg. Tour rápido = sensación de mucho contenido."
        },
        {
            "id": "7.3", "hora": "20:00", "tipo": "IDENTIDAD",
            "concepto": "Cierre de semana — ritual",
            "hook_visual": "Plano del bowl, dashboard cerrado, una vela encendida, escribiendo en cuaderno",
            "texto_sobreimpreso": "cada domingo · cierro el libro · abro el siguiente",
            "caption": "el ritual es la barrera de entrada al sistema.",
            "audio": "Lo-fi muy lento, ASMR papel",
            "duracion": "12 seg",
            "score": 67, "target_views": "8k-15k",
            "tips_grabacion": "Estético MAX. Si el cuaderno o la vela se ven cheap, no lo subas. Calidad estética > velocidad."
        },
    ],
}


# ─── HELPERS ──────────────────────────────────────────────────────────────

def send_telegram(text: str, parse_mode: str = "Markdown") -> bool:
    """Envía un mensaje a Telegram. Devuelve True si OK."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️  TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"❌ Telegram error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


def create_notion_idea(reel: dict, fecha_str: str) -> str:
    """Crea entrada en database 'Ideas de Reels'. Devuelve URL de la página."""
    body = {
        "parent": {"database_id": NOTION_DB_IDEAS},
        "properties": {
            "Concepto": {"title": [{"text": {"content": f"[{reel['id']}] {reel['concepto']}"}}]},
            "Fecha sugerida": {"date": {"start": fecha_str}},
            "Hook visual": {"rich_text": [{"text": {"content": reel["hook_visual"][:1900]}}]},
            "Texto sobreimpreso": {"rich_text": [{"text": {"content": reel["texto_sobreimpreso"][:1900]}}]},
            "Tipo": {"select": {"name": reel["tipo"]}},
            "Audio sugerido": {"rich_text": [{"text": {"content": reel["audio"][:1900]}}]},
            "Score predicción": {"number": reel["score"]},
            "Estado": {"select": {"name": "Pendiente"}},
            "Caption": {"rich_text": [{"text": {"content": reel["caption"][:1900]}}]},
            "Notas": {"rich_text": [{"text": {"content": f"Hora sugerida: {reel['hora']} · Duración: {reel['duracion']} · Target views: {reel['target_views']}\n\nTips grabación: {reel['tips_grabacion']}"[:1900]}}]},
        }
    }
    url = f"{NOTION_API}/pages"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=NOTION_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            return data.get("url", "")
    except urllib.error.HTTPError as e:
        print(f"❌ Notion error {e.code}: {e.read().decode()[:300]}")
        return ""


def format_reel_message(reel: dict, dia_label: str, idx: int, notion_url: str = "") -> str:
    """Mensaje Telegram bonito por cada reel."""
    score_emoji = "🔥🔥🔥" if reel["score"] >= 85 else ("🔥🔥" if reel["score"] >= 70 else ("🔥" if reel["score"] >= 55 else "⚠️"))
    msg = f"""*REEL {idx}/3 — {dia_label.upper()}* {score_emoji}

🎬 *[{reel['id']}] {reel['concepto']}*

⏰ Hora sugerida: `{reel['hora']}`
📊 Tipo: `{reel['tipo']}`  ·  Score: `{reel['score']}/100`  ·  Target: {reel['target_views']}
⏱ Duración: `{reel['duracion']}`

🎨 *Hook visual:*
{reel['hook_visual']}

✍️ *Texto sobreimpreso:*
`{reel['texto_sobreimpreso']}`

📝 *Caption:*
_{reel['caption']}_

🎵 Audio: {reel['audio']}

💡 *Tips grabación:*
{reel['tips_grabacion']}
"""
    if notion_url:
        msg += f"\n🔗 [Abrir en Notion]({notion_url})"
    return msg


# ─── MAIN ─────────────────────────────────────────────────────────────────

def resolver_dia(arg: str | None) -> tuple[str, str]:
    """Devuelve (dia_label, fecha_iso_str)."""
    if arg:
        # ¿Es nombre de día?
        arg_lower = arg.lower().strip()
        if arg_lower in DIAS_NUM:
            # Buscar la próxima ocurrencia desde hoy (incluyendo hoy)
            hoy = datetime.now(LIMA_TZ).date()
            target_wd = DIAS_NUM[arg_lower]
            offset = (target_wd - hoy.weekday()) % 7
            fecha = hoy + timedelta(days=offset)
            return arg_lower, fecha.isoformat()
        # ¿Es fecha ISO?
        try:
            fecha = datetime.strptime(arg, "%Y-%m-%d").date()
            return DIAS_ES[fecha.weekday()], fecha.isoformat()
        except ValueError:
            print(f"❌ Día inválido: {arg}. Usá nombre (lunes, martes...) o YYYY-MM-DD")
            sys.exit(1)
    # Default: hoy Lima time
    hoy = datetime.now(LIMA_TZ).date()
    return DIAS_ES[hoy.weekday()], hoy.isoformat()


def main():
    arg = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dia" and len(sys.argv) > 2:
            arg = sys.argv[2]
        else:
            arg = sys.argv[1]

    dia_label, fecha_iso = resolver_dia(arg)
    print(f"📅 Día: {dia_label} ({fecha_iso})\n")

    reels_hoy = REELS.get(dia_label, [])
    if not reels_hoy:
        print(f"⚠️  No hay reels para {dia_label}")
        sys.exit(1)

    # Header en Telegram
    header = f"""☀️ *BUEN DÍA BRO — {dia_label.upper()} {fecha_iso}*

Tus 3 reels del día con scoring + Notion sync.

Total predicción combinada: *{sum(r['score'] for r in reels_hoy)}/300*"""
    send_telegram(header)

    # Cada reel
    for i, reel in enumerate(reels_hoy, 1):
        print(f"  📤 Procesando reel {reel['id']}...")
        notion_url = create_notion_idea(reel, fecha_iso)
        msg = format_reel_message(reel, dia_label, i, notion_url)
        ok = send_telegram(msg)
        status = "✅" if ok else "❌"
        print(f"     {status} Telegram · Notion: {notion_url or 'falló'}")

    # Footer
    footer = f"""✅ *{len(reels_hoy)} reels listos en Notion*

Cuando grabes alguno, cambialo a 'Grabado' en la database 'Ideas de Reels'.
Cuando lo publiques → 'Publicado' + pegá las views.

Mañana 8am vuelvo con los 3 siguientes."""
    send_telegram(footer)
    print(f"\n✅ Listo. {len(reels_hoy)} reels enviados para {dia_label}.")


if __name__ == "__main__":
    main()
