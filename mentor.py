#!/usr/bin/env python3
"""
MENTORIA — Sistema de Mentoría de Álvaro Tolentino
====================================================
CLI principal. Orquesta todos los subagentes.

Uso:
    python3 mentor.py new "Juan Pérez"
    python3 mentor.py plan "Juan Pérez"
    python3 mentor.py prep "Juan Pérez"
    python3 mentor.py live "Juan Pérez"
    python3 mentor.py progress "Juan Pérez"
    python3 mentor.py report
    python3 mentor.py marketing instagram
    python3 mentor.py video "cómo leer el heatmap"
    python3 mentor.py pago "Juan Pérez" 250
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# ── Setup paths ──────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
STUDENTS    = BASE_DIR / "students"
ACCOUNTING  = BASE_DIR / "accounting" / "registro.json"
LOGS        = BASE_DIR / "logs"
SUBAGENTS   = BASE_DIR / "subagents"

STUDENTS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)
(BASE_DIR / "accounting").mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

# ── Anthropic ─────────────────────────────────────────────────────────────────
import anthropic

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

if not API_KEY:
    # Mac: leer del plist de AELUN
    try:
        plist = Path.home() / "Library/LaunchAgents/com.aelun.telegrambot.plist"
        txt = plist.read_text()
        API_KEY = txt.split("<key>ANTHROPIC_API_KEY</key>")[1].split("<string>")[1].split("</string>")[0]
        os.environ["ANTHROPIC_API_KEY"] = API_KEY
    except Exception:
        pass

if not API_KEY:
    # Windows: leer de config.txt local (mismo directorio que mentor.py)
    config_file = BASE_DIR / "config.txt"
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip()
                os.environ["ANTHROPIC_API_KEY"] = API_KEY
                break

if not API_KEY:
    print("❌ No se encontró ANTHROPIC_API_KEY.")
    print("   Mac:     export ANTHROPIC_API_KEY=sk-ant-...")
    print("   Windows: crear config.txt con ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

MODEL = "claude-sonnet-4-5"
MODEL_OPUS = "claude-opus-4-5"

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────

def ask_claude(system: str, user: str, model: str = MODEL, max_tokens: int = 2000) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return msg.content[0].text.strip()

def student_dir(name: str) -> Path:
    slug = name.lower().replace(" ", "-")
    d = STUDENTS / slug
    d.mkdir(exist_ok=True)
    (d / "sessions").mkdir(exist_ok=True)
    return d

def load_profile(name: str) -> dict:
    p = student_dir(name) / "profile.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}

def save_profile(name: str, data: dict):
    p = student_dir(name) / "profile.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def load_accounting() -> dict:
    if ACCOUNTING.exists():
        return json.loads(ACCOUNTING.read_text())
    return {"students": {}, "revenue": [], "total": 0}

def save_accounting(data: dict):
    ACCOUNTING.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file = LOGS / f"{datetime.now().strftime('%Y-%m')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")

def print_section(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}\n")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 1 — ONBOARDING
# ─────────────────────────────────────────────────────────────────────────────

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

def cmd_new(name: str):
    print_section(f"🤝 ONBOARDING — {name}")
    print("Respondé las siguientes preguntas para crear el perfil del alumno.")
    print("(Podés escribir respuestas cortas)\n")

    preguntas = [
        ("experiencia", "¿Cuánto tiempo lleva en trading? (semanas/meses/años)"),
        ("instrumentos", "¿Qué instrumentos opera? (acciones, futuros, forex, etc.)"),
        ("prop_firm", "¿Está en una prop firm? ¿Cuál? ¿Eval o Funded?"),
        ("resultado", "¿Cómo le ha ido? (en pérdidas, breakeven, ganando)"),
        ("problema", "¿Cuál es su mayor problema ahorita mismo?"),
        ("objetivo", "¿Qué quiere lograr en estas 4 semanas?"),
        ("disponibilidad", "¿Cuántas horas por día puede dedicar al trading?"),
        ("horario_llamadas", "¿Qué horario le viene bien para las 2 llamadas semanales?"),
        ("como_llego", "¿Cómo llegó a Álvaro? (Instagram, referido, Twitter, etc.)"),
        ("notas", "¿Algo más que Álvaro deba saber?"),
    ]

    respuestas = {}
    for key, pregunta in preguntas:
        print(f"→ {pregunta}")
        respuestas[key] = input("  Respuesta: ").strip()

    # Guardar perfil raw
    profile = {
        "nombre": name,
        "fecha_inicio": datetime.now().strftime("%Y-%m-%d"),
        "estado": "activo",
        "semana_actual": 1,
        "sesiones_completadas": 0,
        **respuestas
    }
    save_profile(name, profile)

    # Análisis del agente
    print("\n🧠 Analizando perfil...\n")
    user_text = f"Nuevo alumno: {name}\n\n" + "\n".join([f"{k}: {v}" for k, v in respuestas.items()])
    analysis = ask_claude(SYSTEM_ONBOARDING, user_text)

    # Guardar análisis
    out = student_dir(name) / "onboarding.md"
    out.write_text(f"# Onboarding — {name}\n\n**Fecha:** {datetime.now().strftime('%Y-%m-%d')}\n\n{analysis}")

    # Agregar a contabilidad
    acc = load_accounting()
    acc["students"][name] = {"fecha_inicio": profile["fecha_inicio"], "estado": "activo", "pagos": 0}
    save_accounting(acc)

    print(analysis)
    print(f"\n✅ Perfil guardado en students/{name.lower().replace(' ', '-')}/")
    log(f"NEW STUDENT: {name}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 2 — CURRICULUM (Plan 4 semanas)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_CURRICULUM = """Sos el Curriculum Designer de la mentoría de trading de Álvaro Tolentino.

