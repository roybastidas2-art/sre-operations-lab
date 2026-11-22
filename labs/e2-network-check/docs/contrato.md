# Contrato del comprobador

## Uso

```bash
bash scripts/check.sh --url URL --tcp-host HOST --tcp-port PUERTO [opciones]
```

| Opción | Obligatorio | Valor/validación |
|---|---|---|
| `--url` | Sí | HTTP o HTTPS, sin credenciales, query ni fragmentos |
| `--tcp-host` | Sí | Dominio o IPv4; IPv6 fuera del alcance |
| `--tcp-port` | Sí | Entero 1–65535 |
| `--timeout` | No | 1–99 segundos por comprobación; 5 por defecto |
| `--expect-status` | No | 100–599; 200 por defecto |
| `--label` | No | Identificador 1–48 caracteres, letras, números, punto, guion y guion bajo |
| `--output` | No | Archivo JSONL; `results/checks.jsonl` por defecto |

## Salida

Cada ejecución emite un único objeto JSON en stdout y trata de guardarlo como una línea adicional en el archivo de salida. Campos principales:

- `timestamp_utc`: momento de ejecución en UTC.
- `label`: identificador de la prueba.
- `http.status`: último código HTTP observado (`0` si no se obtuvo respuesta HTTP).
- `http.expected_status`: código exigido al endpoint.
- `http.ok`: `true` cuando curl termina sin error y el código coincide exactamente.
- `http.error`: categoría de fallo (`NONE`, `DNS_ERROR`, `CONNECTION_ERROR`, `TIMEOUT`, `HTTP_STATUS_UNEXPECTED`, errores TLS, etc.).
- `http.curl_exit`: código nativo devuelto por curl.
- `http.timing_s`: tiempos acumulados de DNS, conexión, negociación TLS, TTFB y total, en segundos.
- `tcp.host`, `tcp.port`, `tcp.ok`, `tcp.error`, `tcp.elapsed_ms`: información del intento TCP independiente.
- `overall_ok`: `true` si `http.ok` y `tcp.ok` son ambos `true`.

**Importante:** `time_namelookup`, `time_connect`, `time_appconnect`, `time_starttransfer` y `time_total` son marcas temporales acumuladas desde el inicio de la operación. No deben sumarse. En una falla temprana, una etapa no completada puede aparecer con valor cero.

## Códigos de salida

| Código | Significado |
|---|---|
| `0` | HTTP y TCP cumplen sus condiciones |
| `1` | Alguna comprobación no cumple |
| `2` | Argumentos inválidos o dependencia ausente |
| `3` | No se pudo escribir el registro JSONL |

El comando muestra el JSON antes de intentar guardarlo; por ello puede devolver código `3` aunque haya producido una línea en stdout.

## Decisiones de diseño

- No se ejecuta `ping`: ICMP y disponibilidad de servicios son señales diferentes.
- No se utiliza un proxy: `curl --noproxy '*'` permite una prueba directa, pero fallará en redes que exigen proxy.
- No se siguen redirecciones: 301/302 no equivale al código 200 solicitado.
- No se inspecciona el cuerpo HTTP: un 200 con error funcional es un falso positivo posible.
- Se comprueba TCP con la característica `/dev/tcp` de Bash; el error de una conexión TCP fallida no siempre permite separar DNS y transporte.
- Las dos comprobaciones son secuenciales y cada una tiene su propio timeout. La duración total puede aproximarse a la suma de ambos límites.
- No hay reintentos automáticos: se evita disimular fallos intermitentes en esta etapa.
- No es un servicio de monitorización, ni aporta medición de disponibilidad agregada, SLO o alertas.
