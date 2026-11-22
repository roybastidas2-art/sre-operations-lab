#!/usr/bin/env bash
# E2 — Verificador de disponibilidad HTTP y conectividad TCP.
# Dependencias: bash, curl, GNU timeout, date, mkdir.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

URL=""
TCP_HOST=""
TCP_PORT=""
TIMEOUT_S="5"
EXPECT_STATUS="200"
LABEL="e2-check"
OUTPUT="$LAB_DIR/results/checks.jsonl"

usage() {
  cat <<'HELP'
Uso:
  ./scripts/check.sh --url URL --tcp-host HOST --tcp-port PUERTO [opciones]

Argumentos obligatorios:
  --url URL              Endpoint HTTP o HTTPS (sin credenciales ni parámetros secretos)
  --tcp-host HOST        Nombre DNS o IPv4 del servicio TCP
  --tcp-port PUERTO      Puerto TCP (1-65535)

Opciones:
  --timeout SEGUNDOS     Timeout para cada verificación, por separado (1-99; default: 5)
  --expect-status CODIGO Código HTTP esperado (100-599; default: 200)
  --label NOMBRE         Etiqueta sin espacios (default: e2-check)
  --output RUTA          Archivo JSON Lines (default: results/checks.jsonl)
  -h, --help             Mostrar ayuda

Códigos de salida:
  0  HTTP y TCP correctos
  1  Una o ambas verificaciones fallaron
  2  Uso incorrecto / argumentos inválidos
  3  No fue posible escribir el registro JSONL

Nota: No sigue redirecciones HTTP, no usa proxy y no requiere jq.
HELP
}

usage_error() {
  printf 'ERROR: %s\n\n' "$1" >&2
  usage >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --url|--tcp-host|--tcp-port|--timeout|--expect-status|--label|--output)
      option="$1"
      (($# >= 2)) || usage_error "Falta un valor para $option"
      value="$2"
      shift 2
      case "$option" in
        --url) URL="$value" ;;
        --tcp-host) TCP_HOST="$value" ;;
        --tcp-port) TCP_PORT="$value" ;;
        --timeout) TIMEOUT_S="$value" ;;
        --expect-status) EXPECT_STATUS="$value" ;;
        --label) LABEL="$value" ;;
        --output) OUTPUT="$value" ;;
      esac
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage_error "Opción desconocida: $1" ;;
  esac
done

