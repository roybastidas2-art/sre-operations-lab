# Día 1 — Fundamentos Linux y diagnóstico operativo

**Estado:** En progreso  
**Entorno:** Ubuntu 24.04 LTS sobre WSL2  
**Objetivo:** Desarrollar fundamentos de administración Linux
y diagnóstico técnico orientados a Site Reliability Engineering.

## 1. Preparación del entorno

- Instalación de Ubuntu 24.04 LTS en WSL2.
- Verificación de las distribuciones Ubuntu y docker-desktop.
- Creación de un directorio de trabajo en el sistema de archivos Linux.

## 2. Sistema de archivos

Comandos practicados:

- `pwd`, `cd`, `ls`: navegación e inspección.
- `mkdir -p`: creación de directorios.
- `touch`: creación de archivos.
- `echo`, `>` y `>>`: escritura y redirección.
- `cat`, `head`, `tail`, `wc` y `grep`: inspección de archivos.

**Aprendizaje:** Diferencias entre rutas absolutas y relativas,
sobrescritura y adición de contenido, y códigos de salida.

## 3. Permisos, usuarios y grupos

Comandos practicados:

- `chmod`, `stat`, `id`, `getent`, `whoami` y `sudo`.

Resultados comprobados:

- Archivo de práctica con permisos `640`.
- Directorio de práctica configurado con permisos `750`.
- Identificación de la cuenta normal y del superusuario root.
- Comprobación de que la contraseña de root está bloqueada.

**Aprendizaje:** Permisos de usuario, grupo y otros;
notación octal y principio de mínimo privilegio.

## 4. Servicios y conectividad

| Comprobación | Resultado observado |
|---|---|
| systemd-resolved | active (running) |
| Sockets TCP | Tres entradas LISTEN en puerto 53 |
| Puerto TCP 22 | No observado en la consulta |
| DNS de example.com | Resolución IPv4 e IPv6 correcta |
| Solicitud HTTPS a example.com | HTTP 200 |

Comandos utilizados:

- `ss -ltnp`
- `systemctl status`
- `systemctl is-active`
- `resolvectl query`
- `curl`

## 5. Rendimiento HTTP

Se practicó la medición de:

- Código de respuesta HTTP.
- Tiempo total de solicitud.
- Time to First Byte (TTFB).

Una medición registrada:

- TTFB: 0.035917 segundos.
- Tiempo total: 0.036022 segundos.

Estos valores corresponden a una prueba puntual
y no constituyen una medición sostenida de rendimiento.

## 6. Conclusiones

- Un servicio activo no garantiza su correcto funcionamiento.
- Una resolución DNS exitosa no garantiza disponibilidad HTTPS.
- HTTP 200 no garantiza un rendimiento aceptable.
- Una respuesta desde caché CDN no verifica el servidor de origen.
- Los diagnósticos deben basarse en evidencia, no en suposiciones.

## 7. Próximos pasos

- Completar los ejercicios pendientes.
- Revisar y ampliar la documentación.
- Validar las evidencias antes de publicarlas.
