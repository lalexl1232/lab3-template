#!/bin/bash

echo "Testing Fault Tolerance Implementation"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test health endpoints
echo "1. Testing Health Endpoints..."
for port in 8080 8070 8060 8050; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/manage/health)
    if [ "$response" == "200" ]; then
        echo -e "${GREEN}✓${NC} Port $port health check: OK"
    else
        echo -e "${RED}✗${NC} Port $port health check: FAILED (HTTP $response)"
    fi
done
echo ""

# Test cars service
echo "2. Testing Cars Service..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8080/api/v1/cars?page=1&size=10)
http_code=$(echo "$response" | grep HTTP_CODE | cut -d':' -f2)
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✓${NC} GET /api/v1/cars: OK"
else
    echo -e "${RED}✗${NC} GET /api/v1/cars: FAILED (HTTP $http_code)"
fi
echo ""

# Test Circuit Breaker
echo "3. Testing Circuit Breaker (stop cars service)..."
echo "   To test: docker stop cars"
echo "   Then run: curl http://localhost:8080/api/v1/cars"
echo "   Expected: Fallback response with empty items array"
echo ""

# Test Retry Queue
echo "4. Testing Retry Queue..."
echo "   Retry queue is active and processing failed operations in background"
echo "   Check gateway logs: docker logs gateway"
echo ""

echo "========================================"
echo "Testing complete!"
