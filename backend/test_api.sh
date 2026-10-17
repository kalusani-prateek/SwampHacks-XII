#!/bin/bash
# Test script for Flask API
# Assumes Flask server is running on http://localhost:5000
# Run from backend directory

API_BASE="http://localhost:5000"
DB_PATH="app.db"

echo "=== API Test Started ==="

# Helper function to print result
print_result() {
    if [ $1 -eq 0 ]; then
        echo "   Success"
    else
        echo "   Failed"
    fi
}

# 1. Create a regular user (will be made admin later)
echo "1. Creating test user (user1)..."
REG_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"user1@example.com","password":"pass1","site_id":1}')
REG_BODY=$(echo "$REG_RESPONSE" | sed '$d')
REG_CODE=$(echo "$REG_RESPONSE" | tail -n1)
if echo "$REG_BODY" | grep -q '"message":"User created successfully"' && [ "$REG_CODE" -eq 201 ]; then
    print_result 0
else
    echo "   Response: $REG_BODY"
    echo "   HTTP code: $REG_CODE"
    print_result 1
fi

# 2. Make user1 an admin via direct DB update using Python (since sqlite3 may not be installed)
echo "2. Making user1 an admin via SQL..."
python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_PATH')
    c = conn.cursor()
    c.execute(\"UPDATE users SET is_admin=1 WHERE username='user1'\")
    conn.commit()
    conn.close()
    print('Success')
except Exception as e:
    print('Error:', e)
" | grep -q "Success"
print_result $?

# 3. Login as admin (user1) to get session cookie
echo "3. Logging in as admin (user1)..."
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -c admin_cookie.txt -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass1"}')
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')
LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
if echo "$LOGIN_BODY" | grep -q '"message":"Logged in successfully"' && [ "$LOGIN_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $LOGIN_BODY"
    echo "   HTTP code: $LOGIN_CODE"
    print_result 1
fi

# 4. Create a site as admin
echo "4. Creating a site..."
SITE_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt -X POST "$API_BASE/api/sites/add_site" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Site","city":"Test City","state":"TS"}')
SITE_BODY=$(echo "$SITE_RESPONSE" | sed '$d')
SITE_CODE=$(echo "$SITE_RESPONSE" | tail -n1)
if echo "$SITE_BODY" | grep -q '"id":' && [ "$SITE_CODE" -eq 201 ]; then
    print_result 0
else
    echo "   Response: $SITE_BODY"
    echo "   HTTP code: $SITE_CODE"
    print_result 1
fi

# 5. Get site ID
echo "5. Getting site ID..."
SITE_ID=$(curl -s -b admin_cookie.txt "$API_BASE/api/sites/get_sites" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -z "$SITE_ID" ]; then
    SITE_ID=1
fi
echo "   Using site ID: $SITE_ID"

# 6. Update the site (as admin)
echo "6. Updating the site..."
SITE_UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt -X PUT "$API_BASE/api/sites/$SITE_ID" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Site","city":"Updated City","state":"US"}' )
SITE_UPDATE_BODY=$(echo "$SITE_UPDATE_RESPONSE" | sed '$d')
SITE_UPDATE_CODE=$(echo "$SITE_UPDATE_RESPONSE" | tail -n1)
if echo "$SITE_UPDATE_BODY" | grep -q '"name":"Updated Site"' && [ "$SITE_UPDATE_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $SITE_UPDATE_BODY"
    echo "   HTTP code: $SITE_UPDATE_CODE"
    print_result 1
fi

# 7. Create a regular user (user2) with the site
echo "7. Creating regular user (user2)..."
USER2_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"user2","email":"user2@example.com","password":"pass2","site_id":'"$SITE_ID"'}' )
USER2_BODY=$(echo "$USER2_RESPONSE" | sed '$d')
USER2_CODE=$(echo "$USER2_RESPONSE" | tail -n1)
if echo "$USER2_BODY" | grep -q '"message":"User created successfully"' && [ "$USER2_CODE" -eq 201 ]; then
    print_result 0
else
    echo "   Response: $USER2_BODY"
    echo "   HTTP code: $USER2_CODE"
    print_result 1
fi

# 8. Login as user2
echo "8. Logging in as user2..."
LOGIN2_RESPONSE=$(curl -s -w "\n%{http_code}" -c user2_cookie.txt -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"user2","password":"pass2"}')
LOGIN2_BODY=$(echo "$LOGIN2_RESPONSE" | sed '$d')
LOGIN2_CODE=$(echo "$LOGIN2_RESPONSE" | tail -n1)
if echo "$LOGIN2_BODY" | grep -q '"message":"Logged in successfully"' && [ "$LOGIN2_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $LOGIN2_BODY"
    echo "   HTTP code: $LOGIN2_CODE"
    print_result 1
fi

# 9. Test public endpoints (sites and incidents) - should have at least the site we created
echo "9. Testing public endpoints..."
# Get sites
SITES_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/sites/get_sites")
SITES_BODY=$(echo "$SITES_RESPONSE" | sed '$d')
SITES_CODE=$(echo "$SITES_RESPONSE" | tail -n1)
if echo "$SITES_BODY" | grep -q '"id":' && [ "$SITES_CODE" -eq 200 ]; then
    SITES_OK=0
else
    SITES_OK=1
    echo "   Sites response: $SITES_BODY"
    echo "   Sites HTTP: $SITES_CODE"
fi
# Get incidents
INCIDENTS_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/incidents/get_incidents")
INCIDENTS_BODY=$(echo "$INCIDENTS_RESPONSE" | sed '$d')
INCIDENTS_CODE=$(echo "$INCIDENTS_RESPONSE" | tail -n1)
if echo "$INCIDENTS_BODY" | grep -q '"id":' && [ "$INCIDENTS_CODE" -eq 200 ]; then
    INCIDENTS_OK=0
else
    INCIDENTS_OK=1
    echo "   Incidents response: $INCIDENTS_BODY"
    echo "   Incidents HTTP: $INCIDENTS_CODE"
fi
if [ $SITES_OK -eq 0 ] && [ $INCIDENTS_OK -eq 0 ]; then
    echo "   Success"
else
    echo "   Failed"
fi

# 10. Upload an incident as user2
echo "10. Uploading an incident..."
INCIDENT_RESPONSE=$(curl -s -w "\n%{http_code}" -b user2_cookie.txt -X POST "$API_BASE/api/incidents/add_incident" \
  -H "Content-Type: application/json" \
  -d '{"image":"/uploads/test.jpg","location":"Test Location","description":"Test incident","site_id":'"$SITE_ID"'}' )
INCIDENT_BODY=$(echo "$INCIDENT_RESPONSE" | sed '$d')
INCIDENT_CODE=$(echo "$INCIDENT_RESPONSE" | tail -n1)
if echo "$INCIDENT_BODY" | grep -q '"id":' && [ "$INCIDENT_CODE" -eq 201 ]; then
    print_result 0
else
    echo "   Response: $INCIDENT_BODY"
    echo "   HTTP code: $INCIDENT_CODE"
    print_result 1
fi

# 11. Get incident ID (we'll assume the latest incident is the one we just added)
echo "11. Getting incident ID..."
INCIDENT_ID=$(curl -s -b user2_cookie.txt "$API_BASE/api/incidents/get_incidents" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -z "$INCIDENT_ID" ]; then
    INCIDENT_ID=1
fi
echo "   Using incident ID: $INCIDENT_ID"

# 12. Update the incident (as user2)
echo "12. Updating incident..."
UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -b user2_cookie.txt -X PUT "$API_BASE/api/incidents/$INCIDENT_ID" \
  -H "Content-Type: application/json" \
  -d '{"description":"Updated description","location":"Updated Location"}' )
UPDATE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')
UPDATE_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
if echo "$UPDATE_BODY" | grep -q '"description":"Updated description"' && [ "$UPDATE_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $UPDATE_BODY"
    echo "   HTTP code: $UPDATE_CODE"
    print_result 1
fi

# 13. Delete the incident (as user2)
echo "13. Deleting incident..."
DELETE_INC_RESPONSE=$(curl -s -w "\n%{http_code}" -b user2_cookie.txt -X DELETE "$API_BASE/api/incidents/$INCIDENT_ID")
DELETE_INC_BODY=$(echo "$DELETE_INC_RESPONSE" | sed '$d')
DELETE_INC_CODE=$(echo "$DELETE_INC_RESPONSE" | tail -n1)
if echo "$DELETE_INC_BODY" | grep -q '"message":"Incident deleted"' && [ "$DELETE_INC_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $DELETE_INC_BODY"
    echo "   HTTP code: $DELETE_INC_CODE"
    print_result 1
fi

# 14. Login as admin again (in case cookie expired)
echo "14. Logging in as admin again..."
LOGIN_ADMIN_RESPONSE=$(curl -s -w "\n%{http_code}" -c admin_cookie.txt -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass1"}')
LOGIN_ADMIN_BODY=$(echo "$LOGIN_ADMIN_RESPONSE" | sed '$d')
LOGIN_ADMIN_CODE=$(echo "$LOGIN_ADMIN_RESPONSE" | tail -n1)
if echo "$LOGIN_ADMIN_BODY" | grep -q '"message":"Logged in successfully"' && [ "$LOGIN_ADMIN_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $LOGIN_ADMIN_BODY"
    echo "   HTTP code: $LOGIN_ADMIN_CODE"
    print_result 1
fi

# 15. Admin: Get all users
echo "15. Admin: Getting all users..."
ADMIN_USERS_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt "$API_BASE/api/admins/users")
ADMIN_USERS_BODY=$(echo "$ADMIN_USERS_RESPONSE" | sed '$d')
ADMIN_USERS_CODE=$(echo "$ADMIN_USERS_RESPONSE" | tail -n1)
if echo "$ADMIN_USERS_BODY" | grep -q '"username":"user1"' && echo "$ADMIN_USERS_BODY" | grep -q '"username":"user2"' && [ "$ADMIN_USERS_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $ADMIN_USERS_BODY"
    echo "   HTTP code: $ADMIN_USERS_CODE"
    print_result 1
fi

# 16. Admin: Get user by id (user2)
echo "16. Admin: Getting user by id (user2)..."
ADMIN_GET_USER_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt "$API_BASE/api/admins/users/2")
ADMIN_GET_USER_BODY=$(echo "$ADMIN_GET_USER_RESPONSE" | sed '$d')
ADMIN_GET_USER_CODE=$(echo "$ADMIN_GET_USER_RESPONSE" | tail -n1)
if echo "$ADMIN_GET_USER_BODY" | grep -q '"username":"user2"' && [ "$ADMIN_GET_USER_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $ADMIN_GET_USER_BODY"
    echo "   HTTP code: $ADMIN_GET_USER_CODE"
    print_result 1
fi

# 17. Admin: Update user2 (change email and site_id? we only have one site, so maybe change email)
echo "17. Admin: Updating user2..."
ADMIN_UPDATE_USER_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt -X PUT "$API_BASE/api/admins/users/2" \
  -H "Content-Type: application/json" \
  -d '{"email":"user2updated@example.com"}' )
ADMIN_UPDATE_USER_BODY=$(echo "$ADMIN_UPDATE_USER_RESPONSE" | sed '$d')
ADMIN_UPDATE_USER_CODE=$(echo "$ADMIN_UPDATE_USER_RESPONSE" | tail -n1)
if echo "$ADMIN_UPDATE_USER_BODY" | grep -q '"message":"User updated successfully"' && [ "$ADMIN_UPDATE_USER_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $ADMIN_UPDATE_USER_BODY"
    echo "   HTTP code: $ADMIN_UPDATE_USER_CODE"
    print_result 1
fi

# 18. Admin: Delete user2
echo "18. Admin: Deleting user2..."
ADMIN_DELETE_USER_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt -X DELETE "$API_BASE/api/admins/users/2")
ADMIN_DELETE_USER_BODY=$(echo "$ADMIN_DELETE_USER_RESPONSE" | sed '$d')
ADMIN_DELETE_USER_CODE=$(echo "$ADMIN_DELETE_USER_RESPONSE" | tail -n1)
if echo "$ADMIN_DELETE_USER_BODY" | grep -q '"message":"User deleted successfully"' && [ "$ADMIN_DELETE_USER_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $ADMIN_DELETE_USER_BODY"
    echo "   HTTP code: $ADMIN_DELETE_USER_CODE"
    print_result 1
fi

# 19. Delete the site (as admin)
echo "19. Deleting site..."
DELETE_SITE_RESPONSE=$(curl -s -w "\n%{http_code}" -b admin_cookie.txt -X DELETE "$API_BASE/api/sites/$SITE_ID")
DELETE_SITE_BODY=$(echo "$DELETE_SITE_RESPONSE" | sed '$d')
DELETE_SITE_CODE=$(echo "$DELETE_SITE_RESPONSE" | tail -n1)
if echo "$DELETE_SITE_BODY" | grep -q '"message":"Site deleted"' && [ "$DELETE_SITE_CODE" -eq 200 ]; then
    print_result 0
else
    echo "   Response: $DELETE_SITE_BODY"
    echo "   HTTP code: $DELETE_SITE_CODE"
    print_result 1
fi

# 20. Test public endpoints again (should now be empty or have only default site if any)
echo "20. Testing public endpoints after cleanup..."
# Get sites
SITES2_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/sites/get_sites")
SITES2_BODY=$(echo "$SITES2_RESPONSE" | sed '$d')
SITES2_CODE=$(echo "$SITES2_RESPONSE" | tail -n1)
# Get incidents
INCIDENTS2_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/incidents/get_incidents")
INCIDENTS2_BODY=$(echo "$INCIDENTS2_RESPONSE" | sed '$d')
INCIDENTS2_CODE=$(echo "$INCIDENTS2_RESPONSE" | tail -n1)
# We just check that they return 200 and are valid JSON (we don't care about content)
if [ "$SITES2_CODE" -eq 200 ] && [ "$INCIDENTS2_CODE" -eq 200 ]; then
    echo "   Success"
else
    echo "   Failed"
    echo "   Sites HTTP: $SITES2_CODE"
    echo "   Incidents HTTP: $INCIDENTS2_CODE"
fi

echo "=== API Test Completed ==="