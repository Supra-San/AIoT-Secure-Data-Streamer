#!/bin/bash
# =============================================================================
#  setup.sh — AIoT Secure Data Streamer: Full Initial Setup
#  Handles: PKI (CA & Server Cert), Mosquitto passwd, ACL, mosquitto.conf, .env
# =============================================================================

set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
step()  { echo -e "\n${CYAN}[${1}]${NC} ${BOLD}${2}${NC}"; }
ok()    { echo -e "      ${GREEN}✓${NC} ${1}"; }
info()  { echo -e "      ${DIM}${1}${NC}"; }
warn()  { echo -e "  ${YELLOW}⚠ ${1}${NC}"; }
err()   { echo -e "  ${RED}✗ ERROR: ${1}${NC}"; exit 1; }
hr()    { echo -e "${DIM}────────────────────────────────────────────────────${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║    AIoT Secure Data Streamer — Full Initial Setup      ║"
echo "║    PKI · Credentials · ACL · Mosquitto Config · .env  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Check dependencies ────────────────────────────────────────────────────────
for cmd in openssl mosquitto_passwd; do
    if ! command -v "$cmd" &>/dev/null; then
        err "'$cmd' is not installed.\n  Ubuntu/Debian: sudo apt install openssl mosquitto"
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 1 — Collect user inputs
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${MAGENTA}${BOLD}Section 1 · Configuration${NC}"
hr

# Broker IP
echo -e "The ${BOLD}Common Name (CN)${NC} in the certificate must match your broker's IP/hostname."
read -rp "$(echo -e "${BOLD}  Broker IP Address (e.g. 192.168.1.100): ${NC}")" BROKER_IP
[[ -z "$BROKER_IP" ]] && err "Broker IP cannot be empty."

# Cert validity
read -rp "$(echo -e "${BOLD}  Certificate validity in days [365]: ${NC}")" CERT_DAYS
CERT_DAYS=${CERT_DAYS:-365}

echo ""
hr

# MQTT username & password
echo -e "${MAGENTA}${BOLD}Section 2 · MQTT Credentials${NC}"
hr
echo -e "This username/password is used by the ${BOLD}ESP32 publisher${NC} and ${BOLD}Python subscriber${NC}."
read -rp "$(echo -e "${BOLD}  MQTT Username: ${NC}")" MQTT_USER
[[ -z "$MQTT_USER" ]] && err "MQTT username cannot be empty."

read -srp "$(echo -e "${BOLD}  MQTT Password: ${NC}")" MQTT_PASS
echo ""
[[ -z "$MQTT_PASS" ]] && err "MQTT password cannot be empty."

read -srp "$(echo -e "${BOLD}  Confirm Password: ${NC}")" MQTT_PASS2
echo ""
[[ "$MQTT_PASS" != "$MQTT_PASS2" ]] && err "Passwords do not match."

echo ""
hr

# MQTT Topic
echo -e "${MAGENTA}${BOLD}Section 3 · MQTT Topics${NC}"
hr
read -rp "$(echo -e "${BOLD}  Data Topic (e.g. sensor/suhu/room1): ${NC}")" MQTT_TOPIC
[[ -z "$MQTT_TOPIC" ]] && err "MQTT topic cannot be empty."

read -rp "$(echo -e "${BOLD}  Status/LWT Topic (e.g. sensor/suhu/room1/status): ${NC}")" MQTT_STATUS_TOPIC
[[ -z "$MQTT_STATUS_TOPIC" ]] && err "MQTT status topic cannot be empty."

echo ""
hr

# Resolve absolute project root (directory where this script lives)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Summary before proceeding
echo -e "${MAGENTA}${BOLD}Summary${NC}"
hr
echo -e "  Broker IP      : ${BOLD}${BROKER_IP}${NC}"
echo -e "  Cert validity  : ${BOLD}${CERT_DAYS} days${NC}"
echo -e "  MQTT User      : ${BOLD}${MQTT_USER}${NC}"
echo -e "  Data Topic     : ${BOLD}${MQTT_TOPIC}${NC}"
echo -e "  Status Topic   : ${BOLD}${MQTT_STATUS_TOPIC}${NC}"
echo -e "  Project Root   : ${DIM}${PROJECT_ROOT}${NC}"
hr
read -rp "$(echo -e "\n${BOLD}Proceed with setup? (y/N): ${NC}")" CONFIRM
[[ ! "$CONFIRM" =~ ^[Yy]$ ]] && { echo -e "${YELLOW}Aborted.${NC}"; exit 0; }

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION A — Folder structure
# ─────────────────────────────────────────────────────────────────────────────
step "A" "Creating directory structure"
mkdir -p pki certs config security
ok "pki/ certs/ config/ security/ — ready"

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION B — PKI: CA key + certificate
# ─────────────────────────────────────────────────────────────────────────────
step "B" "Generating Certificate Authority (CA)"

if [[ -f pki/ca.key && -f certs/ca.crt ]]; then
    warn "CA files already exist. Skipping CA generation."
    warn "Delete pki/ca.key and certs/ca.crt manually to regenerate."
else
    info "Generating CA private key → pki/ca.key"
    openssl genrsa -out pki/ca.key 2048 2>/dev/null

    info "Generating CA self-signed certificate → certs/ca.crt"
    openssl req -new -x509 \
        -days "$CERT_DAYS" \
        -key pki/ca.key \
        -out certs/ca.crt \
        -subj "/CN=${BROKER_IP}/O=AIoT-Secure/OU=CA" 2>/dev/null
    ok "CA certificate generated (CN=${BROKER_IP}, valid ${CERT_DAYS} days)"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION C — Server key + CSR + signed certificate
# ─────────────────────────────────────────────────────────────────────────────
step "C" "Generating Server (Broker) Certificate"

if [[ -f certs/server.crt && -f certs/server.key ]]; then
    warn "Server cert/key already exist. Skipping server cert generation."
else
    info "Generating server private key → certs/server.key"
    openssl genrsa -out certs/server.key 2048 2>/dev/null

    info "Generating CSR → pki/server.csr"
    openssl req -new \
        -key certs/server.key \
        -out pki/server.csr \
        -subj "/CN=${BROKER_IP}/O=AIoT-Secure/OU=Broker" 2>/dev/null

    info "Signing server certificate with CA → certs/server.crt"
    openssl x509 -req \
        -in pki/server.csr \
        -CA certs/ca.crt \
        -CAkey pki/ca.key \
        -CAcreateserial \
        -out certs/server.crt \
        -days "$CERT_DAYS" 2>/dev/null
    ok "Server certificate signed and ready"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION D — Mosquitto password file
# ─────────────────────────────────────────────────────────────────────────────
step "D" "Creating Mosquitto password file"

PASSWD_FILE="${PROJECT_ROOT}/config/passwd"

# -c creates new file (overwrites), -b reads password from arg (non-interactive)
mosquitto_passwd -c -b "$PASSWD_FILE" "$MQTT_USER" "$MQTT_PASS"
ok "Password file created → config/passwd"
info "User '${MQTT_USER}' registered with hashed password"

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION E — ACL file
# ─────────────────────────────────────────────────────────────────────────────
step "E" "Creating ACL file"

ACL_FILE="${PROJECT_ROOT}/security/acl"

cat > "$ACL_FILE" <<EOF
# Access Control List — generated by setup.sh

user ${MQTT_USER}

# Read & Write access to data topic
topic readwrite ${MQTT_TOPIC}

# Read & Write access to LWT/status topic
topic readwrite ${MQTT_STATUS_TOPIC}
EOF

ok "ACL file created → security/acl"
info "User '${MQTT_USER}' granted readwrite on:"
info "  ${MQTT_TOPIC}"
info "  ${MQTT_STATUS_TOPIC}"

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION F — mosquitto.conf
# ─────────────────────────────────────────────────────────────────────────────
step "F" "Generating mosquitto.conf"

CONF_FILE="${PROJECT_ROOT}/config/mosquitto.conf"

cat > "$CONF_FILE" <<EOF
# mosquitto.conf — generated by setup.sh
# Listener for TLS (MQTTS on port 8883)
listener 8883

# TLS Certificates (absolute paths)
cafile ${PROJECT_ROOT}/certs/ca.crt
certfile ${PROJECT_ROOT}/certs/server.crt
keyfile ${PROJECT_ROOT}/certs/server.key

# Disable anonymous access
allow_anonymous false

# Authentication
password_file ${PROJECT_ROOT}/config/passwd
acl_file ${PROJECT_ROOT}/security/acl
EOF

ok "mosquitto.conf created → config/mosquitto.conf"
info "All paths are absolute: ${PROJECT_ROOT}/..."

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION G — .env file
# ─────────────────────────────────────────────────────────────────────────────
step "G" "Generating .env file"

ENV_FILE="${PROJECT_ROOT}/.env"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — backing up to .env.bak"
    cp "$ENV_FILE" "${ENV_FILE}.bak"
fi

cat > "$ENV_FILE" <<EOF
MQTT_BROKER=${BROKER_IP}
MQTT_PORT=8883
MQTT_USER=${MQTT_USER}
MQTT_PASS=${MQTT_PASS}
MQTT_TOPIC=${MQTT_TOPIC}
MQTT_STATUS_TOPIC=${MQTT_STATUS_TOPIC}
CA_CERT_PATH=${PROJECT_ROOT}/certs/ca.crt
EOF

ok ".env file written → .env"

# ─────────────────────────────────────────────────────────────────────────────
#  Final summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════╗"
echo -e "║             Setup Complete! 🚀                         ║"
echo -e "╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Files generated:${NC}"
echo -e "  ├── certs/ca.crt       ${CYAN}← Copy this content into edge/secrets.h${NC}"
echo -e "  ├── certs/server.crt"
echo -e "  ├── certs/server.key"
echo -e "  ├── pki/ca.key         ${YELLOW}← KEEP SECRET — never commit or share${NC}"
echo -e "  ├── pki/server.csr"
echo -e "  ├── config/mosquitto.conf"
echo -e "  ├── config/passwd"
echo -e "  ├── security/acl"
echo -e "  └── .env"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "  1. ${CYAN}Copy${NC} contents of ${BOLD}certs/ca.crt${NC} into ${BOLD}edge/secrets.h${NC} (SECRET_CA_CERT)"
echo -e "  2. ${CYAN}Update${NC} ${BOLD}edge/secrets.h${NC} with WiFi, IP, username (${MQTT_USER}), and password"
echo -e "  3. ${CYAN}Flash${NC} the ESP32 via Arduino IDE"
echo -e "  4. ${CYAN}Start${NC} broker:    ${BOLD}mosquitto -c config/mosquitto.conf -v${NC}"
echo -e "  5. ${CYAN}Run${NC} subscriber:  ${BOLD}python3 app_subscriber.py${NC}"
echo ""
echo -e "  ${YELLOW}⚠  Reminder:${NC} pki/ and .env are in .gitignore — never commit them."
echo ""
