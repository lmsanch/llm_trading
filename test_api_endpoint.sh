#!/bin/bash
# Test script for /api/performance/history endpoint
# Run this after backend is restarted

echo "Testing /api/performance/history endpoint..."
echo ""

# Test 1: COUNCIL account with default days
echo "Test 1: COUNCIL account (7 days default)"
curl -s "http://localhost:8200/api/performance/history?account=COUNCIL" | python3 -m json.tool | head -20
echo ""

# Test 2: CHATGPT account with 14 days
echo "Test 2: CHATGPT account (14 days)"
curl -s "http://localhost:8200/api/performance/history?account=CHATGPT&days=14" | python3 -m json.tool | head -20
echo ""

# Test 3: CLAUDE baseline (should stay flat)
echo "Test 3: CLAUDE baseline (should be flat at 100000)"
curl -s "http://localhost:8200/api/performance/history?account=CLAUDE&days=7" | python3 -m json.tool | head -20
echo ""

# Test 4: Check response structure
echo "Test 4: Verify response structure"
RESPONSE=$(curl -s "http://localhost:8200/api/performance/history?account=COUNCIL&days=7")
echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert 'account' in data, 'Missing account field'
assert 'history' in data, 'Missing history field'
assert len(data['history']) > 0, 'Empty history'
assert 'date' in data['history'][0], 'Missing date field'
assert 'equity' in data['history'][0], 'Missing equity field'
assert 'pl' in data['history'][0], 'Missing pl field'
print('✓ All required fields present')
print(f'✓ Account: {data[\"account\"]}')
print(f'✓ History points: {len(data[\"history\"])}')
"
echo ""
echo "✓ All tests completed!"
