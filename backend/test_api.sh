#!/bin/bash
# API Integration Test Script
BASE_URL="http://localhost:8000/api/v1"

echo "=== Testing MeetingMod API ==="
echo ""

# Health check
echo "1. Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# Get principles
echo "2. Get All Principles:"
curl -s "$BASE_URL/principles" | python3 -m json.tool 2>/dev/null || echo "Not implemented yet"
echo ""

# Create meeting
echo "3. Create Meeting:"
MEETING_RESPONSE=$(curl -s -X POST "$BASE_URL/meetings" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Integration Test Meeting",
    "agenda": "Test the API endpoints",
    "participants": [
      {"id": "1", "name": "Alice", "role": "PM"},
      {"id": "2", "name": "Bob", "role": "Dev"}
    ],
    "principleIds": ["agile"]
  }')
echo "$MEETING_RESPONSE" | python3 -m json.tool
MEETING_ID=$(echo "$MEETING_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "Meeting ID: $MEETING_ID"
echo ""

# Get meeting
echo "4. Get Meeting Details:"
curl -s "$BASE_URL/meetings/$MEETING_ID" | python3 -m json.tool 2>/dev/null || echo "Not implemented yet"
echo ""

# Start meeting
echo "5. Start Meeting:"
curl -s -X POST "$BASE_URL/meetings/$MEETING_ID/start" | python3 -m json.tool 2>/dev/null || echo "Not implemented yet"
echo ""

# End meeting
echo "6. End Meeting:"
curl -s -X POST "$BASE_URL/meetings/$MEETING_ID/end" | python3 -m json.tool
echo ""

echo "=== API Tests Complete ==="
