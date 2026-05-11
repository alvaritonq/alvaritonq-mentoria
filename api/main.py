#!/usr/bin/env python3
"""
MENTORIA API — Backend FastAPI
==============================
Recibe aplicaciones del formulario web y las guarda en el sistema de mentoría.

Deploy: uvicorn api.main:app --reload
Prod:   uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

# ── Admin auth ────────────────────────────────────────────────────────────────
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()

def require_admin(token: Optional[str]):
    """Levanta 403 si el token no coincide con ADMIN_TOKEN."""
    if not ADMIN_TOKEN:
        # Si no se configuró el token en el server, bloqueamos por defecto
        raise HTTPException(status_code=503, detail="Admin endpoint not configured")
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

# ── Setup paths ───────────────────────────────────────────────────────────────
API_DIR   = Path(__file__).parent
BASE_DIR  = API_DIR.parent

# En Render usamos /data (disco persistente). Localmente usamos BASE_DIR.
DATA_DIR  = Path(os.environ.get("RENDER_DATA_DIR", str(BASE_DIR)))

WEB_DIR      = BASE_DIR / "web"
STUDENTS     = DATA_DIR / "students"
LOGS         = DATA_DIR / "logs"
ACCOUNTING   = DATA_DIR / "accounting" / "registro.json"
APPLICATIONS = DATA_DIR / "applications"

STUDENTS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
APPLICATIONS.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "accounting").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

# ── Anthropic (opcional — para análisis automático) ────────────────────────────
try:
    import anthropic

    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    if not API_KEY:
        plist = Path.home() / "Library/LaunchAgents/com.aelun.telegrambot.plist"
        if plist.exists():
            txt = plist.read_text()
            API_KEY = txt.split("<key>ANTHROPIC_API_KEY</key>")[1].split("<string>")[1].split("</string>")[0]

    if not API_KEY:
        config_file = BASE_DIR / "config.txt"
        if config_file.exists():
            for line in config_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    v = line.split("=", 1)[1].strip()
                    if v and v != "PONER_TU_KEY_AQUI":
                        API_KEY = v
                        break

    if API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = API_KEY
        ai_client = anthropic.Anthropic(api_key=API_KEY)
        AI_ENABLED = True
    else:
        ai_client = None
        AI_ENABLED = False

except ImportError:
    ai_client = None
    AI_ENABLED = False

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MENTORIA API",
    description="Backend del sistema de mentoría de Álvaro Tolentino",
    version="1.0.0"
)

# CORS — restringido a dominios propios
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alvaritonq.me",
        "https://www.alvaritonq.me",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Middleware de security headers ────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Bloquea iframe embedding (anti-clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    # Fuerza HTTPS por 1 año (HSTS)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Bloquea MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Política de referrer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP básico — ajustar si agregamos más recursos externos
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "frame-src https://www.youtube.com https://buy.stripe.com; "
        "connect-src 'self';"
    )
    return response

# ── Schemas ───────────────────────────────────────────────────────────────────
class ApplicationForm(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = ""         # teléfono con código de país
    instagram: Optional[str] = ""        # usuario de instagram
    experiencia: Optional[str] = ""      # s1 — experiencia libre (tiempo + instrumentos + prop firm)
    resultado: Optional[str] = ""        # s2 — cómo le ha ido
    problema: Optional[str] = ""         # s3 — mayor problema
    objetivo: Optional[str] = ""         # s4 — qué quiere lograr (textarea)
    disponibilidad: Optional[str] = ""   # s5 — horas por día
    horario_llamadas: Optional[str] = "" # s6 — horario sesiones
    como_llego: Optional[str] = ""       # s7 — cómo llegó

class HealthResponse(BaseModel):
    status: str
    ai_enabled: bool
    students_count: int
    version: str

# ── Utils ─────────────────────────────────────────────────────────────────────
def student_dir(name: str) -> Path:
    slug = name.lower().replace(" ", "-")
    d = STUDENTS / slug
    d.mkdir(exist_ok=True)
    (d / "sessions").mkdir(exist_ok=True)
    return d

def load_accounting() -> dict:
    if ACCOUNTING.exists():
        return json.loads(ACCOUNTING.read_text())
    return {"students": {}, "revenue": [], "total": 0}

def save_accounting(data: dict):
    ACCOUNTING.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def log_api(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [API] {msg}"
    print(line)
    log_file = LOGS / f"{datetime.now().strftime('%Y-%m')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")

def notify_telegram(form: "ApplicationForm"):
    """Manda notificación al Telegram de Álvaro cuando llega una nueva aplicación."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return

    texto = (
        f"🔔 *Nueva aplicación — Mentoría*\n\n"
        f"👤 *{form.nombre}*\n"
        f"📧 {form.email}\n"
        f"📱 {form.telefono}\n"
        f"📸 {form.instagram}\n\n"
        f"⏱ Experiencia: {form.experiencia}\n"
        f"📈 Resultados: {form.resultado}\n"
        f"🔥 Problema: {form.problema}\n"
        f"🎯 Objetivo: {form.objetivo}\n"
        f"⏰ Disponibilidad: {form.disponibilidad}\n"
        f"📅 Horario: {form.horario_llamadas}\n"
        f"📣 Cómo llegó: {form.como_llego}"
    )

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=5)
        log_api(f"Telegram notificado: {form.nombre}")
    except Exception as e:
        log_api(f"Telegram error (no crítico): {e}")

