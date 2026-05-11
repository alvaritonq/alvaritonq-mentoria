#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# DEPLOY SCRIPT — AlvaritoNQ Landing Page
# ──────────────────────────────────────────────────────────────────
# Sube solo los cambios necesarios al sitio web (web/ + api/)
# NO sube datos internos (vault Obsidian, alumnos, etc.)
#
# Uso:
#   bash deploy.sh "mensaje del commit"
#
# Después del push, ir a Render dashboard y dale "Manual Deploy"
# ──────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

# Mensaje del commit (argumento o default)
MSG="${1:-Update sitio web — lanzamiento ebook + bootcamp + mentoria}"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🚀 DEPLOY ALVARITONQ.ME"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Mostrar lo que va a entrar al commit
echo "📦 Archivos del sitio web a commitear:"
echo ""
git add web/ api/ DEPLOY.md render.yaml mentor.py start.sh stop.sh requirements.txt .gitignore deploy.sh 2>/dev/null || true
git status --short
echo ""

read -p "¿Confirmar commit y push? (s/n): " confirm
if [ "$confirm" != "s" ] && [ "$confirm" != "S" ] && [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "❌ Cancelado. No se hizo commit ni push."
  exit 0
fi

# Commit
echo ""
echo "💾 Creando commit..."
git commit -m "$MSG"

# Push
echo ""
echo "🌐 Pusheando a origin/main..."
git push origin main

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ PUSH COMPLETADO"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "👉 SIGUIENTE PASO MANUAL:"
echo ""
echo "   1. Entra a Render: https://dashboard.render.com"
echo "   2. Selecciona el servicio de alvaritonq.me"
echo "   3. Click en 'Manual Deploy' → 'Deploy latest commit'"
echo "   4. Espera 1-2 minutos a que termine el build"
echo "   5. Verifica que alvaritonq.me cargó los cambios"
echo ""
echo "═══════════════════════════════════════════════════════════"
