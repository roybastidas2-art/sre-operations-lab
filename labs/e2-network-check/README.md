# Comprobaciones HTTP y TCP con Bash

**Proyecto:** SRE Operations Lab  
**Periodo:** Semana 2  
**Fecha de validación:** 22 de noviembre de 2026  
**Entorno:** Ubuntu 24.04 LTS sobre WSL2

## Objetivo

Implementar un verificador de conectividad que permita distinguir entre
la disponibilidad de un puerto TCP y la respuesta de un endpoint HTTP.

Una conexión TCP exitosa no garantiza que una aplicación responda
correctamente. Del mismo modo, un código HTTP 200 no demuestra que
la operación solicitada haya terminado sin errores funcionales.

## Implementación

El script `scripts/check.sh` realiza dos comprobaciones independientes:

- HTTP: código de respuesta, estado esperado, timeout y tiempos de conexión.
- TCP: conectividad al host y puerto configurados.

Los resultados se presentan en formato JSON Lines (JSONL) e incluyen
el estado individual de cada comprobación y un resultado global.

El proceso devuelve un código de salida para permitir su integración
con otras herramientas de automatización.

## Requisitos

- Linux con Bash.
- curl.
- GNU coreutils.
- Python 3 para ejecutar las pruebas automatizadas y el servidor local.

No requiere Docker, dependencias externas de Python ni privilegios de administrador.

## Estructura

```text
e2-network-check/
├── README.md
├── .gitignore
├── scripts/
│   ├── check.sh
│   └── validar.sh
├── tests/
│   ├── mock_server.py
│   └── test_check.py
├── docs/
│   ├── contrato.md
│   └── diagnostico.md
├── evidence/
│   └── REGISTRO-SEMANA-02.md
└── results/
    └── .gitkeep
```

## Ejecución

Desde el directorio `labs/e2-network-check`:

### 1. Ejecutar las pruebas

```bash
bash scripts/validar.sh
```

### 2. Iniciar el servidor local

En una terminal:

```bash
python3 tests/mock_server.py --port 8088
```

### 3. Ejecutar una comprobación

En otra terminal:

```bash
bash scripts/check.sh \
  --url http://127.0.0.1:8088/health \
  --tcp-host 127.0.0.1 \
  --tcp-port 8088 \
  --timeout 3 \
  --label http-health

echo "codigo_salida=$?"
```

El servidor permite reproducir respuestas HTTP 200, HTTP 503,
errores funcionales, respuestas lentas y redirecciones.

Para finalizar el servidor se utiliza `Ctrl+C`.

## Validación

El 22 de noviembre de 2026 se ejecutaron las pruebas en Ubuntu
24.04 LTS sobre WSL2.

**Suite automatizada:** 16 pruebas superadas, sin errores reportados.

**Escenarios manuales:**

| Escenario | HTTP | TCP | Resultado global |
|---|---|---|---|
| Endpoint `/health` | 200 | Accesible | Éxito |
| Endpoint `/unhealthy` | 503 | Accesible | Fallo |
| Endpoint `/business-error` | 200 | Accesible | Éxito |
| Endpoint `/slow` con timeout de 1 s | Timeout | Accesible | Fallo |
| HTTP operativo y puerto 8099 inaccesible | 200 | Fallo de conexión | Fallo |

Los cinco escenarios produjeron el comportamiento esperado
según el contrato actual del verificador.

Los resultados de las ejecuciones se documentan en
[`evidence/REGISTRO-SEMANA-02.md`](evidence/REGISTRO-SEMANA-02.md).

## Hallazgos

### Conectividad TCP y disponibilidad HTTP

El endpoint `/unhealthy` devolvió HTTP 503 mientras el puerto TCP
permanecía accesible. Esto confirma que ambas comprobaciones aportan
información diferente.

### Timeout

El endpoint `/slow` superó el tiempo configurado de un segundo.
El script identificó el error como `TIMEOUT` y devolvió un código
de salida distinto de cero.

### Error funcional con HTTP 200

El endpoint `/business-error` respondió HTTP 200 con este contenido:

```json
{
  "status": "error",
  "detail": "operation rejected"
}
```

El script clasificó la comprobación como exitosa porque no valida
el contenido funcional de la respuesta.

Este comportamiento es una limitación conocida, no un fallo
respecto al contrato implementado.

## Limitaciones

- El estado HTTP no garantiza que una operación de negocio sea correcta.
- Una ejecución aislada no permite calcular disponibilidad sostenida.
- Los tiempos registrados corresponden a solicitudes puntuales.
- La herramienta no realiza seguimiento de redirecciones HTTP.
- El alcance actual no incluye métricas históricas, alertas ni SLO.

## Documentación

- [Contrato técnico](docs/contrato.md)
- [Diagnóstico de fallos](docs/diagnostico.md)
- [Registro de evidencias](evidence/REGISTRO-SEMANA-02.md)

## Consideraciones de seguridad

Las pruebas deben ejecutarse sobre servicios propios o autorizados.

No se deben incorporar credenciales, tokens, direcciones privadas
de terceros ni información de sistemas empresariales al repositorio.

Los archivos JSONL generados durante la ejecución se conservan
localmente y no forman parte del código fuente publicado.