Metodología completa:
- SEMANA 1: Fundamentos — Wyckoff (ciclos, fases, eventos SC/AR/Spring/UTAD), SMC base (liquidez ERL/IRL, FVG, BOS, MSS), Premium/Discount, Kill Zones
- SEMANA 2: Estructura y Heatmap — AMD/PO3 en 15-5-3min, Opening Range 15min (OR), lectura del Heatmap CME Level 2 (Bookmap), SMT NQ vs ES
- SEMANA 3: Ejecución — Modelo de entrada completo (GATE+absorción+BOS/IFVG+CVD+SMT), gestión de SL/TP, reglas prop firm (trailing drawdown, consistency rule)
- SEMANA 4: Psicología y sistema — Journaling, review de trades, revenge trading, escalado, retiros de prop firm

Dado el perfil del alumno, diseñá el plan personalizado de 4 semanas:
- 2 sesiones por semana (Sesión A y Sesión B)
- Para cada sesión: tema, objetivos, ejercicio práctico, tarea para el hogar
- Adaptar según nivel: si es principiante, ir más despacio en semana 1-2
- Si ya tiene experiencia, enfocarse en los gaps específicos que mencionó

Formato: Markdown limpio, estructurado por semana y sesión."""

def cmd_plan(name: str):
    print_section(f"📋 PLAN 4 SEMANAS — {name}")
    profile = load_profile(name)
    if not profile:
        print(f"❌ No existe el alumno '{name}'. Corrés primero: python3 mentor.py new \"{name}\"")
        return

    print("🧠 Diseñando plan personalizado...\n")
    user_text = f"Alumno: {name}\n\nPerfil:\n" + json.dumps(profile, indent=2, ensure_ascii=False)
    plan = ask_claude(SYSTEM_CURRICULUM, user_text, max_tokens=3000)

    out = student_dir(name) / "plan.md"
    out.write_text(f"# Plan 4 Semanas — {name}\n\n**Generado:** {datetime.now().strftime('%Y-%m-%d')}\n\n{plan}")

    print(plan)
    print(f"\n✅ Plan guardado en students/{name.lower().replace(' ', '-')}/plan.md")
    log(f"PLAN CREATED: {name}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 3 — SESSION PREP (Preparación de sesión)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_SESSION_PREP = """Sos el Session Prep Agent de la mentoría de Álvaro Tolentino.