def send_confirmation_email(form: "ApplicationForm"):
    """Manda email de confirmación al aplicante."""
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_pass:
        return

    body = f"""Hola {form.nombre} 👋

Recibí tu aplicación a la mentoría. Voy a revisarla y te escribo en menos de 24 horas.

Mientras tanto, si tenés alguna pregunta podés escribirme directamente por Instagram: @alvaritonq

¡Hablamos pronto!
Álvaro
"""
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "Aplicación recibida — Mentoría AlvaritoNQ"
        msg["From"]    = f"AlvaritoNQ <{gmail_user}>"
        msg["To"]      = form.email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, form.email, msg.as_string())
        log_api(f"Email confirmación enviado a {form.email}")
    except Exception as e:
        log_api(f"Email error (no crítico): {e}")

SYSTEM_ONBOARDING = """Sos el agente de Onboarding de la mentoría de trading de Álvaro Tolentino.
Tu trabajo es hacer el diagnóstico inicial de un nuevo alumno a partir de sus respuestas.

Metodología que enseña Álvaro: Wyckoff + SMC, FVG/IFVG/BOS, Heatmap CME (Bookmap),
AMD/PO3, Opening Range 15min, SMT NQ vs ES, prop firms (Alpha Futures, Lucid, MFFU).
Precio: $250/mes · 2 llamadas/semana × 4 semanas + soporte 24/7.

Dado el perfil del alumno, generá:
1. Resumen del perfil (nivel, objetivos, experiencia, problemas principales)
2. Áreas prioritarias para trabajar
3. Red flags o riesgos que Álvaro debe tener en cuenta
4. Primera impresión: ¿está listo para esta mentoría? ¿qué esperar de él?

Formato: claro, en bullets, directo."""

