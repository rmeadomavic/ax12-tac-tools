#!/data/data/com.termux/files/usr/bin/bash
# install.sh — ax12-tac-tools bootstrap installer
# One-liner: pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
skip() { echo -e "${YELLOW}[SKIP]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }
info() { echo -e "${CYAN}[INFO]${NC} $*"; }

# ── stdin detection (curl pipe vs interactive) ────────────────────────────────
INTERACTIVE=false
[ -t 0 ] && INTERACTIVE=true

# ── Phase 1: Device Setup ─────────────────────────────────────────────────────
echo -e "\n${BOLD}=== ax12-tac-tools installer ===${NC}"
echo -e "${BOLD}Phase 1 — Device Setup${NC}\n"

# Verify Termux environment
if [ ! -d /data/data/com.termux ]; then
    fail "Not running in Termux. This installer requires Termux on Android."
    exit 1
fi
ok "Termux environment detected"

# Update package lists and upgrade
info "Running pkg update && pkg upgrade..."
pkg update -y && pkg upgrade -y
ok "Packages updated"

# Required packages
REQUIRED_PKGS="python openssh git curl wget"
for pkg in $REQUIRED_PKGS; do
    if dpkg -s "$pkg" &>/dev/null; then
        skip "$pkg already installed"
    else
        info "Installing $pkg..."
        pkg install -y "$pkg"
        ok "$pkg installed"
    fi
done

# Optional advanced packages
ADVANCED_PKGS="binutils dtc strace"
INSTALL_ADVANCED=false

if $INTERACTIVE; then
    echo ""
    read -r -p "Install optional advanced packages (binutils dtc strace)? [y/N] " adv_answer
    case "$adv_answer" in
        [yY][eE][sS]|[yY]) INSTALL_ADVANCED=true ;;
        *) INSTALL_ADVANCED=false ;;
    esac
else
    info "Non-interactive mode — skipping optional advanced packages"
fi

if $INSTALL_ADVANCED; then
    for pkg in $ADVANCED_PKGS; do
        if dpkg -s "$pkg" &>/dev/null; then
            skip "$pkg already installed"
        else
            info "Installing $pkg..."
            pkg install -y "$pkg"
            ok "$pkg installed"
        fi
    done
fi

# ── SSH / sshd setup ──────────────────────────────────────────────────────────
echo ""
info "Configuring sshd..."

if pgrep -x sshd &>/dev/null; then
    skip "sshd already running"
else
    sshd
    ok "sshd started"
fi

# Auto-start via Termux:Boot if available
BOOT_DIR="$HOME/.termux/boot"
SSHD_BOOT="$BOOT_DIR/start-sshd.sh"
TERMUX_BOOT_APP="/data/data/com.termux.boot"

if [ -d "$TERMUX_BOOT_APP" ]; then
    if [ -f "$SSHD_BOOT" ]; then
        skip "Termux:Boot sshd script already exists at $SSHD_BOOT"
    else
        mkdir -p "$BOOT_DIR"
        cat > "$SSHD_BOOT" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
sshd
EOF
        chmod +x "$SSHD_BOOT"
        ok "Termux:Boot auto-start script created at $SSHD_BOOT"
    fi
else
    info "Termux:Boot not installed — sshd won't auto-start on reboot"
fi

# Print SSH connection info
WLAN_IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || true)
echo ""
if [ -n "$WLAN_IP" ]; then
    ok "SSH connection info:"
    info "  Host: $WLAN_IP  Port: 8022"
    info "  Connect: ssh -p 8022 $(whoami)@$WLAN_IP"
else
    info "Could not detect wlan0 IP — check 'ip addr show wlan0' manually"
    info "SSH port: 8022"
fi

# Tailscale prompt
echo ""
INSTALL_TAILSCALE=false

if $INTERACTIVE; then
    read -r -p "Set up Tailscale for remote access? [y/N] " ts_answer
    case "$ts_answer" in
        [yY][eE][sS]|[yY]) INSTALL_TAILSCALE=true ;;
        *) INSTALL_TAILSCALE=false ;;
    esac
