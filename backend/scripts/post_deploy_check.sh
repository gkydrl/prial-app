#!/bin/bash
#
# Deploy sonrasi kontrol scripti
# Kullanim: ./scripts/post_deploy_check.sh [BASE_URL]
#
# Ornekler:
#   ./scripts/post_deploy_check.sh
#   ./scripts/post_deploy_check.sh https://prial-app-production.up.railway.app
#

BASE_URL="${1:-https://prial-app-production.up.railway.app}"
PASS=0
FAIL=0
RESULTS=""

check() {
    local name="$1"
    local url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url")

    if [ "$status" = "200" ]; then
        RESULTS="$RESULTS\n  ✓ $name ($status)"
        PASS=$((PASS + 1))
    else
        RESULTS="$RESULTS\n  ✗ $name ($status) ← HATA!"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "═══════════════════════════════════════"
echo "  Prial Deploy Kontrolu"
echo "  $BASE_URL"
echo "═══════════════════════════════════════"
echo ""

# Temel kontroller
check "Health" "$BASE_URL/health"
check "Deep Health" "$BASE_URL/health/deep"

# Kullaniciya acik endpoint'ler (auth gerektirmez)
check "Kategoriler" "$BASE_URL/api/v1/discover/categories"
check "Kesfet Urunler" "$BASE_URL/api/v1/discover/products?page=1&page_size=1"
check "Kategori Urunler" "$BASE_URL/api/v1/discover/categories/akilli-telefon/products?page=1&page_size=1"
check "Gunun Firsatlari" "$BASE_URL/api/v1/home/daily-deals?limit=1"
check "En Cok Dusenler" "$BASE_URL/api/v1/home/top-drops?limit=1"
check "En Cok Takip" "$BASE_URL/api/v1/home/most-alarmed?limit=1"
check "Urun Listesi" "$BASE_URL/api/v1/products?limit=1"
check "Arama" "$BASE_URL/api/v1/discover/search?q=samsung"

echo -e "$RESULTS"
echo ""
echo "═══════════════════════════════════════"

TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo "  SONUC: $PASS/$TOTAL basarili ✓"
else
    echo "  SONUC: $FAIL/$TOTAL BASARISIZ ✗"
fi

echo "═══════════════════════════════════════"
echo ""

# Deep health detayli sonuc
if [ "$FAIL" -gt 0 ]; then
    echo "Deep health detay:"
    curl -s "$BASE_URL/health/deep" | python3 -m json.tool 2>/dev/null
    echo ""
    exit 1
fi