def analyze_applicant(form: ApplicationForm) -> str:
    """Genera análisis del applicante con Claude. Retorna string vacío si AI no disponible."""
    if not AI_ENABLED or not ai_client:
        return ""

    try:
        user_text = f"""Nuevo aplicante para la mentoría:

Nombre: {form.nombre}
Email: {form.email}
Experiencia en trading: {form.experiencia}
Instrumentos que opera: {form.instrumentos}
Prop firm: {form.prop_firm}
Resultados hasta ahora: {form.resultado}
Horas disponibles por día: {form.disponibilidad}
Mayor problema actual: {form.problema}
Objetivo en 4 semanas: {form.objetivo}
Horario para llamadas: {form.horario_llamadas}
Cómo llegó a Álvaro: {form.como_llego}"""

        msg = ai_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=SYSTEM_ONBOARDING,
            messages=[{"role": "user", "content": user_text}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log_api(f"AI analysis failed: {e}")
        return ""

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    """Estado del sistema."""
    students_count = len([d for d in STUDENTS.iterdir() if d.is_dir()]) if STUDENTS.exists() else 0
    return HealthResponse(
        status="ok",
        ai_enabled=AI_ENABLED,
        students_count=students_count,
        version="1.0.0"
    )

@app.post("/api/apply")
def apply(form: ApplicationForm):
    """
    Recibe la aplicación del formulario web.
    1. Guarda la aplicación raw en applications/
    2. Crea el perfil del alumno en students/
    3. Genera análisis con Claude (si API key disponible)
    4. Registra en accounting
    """
    ts = datetime.now()
    slug = form.nombre.lower().replace(" ", "-")
    log_api(f"NEW APPLICATION: {form.nombre} <{form.email}>")

    # 1. Guardar aplicación raw (siempre, sin importar nada)
    app_file = APPLICATIONS / f"{ts.strftime('%Y-%m-%d-%H%M%S')}-{slug}.json"
    raw_data = form.model_dump()
    raw_data["timestamp"] = ts.isoformat()
    app_file.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False))

    # 2. Verificar si el alumno ya existe
    sdir = student_dir(form.nombre)
    profile_file = sdir / "profile.json"

    if profile_file.exists():
        log_api(f"DUPLICATE APPLICATION: {form.nombre}")
        # No falla — actualiza el perfil con los nuevos datos
        existing = json.loads(profile_file.read_text())
        existing["email"] = form.email
        existing["ultima_aplicacion"] = ts.isoformat()
    else:
        existing = None

    # 3. Armar perfil
    profile = {
        "nombre": form.nombre,
        "email": form.email,
        "fecha_inicio": ts.strftime("%Y-%m-%d"),
        "estado": "aplicante",   # será "activo" cuando Álvaro confirme
        "semana_actual": 1,
        "sesiones_completadas": 0,
        "experiencia": form.experiencia,
        "instrumentos": form.instrumentos,
        "prop_firm": form.prop_firm,
        "resultado": form.resultado,
        "disponibilidad": form.disponibilidad,
        "problema": form.problema,
        "objetivo": form.objetivo,
        "horario_llamadas": form.horario_llamadas,
        "como_llego": form.como_llego,
    }

    if existing:
        # Preservar campos de tracking si ya existía
        for key in ["semana_actual", "sesiones_completadas", "estado", "fecha_inicio"]:
            if key in existing:
                profile[key] = existing[key]

    profile_file.write_text(json.dumps(profile, indent=2, ensure_ascii=False))

    # 4. Análisis IA (no bloquea si falla)
    analysis = analyze_applicant(form)
    if analysis:
        onboarding_file = sdir / "onboarding.md"
        onboarding_file.write_text(
            f"# Onboarding — {form.nombre}\n\n"
            f"**Fecha aplicación:** {ts.strftime('%Y-%m-%d %H:%M')}\n"
            f"**Email:** {form.email}\n\n"
            f"## Análisis IA\n\n{analysis}\n\n"
            f"## Datos Crudos\n\n"
            + "\n".join([f"**{k}:** {v}" for k, v in form.model_dump().items() if k not in ["nombre", "email"]])
        )

    # 5. Accounting — registrar aplicante (no pago, solo el lead)
    try:
        acc = load_accounting()
        if form.nombre not in acc["students"]:
            acc["students"][form.nombre] = {
                "email": form.email,
                "fecha_aplicacion": ts.strftime("%Y-%m-%d"),
                "estado": "aplicante",
                "pagos": 0
            }
        else:
            acc["students"][form.nombre]["email"] = form.email
            acc["students"][form.nombre]["ultima_aplicacion"] = ts.strftime("%Y-%m-%d")
        save_accounting(acc)
    except Exception as e:
        log_api(f"Accounting update failed (non-critical): {e}")

    log_api(f"APPLICATION SAVED: {form.nombre} → students/{slug}/")

    # Notificar por Telegram y enviar confirmación al aplicante
    notify_telegram(form)
    send_confirmation_email(form)

    return {
        "success": True,
        "message": "Aplicación recibida",
        "alumno": form.nombre,
        "ai_analysis": bool(analysis),
        "timestamp": ts.isoformat()
    }

