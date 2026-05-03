#!/bin/bash
# MENTORIA — Para backend + tunnel

echo "🛑 Parando MENTORIA..."

[ -f /tmp/mentoria_api.pid ]    && kill $(cat /tmp/mentoria_api.pid) 2>/dev/null && echo "   Backend detenido"
[ -f /tmp/mentoria_tunnel.pid ] && kill $(cat /tmp/mentoria_tunnel.pid) 2>/dev/null && echo "   Tunnel detenido"

rm -f /tmp/mentoria_api.pid /tmp/mentoria_tunnel.pid
echo "✅ Listo"