Tu trabajo: preparar la agenda completa para la próxima sesión, para que Álvaro llegue listo
y no tenga que improvisar nada. Álvaro solo necesita aparecer — vos hacés el trabajo previo.

Para cada sesión generá:
1. **Recap** — qué se vio la sesión anterior (si aplica), qué tarea tenía el alumno
2. **Agenda de la sesión** — paso a paso con tiempos estimados (total 60-75 min)
3. **Concepto principal** — explicación del tema del día con ejemplos específicos de NQ/ES
4. **Ejercicio práctico** — algo que el alumno hace EN la llamada (identificar en chart, etc.)
5. **Preguntas para el alumno** — Álvaro debe hacer estas preguntas para diagnosticar comprensión
6. **Señales de alerta** — si el alumno dice X, significa que no entendió Y → cómo redirigir
7. **Tarea para casa** — qué debe practicar hasta la próxima sesión
8. **Métricas de éxito** — cómo saber si esta sesión fue exitosa

Formato: directo, en bullets, listo para que Álvaro lo lea 5 minutos antes de la llamada."""

def cmd_prep(name: str):
    print_section(f"🎯 PREPARACIÓN DE SESIÓN — {name}")
    profile = load_profile(name)
    if not profile:
        print(f"❌ No existe el alumno '{name}'.")
        return

    plan_file = student_dir(name) / "plan.md"
    plan = plan_file.read_text() if plan_file.exists() else "Plan no disponible"

    progress_file = student_dir(name) / "progress.md"
    progress = progress_file.read_text() if progress_file.exists() else "Sin progreso registrado aún"

    sesion_num = profile.get("sesiones_completadas", 0) + 1
    print(f"🧠 Preparando Sesión #{sesion_num}...\n")

    user_text = f"""Alumno: {name}
Sesión número: {sesion_num}
Semana: {profile.get('semana_actual', 1)}

Perfil del alumno:
{json.dumps(profile, indent=2, ensure_ascii=False)}

Plan de 4 semanas:
{plan[:2000]}

Progreso hasta ahora:
{progress[:1000]}"""

    prep = ask_claude(SYSTEM_SESSION_PREP, user_text, max_tokens=2500)

    out = student_dir(name) / "sessions" / f"sesion-{sesion_num}-prep.md"
    out.write_text(f"# Sesión #{sesion_num} — Prep — {name}\n\n**Fecha:** {datetime.now().strftime('%Y-%m-%d')}\n\n{prep}")

    print(prep)
    print(f"\n✅ Prep guardado en sessions/sesion-{sesion_num}-prep.md")
    log(f"SESSION PREP: {name} sesion #{sesion_num}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 4 — LIVE COACH (Asistente en vivo durante la llamada)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_LIVE = """Sos el Live Coach de Álvaro Tolentino — su asistente durante las llamadas de mentoría.

Álvaro está EN VIVO con un alumno ahora mismo. Él te pasa lo que dice el alumno
y vos le das la MEJOR RESPUESTA posible para que él la use inmediatamente.

Reglas:
- Respuesta directa, lista para hablar. Sin introducciones.
- Máximo 3-4 oraciones. El alumno está esperando.
- Usá ejemplos concretos de NQ/ES cuando sea posible
- Si el alumno está confundido → simplificar con analogía
- Si el alumno pregunta algo que no es del programa → redirigir con tacto
- Si el alumno quiere aprender algo avanzado → validar y agendarlo para semana posterior
- Si el alumno tiene un problema psicológico (miedo, revenge) → respuesta empática + solución concreta

