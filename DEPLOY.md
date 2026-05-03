# Deploy — Sistema MENTORIA

## Stack

- **Frontend** (`web/index.html`) → Netlify (gratis)
- **Backend** (`api/main.py`) → Render.com (gratis)
- **Dominio custom** → apuntás a Netlify

---

## 1. Backend — Render.com (gratis)

### Setup inicial

1. Ir a [render.com](https://render.com) → Create → Web Service
2. Conectar tu GitHub (subís la carpeta MENTORIA como repo)
3. Configuración:
   - **Root Directory:** `api`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3
4. Variables de entorno en Render:
   - `ANTHROPIC_API_KEY` = tu key de Anthropic

### URL del backend
Render te da algo como: `https://mentoria-api.onrender.com`

⚠️ **Render gratis se duerme después de 15min sin tráfico.** El primer request puede tardar 30s.
Para evitarlo: upgrade a $7/mes (Starter) o usar [UptimeRobot](https://uptimerobot.com) gratuito para ping cada 14min.

---

## 2. Frontend — Netlify (gratis)

### Opción A — Drag & drop (más fácil)

1. Ir a [netlify.com](https://netlify.com) → Add new site → Deploy manually
2. Arrastrá la carpeta `web/` al área de upload
3. Listo — te da URL tipo `https://amazing-name.netlify.app`

### Opción B — Git (recomendado para actualizaciones fáciles)

1. Subís MENTORIA a GitHub
2. Netlify → Add new site → Import from Git → elegís el repo
3. Build settings: **Publish directory:** `web`

### Conectar con el backend (IMPORTANTE)

En `web/index.html`, buscar esta línea (cerca del final del script):

```javascript
const res = await fetch('/api/apply', {
```

Cambiar a la URL de Render:

```javascript
const res = await fetch('https://mentoria-api.onrender.com/api/apply', {
```

---

## 3. Dominio custom (opcional)

1. Comprás el dominio (Namecheap, GoDaddy, Porkbun — el más barato)
2. En Netlify → Site settings → Domain management → Add custom domain
3. Seguís las instrucciones para apuntar los nameservers a Netlify
4. SSL automático (HTTPS) — Netlify lo configura solo

---

## 4. Correr en local (para probar)

```bash
cd /Users/Joaquin/Desktop/MENTORIA

# Instalar dependencias del backend
pip3 install -r api/requirements.txt

# Correr el backend
python3 api/main.py
# → http://localhost:8000

# En otra terminal — servir el frontend
python3 -m http.server 3000 --directory web
# → http://localhost:3000
```

Para que el frontend conecte al backend local, en `index.html` cambiar:
```javascript
const res = await fetch('http://localhost:8000/api/apply', {
```

---

## 5. Verificar que funciona

```bash
# Health check
curl http://localhost:8000/health

# Test aplicación
curl -X POST http://localhost:8000/api/apply \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan Test","email":"juan@test.com","experiencia":"1 año","problema":"no sé entrar"}'

# Ver aplicaciones recibidas
curl http://localhost:8000/api/applications

# Ver alumnos
curl http://localhost:8000/api/students
```

---

## 6. Workflow de una nueva aplicación

1. Visitante llena formulario en tu dominio
2. Frontend hace POST a `/api/apply` en Render
3. Backend:
   - Guarda raw en `MENTORIA/applications/YYYY-MM-DD-HHMMSS-nombre.json`
   - Crea `MENTORIA/students/nombre/profile.json`
   - Genera análisis IA con Claude → `MENTORIA/students/nombre/onboarding.md`
   - Registra en `MENTORIA/accounting/registro.json`
4. Vos ves la aplicación con:
   ```bash
   python3 mentor.py report
   # o
   curl https://mentoria-api.onrender.com/api/applications
   ```
5. Cuando aceptás al alumno, corrés:
   ```bash
   python3 mentor.py plan "Juan Pérez"
   ```

---

*Última actualización: 2026-04-30*
