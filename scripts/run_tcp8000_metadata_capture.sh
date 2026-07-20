#!/usr/bin/env bash
# Capture metadata-only TCP diagnostics for the NJIT Thesis Auditor listener.
#
# This wrapper intentionally prints tcpdump's decoded header lines to stdout and
# never writes pcap files. Run it under the systemd unit template in
# deploy/systemd/ so stdout is rotated as a normal text log.
set -euo pipefail

AUDITOR_HOST="${AUDITOR_HOST:-10.196.93.210}"
AUDITOR_PORT="${AUDITOR_PORT:-8000}"
CLIENT_FILTER="${CLIENT_FILTER:-}"
TCPDUMP_BIN="${TCPDUMP_BIN:-tcpdump}"
TCPDUMP_INTERFACE="${TCPDUMP_INTERFACE:-any}"
TCPDUMP_SNAPLEN="${TCPDUMP_SNAPLEN:-96}"

filter="tcp port ${AUDITOR_PORT} and host ${AUDITOR_HOST}"
if [[ -n "${CLIENT_FILTER}" ]]; then
  filter="${filter} and host ${CLIENT_FILTER}"
fi

echo "# $(date -Is) starting metadata capture: interface=${TCPDUMP_INTERFACE} snaplen=${TCPDUMP_SNAPLEN} filter=${filter}" >&2

exec "${TCPDUMP_BIN}" \
  -i "${TCPDUMP_INTERFACE}" \
  -n \
  -tttt \
  -l \
  -s "${TCPDUMP_SNAPLEN}" \
  "${filter}"