Metodología de Álvaro: Wyckoff + SMC, FVG/IFVG/BOS, Heatmap CME, AMD/PO3, OR 15min, SMT NQ vs ES."""

def cmd_live(name: str):
    print_section(f"🎙️ MODO EN VIVO — {name}")
    profile = load_profile(name)

    # Cargar prep de sesión si existe
    sesion_num = profile.get("sesiones_completadas", 0) + 1
    prep_file = student_dir(name) / "sessions" / f"sesion-{sesion_num}-prep.md"
    context = prep_file.read_text() if prep_file.exists() else ""

    print(f"Alumno: {name} | Sesión #{sesion_num}")
    print("Escribí lo que dice el alumno → ENTER → recibís la mejor respuesta.")
    print("Escribí 'fin' para terminar la sesión.\n")

    notas = []
    while True:
        print("─" * 50)
        alumno_dice = input("📢 Alumno dice: ").strip()
        if alumno_dice.lower() in ["fin", "exit", "salir"]:
            break
        if not alumno_dice:
            continue

        user_text = f"""Alumno: {name}
Contexto de la sesión: {context[:500] if context else 'no disponible'}

El alumno acaba de decir:
"{alumno_dice}"

Dame la mejor respuesta para que Álvaro la diga ahora mismo."""

        print("\n💬 Álvaro responde:\n")
        respuesta = ask_claude(SYSTEM_LIVE, user_text, max_tokens=400)
        print(respuesta)
        notas.append({"alumno": alumno_dice, "respuesta": respuesta})

    # Guardar notas de la sesión
    if notas:
        out = student_dir(name) / "sessions" / f"sesion-{sesion_num}-notas.md"
        content = f"# Sesión #{sesion_num} — Notas en Vivo — {name}\n\n**Fecha:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
        for i, n in enumerate(notas, 1):
            content += f"### Intercambio {i}\n**Alumno:** {n['alumno']}\n**Álvaro:** {n['respuesta']}\n\n"
        out.write_text(content)

        # Actualizar sesiones completadas
        profile["sesiones_completadas"] = sesion_num
        if sesion_num % 2 == 0:
            profile["semana_actual"] = profile.get("semana_actual", 1) + 1
        save_profile(name, profile)

        print(f"\n✅ Sesión guardada. Total sesiones: {sesion_num}")
        log(f"LIVE SESSION COMPLETED: {name} sesion #{sesion_num}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 5 — PROGRESS TRACKER
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROGRESS = """Sos el Progress Tracker de la mentoría de Álvaro Tolentino.

Analizás el historial de sesiones de un alumno y generás:
1. **Resumen de progreso** — qué aprendió, qué consolidó, qué sigue faltando
2. **Nivel actual** — dónde está el alumno en la curva de aprendizaje (1-10)
3. **Velocidad de aprendizaje** — está avanzando rápido, normal, o lento
4. **Fortalezas** — qué entiende bien
5. **Gaps críticos** — qué no entiende todavía y es bloqueante
6. **Riesgo de abandono** — ¿hay señales de que pueda dejar la mentoría? (frustración, falta de progreso, etc.)
7. **Recomendación para próxima semana** — ajuste del plan si es necesario
8. **Mensaje motivacional** — algo específico para este alumno que Álvaro puede decirle

Formato: directo, con números y ejemplos."""

def cmd_progress(name: str):
    print_section(f"📈 PROGRESO — {name}")
    profile = load_profile(name)
    if not profile:
        print(f"❌ No existe el alumno '{name}'.")
        return

    # Leer todas las notas de sesiones
    sessions_dir = student_dir(name) / "sessions"
    notas_all = ""
    for f in sorted(sessions_dir.glob("*.md")):
        notas_all += f"\n\n--- {f.name} ---\n" + f.read_text()[:800]

    print("🧠 Analizando progreso...\n")
    user_text = f"""Alumno: {name}
Semana actual: {profile.get('semana_actual', 1)}
Sesiones completadas: {profile.get('sesiones_completadas', 0)}
Perfil: {json.dumps(profile, indent=2, ensure_ascii=False)}

Historial de sesiones:
{notas_all[:3000] if notas_all else 'Sin sesiones registradas aún'}"""

    analysis = ask_claude(SYSTEM_PROGRESS, user_text, max_tokens=1500)

    out = student_dir(name) / "progress.md"
    out.write_text(f"# Progreso — {name}\n\n**Actualizado:** {datetime.now().strftime('%Y-%m-%d')}\n\n{analysis}")

    print(analysis)
    log(f"PROGRESS REVIEW: {name}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 6 — MARKETING
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_MARKETING = """Sos el Marketing Manager de la mentoría de trading de Álvaro Tolentino.

