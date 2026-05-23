#!/usr/bin/env bash
# mw_setup_check.sh — verify a machine is ready to run MobileWorld eval.
# Usage:  bash Mobile-Agent-E/instr_rewrite/mw_setup_check.sh
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MW="$REPO/MobileWorld/MobileWorld"
PASS="\033[32m✓\033[0m"; FAIL="\033[31m✗\033[0m"; WARN="\033[33m!\033[0m"
fail=0

echo "== MobileWorld readiness check =="
echo "repo: $REPO"

# 1. CPU virtualization
n=$(grep -E '(vmx|svm)' /proc/cpuinfo 2>/dev/null | wc -l)
if [ "$n" -gt 0 ]; then echo -e "$PASS CPU virtualization (vmx/svm count=$n)";
else echo -e "$FAIL CPU virtualization NOT exposed (vmx/svm=0) — KVM impossible here"; fail=1; fi

# 2. Not a nested VM
virt=$(systemd-detect-virt 2>/dev/null || echo unknown)
if [ "$virt" = "none" ]; then echo -e "$PASS bare metal (systemd-detect-virt=none)";
else echo -e "$WARN running inside '$virt' — KVM needs nested virtualization enabled"; fi

# 3. /dev/kvm
if [ -e /dev/kvm ]; then echo -e "$PASS /dev/kvm present";
else
  echo -e "$WARN /dev/kvm missing — trying modprobe ..."
  sudo modprobe kvm_intel 2>/dev/null || sudo modprobe kvm_amd 2>/dev/null || true
  if [ -e /dev/kvm ]; then echo -e "$PASS /dev/kvm appeared after modprobe";
  else echo -e "$FAIL /dev/kvm still missing — emulator cannot run"; fail=1; fi
fi

# 4. Docker
if command -v docker >/dev/null && docker ps >/dev/null 2>&1; then
  echo -e "$PASS docker usable (no sudo)";
elif command -v docker >/dev/null && sudo docker ps >/dev/null 2>&1; then
  echo -e "$WARN docker needs sudo — prepend 'sudo ' to --mw-cmd / env run";
else echo -e "$FAIL docker not usable"; fail=1; fi

# 5. mw venv binary
if [ -x "$MW/.venv/bin/mw" ]; then echo -e "$PASS mw venv binary ($MW/.venv/bin/mw)";
else echo -e "$FAIL mw venv missing — run 'cd $MW && uv sync'"; fail=1; fi

# 6. .env
if [ -f "$MW/.env" ]; then
  echo -e "$PASS .env present"
  for k in API_KEY DASHSCOPE_API_KEY USER_AGENT_API_KEY; do
    v=$(grep -E "^$k=" "$MW/.env" | head -1 | cut -d= -f2-)
    case "$v" in
      ""|*TODO*|*your_*|*_for_*) echo -e "   $WARN $k looks unset ('$v')";;
      *) echo -e "   $PASS $k set";;
    esac
  done
else echo -e "$FAIL $MW/.env missing — cp .env.example .env"; fail=1; fi

echo
if [ "$fail" -eq 0 ]; then
  echo -e "$PASS ready. Next: (terminal A) cd $MW && .venv/bin/mw env run --count 5 --launch-interval 20"
else
  echo -e "$FAIL not ready — fix the ✗ items above. KVM ✗ usually means: switch to a bare-metal host."
fi
exit $fail