@app.get("/api/applications")
def list_applications(x_admin_token: Optional[str] = Header(None)):
    """Lista todas las aplicaciones recibidas (para uso de Álvaro)."""
    require_admin(x_admin_token)
    apps = []
    for f in sorted(APPLICATIONS.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            apps.append({
                "archivo": f.name,
                "nombre": data.get("nombre"),
                "email": data.get("email"),
                "timestamp": data.get("timestamp"),
                "problema": data.get("problema", "")[:100],
                "objetivo": data.get("objetivo", "")[:100],
            })
        except Exception:
            pass
    return {"total": len(apps), "applications": apps}

@app.get("/api/students")
def list_students(x_admin_token: Optional[str] = Header(None)):
    """Lista todos los alumnos activos."""
    require_admin(x_admin_token)
    acc = load_accounting()
    students = []
    for name, data in acc.get("students", {}).items():
        # Cargar perfil si existe
        slug = name.lower().replace(" ", "-")
        profile_file = STUDENTS / slug / "profile.json"
        sessions_count = 0
        if profile_file.exists():
            p = json.loads(profile_file.read_text())
            sessions_count = p.get("sesiones_completadas", 0)

        students.append({
            "nombre": name,
            "email": data.get("email", ""),
            "estado": data.get("estado", "desconocido"),
            "fecha_aplicacion": data.get("fecha_aplicacion", ""),
            "pagos": data.get("pagos", 0),
            "sesiones": sessions_count,
        })
    return {"total": len(students), "students": students}

# ── Serve frontend estático ───────────────────────────────────────────────────
# Si existe el directorio web/, lo sirve en /
# Esto permite deployar todo desde un solo server (opcional)
if WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(
            str(WEB_DIR / "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    # Servir páginas HTML específicas del sitio (intermediarios de compra,
    # términos, descargas, etc.) por nombre limpio sin .html.
    _SAFE_PAGES = {
        "comprar-ebook",
        "comprar-bootcamp",
        "descarga-ebook",
        "descarga-bootcamp",
        "terminos",
    }

    @app.get("/{page}")
    def serve_page(page: str):
        # Quitar .html si vino con extensión y normalizar
        slug = page.rstrip("/").removesuffix(".html")
        if slug not in _SAFE_PAGES:
            raise HTTPException(status_code=404, detail="Not found")
        html_file = WEB_DIR / f"{slug}.html"
        if not html_file.exists():
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(
            str(html_file),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    # Servir las páginas ocultas con hash en su path completo
    _HIDDEN_PATHS = {
        "g7f2k9x4q1m8p3w6": "g7f2k9x4q1m8p3w6/acceso.html",
        "h5n8r2v9j4t1y7l3": "h5n8r2v9j4t1y7l3/acceso.html",
        "m9k4p7t2v6x1z8b5": "m9k4p7t2v6x1z8b5/acceso.html",
    }

    @app.get("/{hash_dir}/acceso.html")
    def serve_hidden(hash_dir: str):
        if hash_dir not in _HIDDEN_PATHS:
            raise HTTPException(status_code=404, detail="Not found")
        html_file = WEB_DIR / _HIDDEN_PATHS[hash_dir]
        if not html_file.exists():
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(
            str(html_file),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("🚀 MENTORIA API corriendo en http://localhost:8000")
    print(f"   AI Analysis: {'✅ habilitado' if AI_ENABLED else '⚠️  deshabilitado (falta API key)'}")
    print(f"   Alumnos registrados: {len([d for d in STUDENTS.iterdir() if d.is_dir()])}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(API_DIR))