else
    info "Non-interactive mode — skipping Tailscale setup"
fi

if $INSTALL_TAILSCALE; then
    echo ""
    info "Tailscale setup — manual steps required:"
    info "  1. Download Tailscale APK: https://pkgs.tailscale.com/stable/#android"
    info "  2. Install via: adb install tailscale.apk  OR  use a file manager"
    info "  3. Open Tailscale app and log in with your Tailscale account"
    info "  4. Enable the VPN — you'll get a stable Tailscale IP for remote SSH"
fi

# ── Phase 2: Tool Install ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Phase 2 — Tool Install${NC}\n"

PYTHON3="/data/data/com.termux/files/usr/bin/python3"
REPO_DIR="$HOME/ax12-tac-tools"
REPO_URL="https://github.com/rmeadomavic/ax12-tac-tools.git"

if [ -d "$REPO_DIR/.git" ]; then
    info "Repo already cloned at $REPO_DIR — pulling latest..."
    git -C "$REPO_DIR" pull --ff-only
    ok "Repo updated"
else
    info "Cloning ax12-tac-tools..."
    git clone "$REPO_URL" "$REPO_DIR"
    ok "Repo cloned to $REPO_DIR"
fi

# Copy Lua scripts
LUA_DEST="/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"
LUA_SRC="$REPO_DIR/lua"

info "Installing Lua scripts to $LUA_DEST..."

if su 0 mkdir -p "$LUA_DEST" 2>/dev/null; then
    ok "Lua destination directory ready"
else
    fail "Could not create $LUA_DEST — root access required"
    info "Run manually: su 0 mkdir -p $LUA_DEST"
fi

