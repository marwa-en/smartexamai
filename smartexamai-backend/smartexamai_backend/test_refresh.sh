#!/bin/bash
BASE="http://127.0.0.1:8000"
PASSWORD="UdFqldpIIVYewZOeTH9QNHit"   # ← CHANGE ICI

echo "=== 1. Login (obtention refresh token) ==="
LOGIN=$(curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$PASSWORD\"}")
REFRESH1=$(echo "$LOGIN" | python -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")
echo "refresh 1 : ${REFRESH1:0:20}..."

echo ""
echo "=== 2. Refresh (rotation : nouveau token émis) ==="
RESP2=$(curl -s -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH1\"}")
REFRESH2=$(echo "$RESP2" | python -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")
echo "refresh 2 : ${REFRESH2:0:20}..."

echo ""
echo "=== 3. Rejouer l'ANCIEN token (doit échouer 401 + révoquer la famille) ==="
curl -s -w "\nHTTP: %{http_code}\n" -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH1\"}"

echo ""
echo "=== 4. Le token 2 doit aussi être révoqué (famille entière tuée) ==="
curl -s -w "\nHTTP: %{http_code}\n" -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH2\"}"

echo ""
echo "=== 5. Nouveau login + logout ==="
LOGIN3=$(curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$PASSWORD\"}")
REFRESH3=$(echo "$LOGIN3" | python -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")

curl -s -X POST $BASE/api/auth/logout \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH3\"}"
echo ""

echo ""
echo "=== 6. Le token déconnecté ne doit plus fonctionner (401) ==="
curl -s -w "\nHTTP: %{http_code}\n" -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH3\"}"