Álvaro: 21 años, Lima, trader NQ/ES + mentor. Handle: @alvaritonq.
Producto: Mentoría 1:1 $250/mes · 2 llamadas semanales + soporte 24/7.
Audiencia: traders retail 18-35 años, habla española, quieren vivir del trading o pasar prop firms.

Generás contenido que convierte. Estilo: directo, sin filtros, basado en resultados reales.
Nada de motivación genérica — siempre con datos, metodología y prueba social específica."""

def cmd_marketing(platform: str = "instagram"):
    print_section(f"📣 MARKETING — {platform.upper()}")

    prompts = {
        "instagram": """Generá 5 ideas de posts para Instagram de Álvaro (@alvaritonq) para esta semana.
Para cada idea: Caption completo + CTA + hashtags + tipo de visual sugerido.
Temas a rotar: wins de trading, errores comunes del retail, explicación de concepto (FVG/OR/SMT),
behind the scenes de mentoría, testimonio/resultado de alumno.""",

        "tiktok": """Generá 5 scripts cortos para TikTok de Álvaro (@alvaritonq).
Cada video de 30-60 segundos. Hook en los primeros 3 segundos.
Formato: Hook / Conflicto / Revelación / CTA.
Temas: errores que le costaron dinero, cómo funciona realmente el heatmap,
diferencia entre retail y smart money, cómo pasar una evaluación de prop firm.""",

        "email": """Escribí una secuencia de 3 emails para prospects interesados en la mentoría de Álvaro.
Email 1 (día 0): Bienvenida + historia de Álvaro + qué van a aprender
Email 2 (día 2): Error #1 que comete todo trader (con solución)
Email 3 (día 4): Oferta directa de la mentoría con garantía implícita y escasez real.""",

        "stories": """Generá una secuencia de 7 Instagram Stories para esta semana.
Lunes a domingo. Cada story: objetivo + texto + visual + acción del usuario.
Mix de: educación, motivación, behind the scenes, encuestas, CTA a DM.""",
    }

    prompt = prompts.get(platform, prompts["instagram"])
    content = ask_claude(SYSTEM_MARKETING, prompt, max_tokens=2500)

    out = BASE_DIR / "marketing" / "copy" / f"{datetime.now().strftime('%Y-%m-%d')}-{platform}.md"
    out.write_text(f"# Marketing {platform.upper()} — {datetime.now().strftime('%Y-%m-%d')}\n\n{content}")

    print(content)
    print(f"\n✅ Guardado en marketing/copy/")
    log(f"MARKETING GENERATED: {platform}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 7 — CONTENT CREATOR (Scripts de video / PDFs)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_CONTENT = """Sos el Content Creator de la mentoría de Álvaro Tolentino.

Creás material educativo de alta calidad: scripts de video y estructura de PDFs.
Metodología: Wyckoff + SMC, FVG/IFVG/BOS, Heatmap CME, AMD/PO3, OR 15min, SMT.

Para scripts de video:
- Duración target: 8-15 minutos (contenido gratuito) o 20-45 min (contenido premium)
- Estructura: Hook → Problema → Concepto → Ejemplo en chart → Aplicación práctica → CTA
- Lenguaje: directo, técnico pero accesible, con ejemplos en NQ

Para PDFs:
- Máximo 10 páginas, visual, con ejemplos reales
- Cada sección debe tener: teoría + ejemplo + ejercicio del lector"""

def cmd_video(topic: str):
    print_section(f"🎬 SCRIPT DE VIDEO — {topic}")
    print("🧠 Creando script...\n")

    user_text = f"""Creá el script completo para un video sobre: "{topic}"

El video es para el canal de Álvaro (@alvaritonq). Target: traders que quieren aprender
a operar NQ/ES con metodología institucional.