LUA_COUNT=0
LUA_FAIL=0
for lua_file in "$LUA_SRC"/*.lua; do
    [ -f "$lua_file" ] || continue
    fname=$(basename "$lua_file")
    if su 0 cp "$lua_file" "$LUA_DEST/$fname" 2>/dev/null; then
        ok "  $fname"
        LUA_COUNT=$((LUA_COUNT + 1))
    else
        fail "  $fname (copy failed)"
        LUA_FAIL=$((LUA_FAIL + 1))
    fi
done
info "$LUA_COUNT Lua scripts installed, $LUA_FAIL failed"

# ── Alias + auto-launch ──────────────────────────────────────────────────────
BASHRC="$HOME/.bashrc"
ALIAS_CMD="alias tac='$PYTHON3 $REPO_DIR/launcher.py'"

touch "$BASHRC"

if grep -q "^alias tac=" "$BASHRC" 2>/dev/null; then
    sed -i "s|^alias tac=.*|$ALIAS_CMD|" "$BASHRC"
    ok "Updated 'tac' alias in ~/.bashrc"
elif grep -q "alias tac=" "$BASHRC" 2>/dev/null; then
    sed -i "s|alias tac=.*|$ALIAS_CMD|" "$BASHRC"
    ok "Updated 'tac' alias in ~/.bashrc"
else
    echo "$ALIAS_CMD" >> "$BASHRC"
    ok "Added 'tac' alias to ~/.bashrc"
fi

# Auto-launch: opening Termux shows the tool menu (not a blank prompt).
# Skipped over SSH so remote access still gets a normal shell.
# Set TAC_NO_MENU=1 in your env to disable.
if grep -q "TAC_NO_MENU" "$BASHRC" 2>/dev/null; then
    skip "Auto-launch already configured"
else
    cat >> "$BASHRC" <<'AUTOLAUNCH'

# AX12 Tactical Tools — open menu on launch (skip over SSH)
if [ -t 0 ] && [ -z "$SSH_CONNECTION" ] && [ -z "$TAC_NO_MENU" ]; then
    /data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/launcher.py
fi
AUTOLAUNCH
    ok "Termux will open the tool menu on launch"
fi

# shellcheck disable=SC1090
source "$BASHRC" 2>/dev/null || true

# ── Home screen shortcuts (Termux:Widget) ─────────────────────────────────────
SHORTCUTS_SRC="$REPO_DIR/shortcuts"
SHORTCUTS_DST="$HOME/.shortcuts"

if [ -d "$SHORTCUTS_SRC" ]; then
    mkdir -p "$SHORTCUTS_DST"
    SC_COUNT=0
    for sc in "$SHORTCUTS_SRC"/*.sh; do
        [ -f "$sc" ] || continue
        cp "$sc" "$SHORTCUTS_DST/"
        chmod +x "$SHORTCUTS_DST/$(basename "$sc")"
        SC_COUNT=$((SC_COUNT + 1))
    done
    ok "$SC_COUNT home screen shortcuts installed"

    if pm list packages 2>/dev/null | grep -q "com.termux.widget"; then
        skip "Termux:Widget already installed"
        info "Long-press home screen > Widgets > Termux:Widget to add buttons"
    else
        info "For home screen buttons, install Termux:Widget from F-Droid:"
        info "  f-droid.org/en/packages/com.termux.widget/"
        info "  Then: long-press home screen > Widgets > Termux:Widget"
    fi
fi

# ── Self-test ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Self-test${NC}\n"

PASS=0
TESTS_FAIL=0

run_test() {
    local label="$1"
    local result="$2"
    local detail="${3:-}"
    if [ "$result" = "ok" ]; then
        ok "$label${detail:+  ($detail)}"
        PASS=$((PASS + 1))
    else
        fail "$label${detail:+  ($detail)}"
        TESTS_FAIL=$((TESTS_FAIL + 1))
    fi
}

# Python version
PY_VER=$(python3 --version 2>&1 || true)
if [ -n "$PY_VER" ]; then
    run_test "Python available" ok "$PY_VER"
else
    run_test "Python available" fail "python3 not found"
fi

# Launcher present
if [ -f "$REPO_DIR/launcher.py" ]; then
    run_test "launcher.py present" ok "$REPO_DIR/launcher.py"
else
    run_test "launcher.py present" fail "not found at $REPO_DIR/launcher.py"
fi

# Lua files in place
LUA_INSTALLED=$(su 0 sh -c "ls '$LUA_DEST'/*.lua 2>/dev/null | wc -l" || echo 0)
if [ "$LUA_INSTALLED" -gt 0 ]; then
    run_test "Lua files installed" ok "$LUA_INSTALLED files in $LUA_DEST"
else
    run_test "Lua files installed" fail "no .lua files found in $LUA_DEST"
fi

# /dev/ttyS0 exists (UART for UMBUS)
if [ -e /dev/ttyS0 ]; then
    run_test "/dev/ttyS0 present" ok
else
    run_test "/dev/ttyS0 present" fail "UART device not found"
fi

# Root access
ROOT_CHECK=$(su 0 id 2>/dev/null || true)
if echo "$ROOT_CHECK" | grep -q "uid=0"; then
    run_test "Root access (su 0)" ok
else
    run_test "Root access (su 0)" fail "su 0 did not return uid=0"
fi

# Shortcuts installed
SC_INSTALLED=$(ls "$SHORTCUTS_DST"/*.sh 2>/dev/null | wc -l || echo 0)
if [ "$SC_INSTALLED" -gt 0 ]; then
    run_test "Home screen shortcuts" ok "$SC_INSTALLED shortcuts in ~/.shortcuts"
else
    run_test "Home screen shortcuts" fail "no shortcuts found"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}=== Install Complete ===${NC}"
echo -e "  Tests passed: ${GREEN}${PASS}${NC}"
echo -e "  Tests failed: ${RED}${TESTS_FAIL}${NC}"
echo ""

if [ "$TESTS_FAIL" -eq 0 ]; then
    ok "Done. Tap Termux to open the tool menu."
    info "Install Termux:Widget from F-Droid for home screen buttons."
else
    info "Completed with $TESTS_FAIL issue(s). Review [FAIL] lines above."
    info "Safe to re-run this script after fixing issues."
fi

echo ""