[[ "$URL" =~ ^https?://[^[:space:]]+$ ]] || usage_error "--url debe empezar por http:// o https://"
# Para el laboratorio no se necesitan credenciales en URL ni query strings.
[[ "$URL" != *'?'* && "$URL" != *'#'* ]] || usage_error "No se permiten query strings ni fragmentos en --url"
url_authority="${URL#*://}"
url_authority="${url_authority%%/*}"
[[ "$url_authority" != *'@'* ]] || usage_error "No se permiten credenciales en --url"
[[ "$TCP_HOST" =~ ^[A-Za-z0-9.-]+$ ]] || usage_error "--tcp-host debe ser un nombre DNS o IPv4 (no IPv6 en este laboratorio)"
[[ "$TCP_PORT" =~ ^[0-9]{1,5}$ ]] || usage_error "--tcp-port debe ser un entero de 1 a 65535"
port_num=$((10#$TCP_PORT))
((port_num >= 1 && port_num <= 65535)) || usage_error "--tcp-port fuera del rango válido"
[[ "$TIMEOUT_S" =~ ^[1-9][0-9]?$ ]] || usage_error "--timeout debe ser un entero entre 1 y 99"
[[ "$EXPECT_STATUS" =~ ^[1-5][0-9]{2}$ ]] || usage_error "--expect-status debe ser un código HTTP entre 100 y 599"
[[ "$LABEL" =~ ^[A-Za-z0-9_.-]{1,48}$ ]] || usage_error "--label admite 1-48 caracteres alfanuméricos, _, . o -"
[[ -n "$OUTPUT" && "$OUTPUT" != '-' ]] || usage_error "--output requiere una ruta de archivo"

for required in curl timeout date mkdir bash; do
  command -v "$required" >/dev/null 2>&1 || usage_error "Falta la dependencia: $required"
done

timestamp_utc="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

# Las marcas de tiempo de curl son acumuladas desde el inicio de la solicitud.
# Se ocultan los errores de curl para que la salida JSON sea estable y no exponga URLs.
curl_exit=0
curl_metrics="$(curl \
  --silent --show-error --noproxy '*' \
  --proto '=http,https' \
  --connect-timeout "$TIMEOUT_S" \
  --max-time "$TIMEOUT_S" \
  --output /dev/null \
  --write-out $'%{http_code}\t%{time_namelookup}\t%{time_connect}\t%{time_appconnect}\t%{time_starttransfer}\t%{time_total}' \
  -- "$URL" 2>/dev/null)" || curl_exit=$?

http_code='000'
dns_s='0.000000'
connect_s='0.000000'
tls_s='0.000000'
ttfb_s='0.000000'
total_s='0.000000'
if [[ -n "$curl_metrics" ]]; then
  IFS=$'\t' read -r http_code dns_s connect_s tls_s ttfb_s total_s <<< "$curl_metrics"
fi
# No permitimos texto arbitrario en el documento JSON.
[[ "$http_code" =~ ^[0-9]{3}$ ]] || http_code='000'
for metric in dns_s connect_s tls_s ttfb_s total_s; do
  if [[ ! "${!metric}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    printf -v "$metric" '0.000000'
  fi
done
http_code_num=$((10#$http_code))

http_ok=false
http_error='NONE'
if ((curl_exit == 0)); then
  if ((http_code_num == 10#$EXPECT_STATUS)); then
    http_ok=true
  else
    http_error='HTTP_STATUS_UNEXPECTED'
  fi
else
  case "$curl_exit" in
    5)  http_error='PROXY_DNS_ERROR' ;;
    6)  http_error='DNS_ERROR' ;;
    7)  http_error='CONNECTION_ERROR' ;;
    28) http_error='TIMEOUT' ;;
    35) http_error='TLS_HANDSHAKE_ERROR' ;;
    51|60) http_error='TLS_CERT_ERROR' ;;
    52) http_error='EMPTY_REPLY' ;;
    56) http_error='RECEIVE_ERROR' ;;
    *)  http_error='CURL_ERROR' ;;
  esac
fi

# Conexión TCP independiente de HTTP. La redirección /dev/tcp es una función de Bash.
# timeout limita también la espera durante la resolución DNS.
tcp_start_ms="$(date +%s%3N)"
tcp_exit=0
timeout --signal=TERM --kill-after=1s "${TIMEOUT_S}s" \
  bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$TCP_HOST" "$port_num" \
  >/dev/null 2>&1 || tcp_exit=$?
tcp_end_ms="$(date +%s%3N)"
tcp_elapsed_ms="$((tcp_end_ms - tcp_start_ms))"

tcp_ok=false
tcp_error='NONE'
if ((tcp_exit == 0)); then
  tcp_ok=true
elif ((tcp_exit == 124 || tcp_exit == 137)); then
  tcp_error='TIMEOUT'
else
  tcp_error='CONNECTION_ERROR'
fi

overall_ok=false
if [[ "$http_ok" == true && "$tcp_ok" == true ]]; then
  overall_ok=true
fi

# LABEL y TCP_HOST están restringidos a caracteres seguros y no requieren JSON escaping.
json="$(printf '{"schema_version":1,"timestamp_utc":"%s","label":"%s","http":{"status":%d,"expected_status":%d,"ok":%s,"error":"%s","curl_exit":%d,"timing_s":{"dns":%s,"connect":%s,"tls":%s,"ttfb":%s,"total":%s}},"tcp":{"host":"%s","port":%d,"ok":%s,"error":"%s","elapsed_ms":%d},"overall_ok":%s}' \
  "$timestamp_utc" "$LABEL" "$http_code_num" "$EXPECT_STATUS" "$http_ok" "$http_error" "$curl_exit" \
  "$dns_s" "$connect_s" "$tls_s" "$ttfb_s" "$total_s" \
  "$TCP_HOST" "$port_num" "$tcp_ok" "$tcp_error" "$tcp_elapsed_ms" "$overall_ok")"

printf '%s\n' "$json"
if ! mkdir -p -- "$(dirname -- "$OUTPUT")"; then
  printf 'ERROR: no se pudo crear el directorio de resultados.\n' >&2
  exit 3
fi
if ! printf '%s\n' "$json" >> "$OUTPUT"; then
  printf 'ERROR: no se pudo escribir el archivo JSONL.\n' >&2
  exit 3
fi

if [[ "$overall_ok" == true ]]; then
  exit 0
fi
exit 1
