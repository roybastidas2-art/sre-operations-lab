# Registro de validación — Semana 2

**Proyecto:** SRE Operations Lab  
**Laboratorio:** Comprobaciones HTTP y TCP con Bash  
**Fecha:** 22 de noviembre de 2026  
**Entorno:** Ubuntu 24.04 LTS sobre WSL2  
**Estado:** Pruebas automatizadas y escenarios manuales completados

## 1. Objetivo

Validar el comportamiento de un comprobador HTTP/TCP ante
respuestas correctas, errores HTTP, timeouts y fallos de conexión.

Las pruebas se realizaron contra un servidor HTTP local
en 127.0.0.1:8088.

## 2. Pruebas automatizadas

Comando ejecutado:

```
bash scripts/validar.sh
```

Resultados:

- Sintaxis Bash: OK.
- Pruebas ejecutadas: 16.
- Pruebas superadas: 16.
- Fallos reportados: 0.
- Tiempo de ejecución: 2.868 segundos.

La suite incluyó validación de argumentos, estados HTTP,
DNS, timeouts, conectividad TCP, redirecciones y escritura JSONL.

Las pruebas automatizadas no sustituyen una evaluación de
rendimiento o confiabilidad en producción.

## 3. Escenarios manuales

Las siguientes mediciones corresponden a las ejecuciones
locales del 22 de noviembre de 2026.

| Escenario | HTTP | TCP | Resultado global | Exit code |
|---|---|---|---|---|
| /health | 200 | OK | true | 0 |
| /unhealthy | 503 | OK | false | 1 |
| /business-error | 200 | OK | true | 0 |
| /slow (timeout 1 s) | Sin respuesta HTTP | OK | false | 1 |
| /health + TCP 8099 | 200 | CONNECTION_ERROR | false | 1 |

### 3.1 Respuesta HTTP satisfactoria

Fecha UTC: 2026-11-22 17:51:18

- Endpoint: /health.
- HTTP: 200.
- Tiempo total HTTP: 72.260 ms.
- TTFB: 71.085 ms.
- TCP: accesible.
- Tiempo de comprobación TCP: 29 ms.
- Código de salida: 0.

El endpoint respondió con el estado esperado y la comprobación
TCP independiente terminó correctamente.

### 3.2 HTTP 503 con TCP accesible

Fecha UTC: 2026-11-22 17:51:59

- Endpoint: /unhealthy.
- HTTP: 503.
- Error: HTTP_STATUS_UNEXPECTED.
- Tiempo total HTTP: 26.392 ms.
- TCP: accesible.
- Código de salida: 1.

El servidor aceptó conexiones TCP, pero respondió con un
estado HTTP distinto del esperado.

curl_exit fue 0: la transferencia HTTP se completó, aunque
la respuesta no cumplió el criterio configurado.

### 3.3 HTTP 200 con error funcional

Fecha UTC: 2026-11-22 17:53:41

- Endpoint: /business-error.
- HTTP: 200.
- Tiempo total HTTP: 51.385 ms.
- TCP: accesible.
- overall_ok: true.
- Código de salida: 0.

El cuerpo de la respuesta contenía:

```json
{
  "status": "error",
  "detail": "operation rejected"
}
```

El script consideró exitosa esta comprobación porque su
contrato actual valida conectividad y estado HTTP, pero no
interpreta el contenido funcional de la respuesta.

Este caso evidencia una limitación de cobertura del verificador.

### 3.4 Timeout HTTP

Fecha UTC: 2026-11-22 17:55:24

- Endpoint: /slow.
- Timeout configurado: 1 segundo.
- HTTP status registrado: 0.
- Error: TIMEOUT.
- curl_exit: 28.
- Tiempo total HTTP: 1000.980 ms.
- TCP: accesible.
- Código de salida: 1.

No se recibió una respuesta HTTP completa antes del límite
configurado. La conexión TCP independiente fue satisfactoria.

### 3.5 Fallo de conexión TCP

Fecha UTC: 2026-11-22 17:56:19

- Endpoint HTTP: 127.0.0.1:8088/health.
- HTTP: 200.
- Puerto TCP comprobado: 8099.
- TCP: false.
- Error: CONNECTION_ERROR.
- Tiempo de comprobación TCP: 28 ms.
- Código de salida: 1.

La comprobación HTTP funcionó, pero no se consiguió establecer
la conexión al puerto TCP evaluado por separado.

El resultado no determina por sí solo la causa del fallo TCP.

## 4. Análisis técnico

### Conectividad y disponibilidad

Una conexión TCP satisfactoria demuestra que fue posible
establecer comunicación con el puerto probado.

No garantiza que el endpoint HTTP devuelva el estado esperado
ni que la aplicación complete correctamente sus operaciones.

### Códigos HTTP y errores funcionales

El escenario /business-error demuestra que HTTP 200 no es
suficiente para comprobar el resultado funcional de una API.

Para detectar ese caso sería necesario validar el cuerpo de
la respuesta según un contrato funcional definido.

### Tiempos de respuesta

Los tiempos DNS, conexión, TLS, TTFB y total registrados por curl
representan hitos acumulados desde el inicio de la solicitud.

No deben sumarse entre sí.

Las mediciones corresponden a ejecuciones puntuales en
localhost. No representan latencias de una red externa.

### Códigos de salida

El script devolvió 0 cuando las comprobaciones configuradas
fueron satisfactorias y 1 en los escenarios manuales donde
detectó un fallo.

Los códigos de salida permiten que otro proceso distinga
un resultado satisfactorio de una condición de error.

## 5. Limitaciones identificadas

- No valida el contenido funcional del JSON.
- No calcula disponibilidad histórica.
- No implementa métricas agregadas ni SLO.
- No realiza alertas.
- No sustituye pruebas de extremo a extremo.
- Las mediciones locales no representan el comportamiento
  de un servicio de producción.

## 6. Trazabilidad

Las ejecuciones originales generaron registros JSONL locales
en `results/checks.jsonl`.

## 7. Revisión previa a publicación

- [x] Suite automatizada ejecutada.
- [x] Cinco escenarios manuales ejecutados.
- [x] Resultados consolidados a partir de salidas reales.
- [x] Limitaciones del verificador documentadas.
- [x] Reglas de .gitignore verificadas.