Incluí:
- Script narrado completo (lo que Álvaro dice en voz)
- Indicaciones de pantalla (qué mostrar en cada momento)
- Timestamps aproximados
- CTA al final (hacia la mentoría)"""

    script = ask_claude(SYSTEM_CONTENT, user_text, max_tokens=3000)

    slug = topic.lower().replace(" ", "-")[:40]
    out = BASE_DIR / "content" / "video-scripts" / f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
    out.write_text(f"# Script — {topic}\n\n**Creado:** {datetime.now().strftime('%Y-%m-%d')}\n\n{script}")

    print(script)
    print(f"\n✅ Script guardado en content/video-scripts/")
    log(f"VIDEO SCRIPT: {topic}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 8 — ACCOUNTING (Contabilidad)
# ─────────────────────────────────────────────────────────────────────────────

def cmd_pago(name: str, amount: float):
    acc = load_accounting()
    if name not in acc["students"]:
        acc["students"][name] = {"fecha_inicio": datetime.now().strftime("%Y-%m-%d"), "estado": "activo", "pagos": 0}

    acc["students"][name]["pagos"] = acc["students"][name].get("pagos", 0) + 1
    acc["revenue"].append({
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "alumno": name,
        "monto": amount,
    })
    acc["total"] = acc.get("total", 0) + amount
    save_accounting(acc)

    print(f"✅ Pago registrado: {name} — ${amount}")
    print(f"   Total acumulado: ${acc['total']}")
    log(f"PAYMENT: {name} ${amount}")

# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTO 9 — REPORT (Estado del negocio)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_REPORT = """Sos el Business Analyst de la mentoría de Álvaro Tolentino.
Dado el estado actual del negocio, generá un reporte ejecutivo con:
1. Revenue del mes actual y proyección
2. Alumnos activos, en riesgo, completados
3. MRR (Monthly Recurring Revenue) actual y meta
4. Recomendaciones de crecimiento (qué hacer esta semana para conseguir más alumnos)
5. Alertas (alumnos que faltan pagar, que están estancados, etc.)"""

def cmd_report():
    print_section("💰 REPORTE DEL NEGOCIO")
    acc = load_accounting()

    # Stats básicas
    students_data = acc.get("students", {})
    revenue = acc.get("revenue", [])
    total = acc.get("total", 0)

    activos = [n for n, d in students_data.items() if d.get("estado") == "activo"]
    mrr = len(activos) * 250

    print(f"Alumnos activos: {len(activos)}")
    print(f"MRR actual: ${mrr}")
    print(f"Revenue total acumulado: ${total}")
    print(f"Revenue este mes: ${sum(r['monto'] for r in revenue if r['fecha'].startswith(datetime.now().strftime('%Y-%m')))}")
    print()

    user_text = f"""Estado del negocio de mentoría de Álvaro:
- Alumnos activos: {len(activos)} ({', '.join(activos) if activos else 'ninguno'})
- MRR: ${mrr}
- Total revenue acumulado: ${total}
- Precio del servicio: $250/mes
- Historial de pagos: {json.dumps(revenue[-10:], indent=2)}"""

    analysis = ask_claude(SYSTEM_REPORT, user_text, max_tokens=1000)
    print(analysis)
    log("BUSINESS REPORT GENERATED")

# ─────────────────────────────────────────────────────────────────────────────
# CLI MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "new":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        cmd_new(name)

    elif cmd == "plan":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        cmd_plan(name)

    elif cmd == "prep":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        cmd_prep(name)

    elif cmd == "live":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        cmd_live(name)

    elif cmd == "progress":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        cmd_progress(name)

    elif cmd == "marketing":
        platform = sys.argv[2] if len(sys.argv) > 2 else "instagram"
        cmd_marketing(platform)

    elif cmd == "video":
        topic = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Tema del video: ")
        cmd_video(topic)

    elif cmd == "pago":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Nombre del alumno: ")
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else float(input("Monto: "))
        cmd_pago(name, amount)

    elif cmd == "report":
        cmd_report()

    else:
        print(f"❌ Comando desconocido: '{cmd}'")
        print("Comandos disponibles: new, plan, prep, live, progress, marketing, video, pago, report")

if __name__ == "__main__":
    main()
