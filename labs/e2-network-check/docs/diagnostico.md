# Diagnóstico rápido

| Resultado observado | Interpretación inicial | Qué comprobar después |
|---|---|---|
| `http.error=DNS_ERROR` | curl no pudo resolver el nombre | DNS local, resolvers y nombre solicitado |
| `http.error=CONNECTION_ERROR` | Falló la conexión del cliente HTTP | Destino, puerto, firewall, aplicación escuchando |
| `http.error=TIMEOUT` | Se agotó el tiempo para la prueba HTTP | Latencia, saturación, ruta de red y límites configurados |
| `http.error=HTTP_STATUS_UNEXPECTED` | Hubo respuesta, pero el código no coincide | Código concreto, logs de aplicación y ruta |
| `http.error=TLS_CERT_ERROR` | Problema en validación de certificado | Nombre, cadena de confianza, vigencia; no desactivar TLS como solución |
| `tcp.ok=true`, `http.ok=false` | Puerto accesible, pero HTTP no cumple | Servicio de aplicación, HTTP/TLS, dependencias |
| `tcp.ok=false`, `http.ok=true` | HTTP respondió, pero el chequeo TCP separado falló | Revisar si ambos apuntan al mismo destino y puerto |
| `http.ok=true`, `tcp.ok=true` | Dos comprobaciones puntuales exitosas | No descarta errores funcionales, intermitencias o saturación |

## Una trampa deliberada

`/business-error` devuelve HTTP 200 con `{"status":"error"}`. El verificador no lee ni interpreta ese cuerpo y marcará la muestra como correcta si también llega por TCP. No es un defecto oculto: es un límite explícito. Para diagnosticar una operación real haría falta un chequeo funcional de una ruta controlada y una definición precisa de éxito.

## Reglas de operación

- No diagnosticar un sistema completo a partir de una sola muestra.
- No transformar un HTTP 200 en una afirmación de salud de negocio.
- No publicar endpoints privados, credenciales o resultados sin revisar.
- Ante un fallo, conservar código, contexto, hora y resultado para reproducir el caso.
