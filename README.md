<div align="center">

# 🛒 BigShop — Auditoría de Seguridad Web

### Trabajo de Fin de Máster · Máster en Ciberseguridad y Hacking Ético

![Status](https://img.shields.io/badge/estado-en%20curso-yellow)
![Target](https://img.shields.io/badge/objetivo-172.17.0.2-blue)
![Findings](https://img.shields.io/badge/hallazgos-34-critical)
![License](https://img.shields.io/badge/uso-educativo-lightgrey)

</div>

---

## 📋 Resumen

Auditoría de seguridad de caja negra realizada, en el marco de un TFM, sobre **BigShop**, un laboratorio Docker con **4 aplicaciones web** desplegadas sobre un mismo host. Adoptamos el rol de auditores externos contratados por la empresa cliente ficticia *BigShop*, partiendo únicamente de una dirección IP.

> 🚧 **Estado:** **3 de 4 aplicaciones auditadas por completo** — **PenguinWave** (puerto 8080, 10 hallazgos), **PixelForge** (puerto 10000, 7 hallazgos, con dos rutas independientes hasta ejecución remota de código y dos rutas independientes adicionales de toma de cuenta administradora) y **WordPress** (puerto 80, 7 hallazgos, compromiso total del servidor vía fuerza bruta → RCE → secretos expuestos). La aplicación restante (puerto 9090, **StreamWave**) está **en análisis** — **10 hallazgos confirmados** hasta ahora, destacando un **Path Traversal no autenticado** que permite leer el código fuente completo de la aplicación (con secretos de Stripe/AWS/SendGrid/Twilio hardcodeados) y **comprometer la base de datos de PixelForge**, y un **bypass total de autenticación JWT** (`alg:none`) que vuelca la base de usuarios completa con contraseñas en texto plano y permite tomar la cuenta real de administrador. Se suman el IDOR masivo, los secretos expuestos en contenido privado, el SSRF que bypassa un control de acceso por IP real de las otras 3 apps, la condición de carrera en los likes, un XSS almacenado vía subida de fichero, un XSS reflejado en el buscador, y una política de contraseñas débil. Incluye también un resultado negativo documentado (CSRF probado y descartado).

## 🎯 Objetivo y alcance

| | |
|---|---|
| **Objetivo** | `172.17.0.2` |
| **Dentro de alcance** | Puertos 80, 8080, 9090, 10000 |
| **Fuera de alcance** | Cualquier sistema fuera del laboratorio Docker |
| **Tipo de auditoría** | Caja negra (black-box) |
| **Herramientas** | `nmap`, `ffuf` + SecLists, Burp Suite, DevTools, WPScan, Python (scripts propios), `curl`, cliente MySQL, Apache Benchmark |

---

## 🗂️ Estructura del repositorio

```
bigshop-security-audit/
├── README.md                    ← este archivo (síntesis)
├── docs/
│   └── informe-BigShop.pdf      ← informe técnico formal (CVSS, CWE, remediación)
├── auditoria/                   ← proceso completo de cada aplicación, paso a paso
│   ├── 00-reconocimiento-general.md
│   ├── penguinwave/README.md
│   ├── pixelforge/README.md
│   └── wordpress/README.md
├── writeups/                    ← un writeup visual independiente por hallazgo (25)
│   └── README.md                ← índice de writeups
├── scripts/                     ← PoCs propios (fuerza bruta MFA, webshells de prueba)
├── scans/                       ← output crudo de herramientas (ej. WPScan)
└── assets/                      ← capturas de pantalla de todos los hallazgos
```

- **`auditoria/`** — el relato completo, aplicación por aplicación: descubrimiento de contenido, comandos reales y cronología de cada hallazgo según se fue encontrando. Es la forma de leer *todo el proceso* de principio a fin.
- **`writeups/`** — cada hallazgo por separado, como página autocontenida (contexto, PoC, impacto, remediación). Para leer uno suelto sin el resto del contexto.
- **`docs/informe-BigShop.pdf`** — el entregable formal del TFM, con CVSS/CWE/remediación estructurados por hallazgo.
- **`scripts/`** y **`scans/`** — artefactos reales usados durante la auditoría (código propio y output de herramientas), referenciados desde `auditoria/` y `writeups/`.

---

## 🏆 Hallazgos confirmados

| # | Hallazgo | Severidad | CVSS |
|---|---|:---:|:---:|
| 1 | Cookie de sesión sin atributos de seguridad | 🟠 Alto | 6.5 |
| 2 | Credenciales por defecto (`admin`/`admin`) | 🔴 Crítico | 9.1 |
| 3 | **Cadena completa de compromiso administrador** | 🔴 Crítico | 9.1 |
| 4 | XSS reflejado en buscador + robo de sesión | 🟠 Alto | 8.1 |
| 5 | XSS almacenado en reviews + robo de sesión | 🟠 Alto | 7.3 |
| 6 | Manipulación de precio (descuento al 100% del carrito) | 🟡 Medio | 6.5 |
| 7 | IDOR en facturas (`invoice.php`) | 🟡 Medio | 6.5 |
| 8 | Reviews ilimitadas / rating bombing | 🟡 Medio | 4.3 |
| 9 | CSRF en envío de reviews (`add_review.php`) | 🟡 Medio | 4.3 |
| 10 | **IDOR masivo en Developer API** (perfiles, direcciones, pedidos) | 🔴 Crítico | 6.5 |
| 11 | **[PixelForge]** Inyección SQL en login.php — toma de cuenta admin | 🔴 Crítico | 9.8 |
| 12 | **[PixelForge]** Subida de fichero sin restricciones → RCE | 🔴 Crítico | 9.8 |
| 13 | **[PixelForge]** Política de registro débil (sin verificación de email) | 🟡 Medio | 5.3 |
| 14 | **[PixelForge]** 🏆 Cadena completa: invitado anónimo → RCE (2 rutas) | 🔴 Crítico | 9.8 |
| 15 | **[PixelForge]** Escalada de privilegios local (www-data → pepe) | 🟠 Alto | 7.8 |
| 16 | **[PixelForge]** Secretos y credenciales en texto plano en config.php | 🔴 Crítico | 8.6 |
| 17 | **[PixelForge]** 🏆 Toma de cuenta admin vía tokens filtrados en mail.log | 🔴 Crítico | 8.6 |
| 18 | **[WordPress]** Enumeración masiva de usuarios sin autenticación (29 cuentas) | 🟡 Medio | 5.3 |
| 19 | **[WordPress]** Denegación de servicio parcial vía wp-cron.php | 🟡 Medio | 5.3 |
| 20 | **[WordPress]** Credenciales débiles (`admin`/`qwerty`) vía fuerza bruta | 🔴 Crítico | 9.1 |
| 21 | **[WordPress]** RCE vía Theme File Editor → reverse shell | 🔴 Crítico | 9.8 |
| 22 | **[WordPress]** Secretos de BD y claves de autenticación en wp-config.php | 🔴 Crítico | 8.6 |
| 23 | **[WordPress]** Grupo `workers` con `/etc` escribible (no explotado) | 🟡 Medio | 6.0 |
| 24 | **[WordPress]** 🏆 Cadena completa: fuerza bruta → RCE → compromiso total | 🔴 Crítico | 9.8 |
| 25 | **[StreamWave]** IDOR en `/watch/{id}` — vídeos "privados" visibles por cualquiera | 🟠 Alto | 7.5 |
| 26 | **[StreamWave]** Secretos expuestos en contenido privado (credenciales BD + API key) | 🟠 Alto | 7.5 |
| 27 | **[StreamWave]** 🏆 SSRF en `/api/fetch-thumb` — escaneo interno + bypass de control de acceso por IP | 🔴 Crítico | 8.6 |
| 28 | **[StreamWave]** Condición de carrera en likes — manipulación del ranking de Trending | 🟡 Medio | 6.5 |
| 29 | **[StreamWave]** 🏆 Bypass de autenticación JWT (`alg:none`) — dump de usuarios + toma de cuenta admin | 🔴 Crítico | 9.8 |
| 30 | **[StreamWave]** CSRF en comentarios — probado en navegador real, no explotable | ⚪ Info | — |
| 31 | **[StreamWave]** Política de contraseñas inexistente y sin rate-limit en login | 🟡 Medio | 5.3 |
| 32 | **[StreamWave]** Subida de fichero sin restricciones → XSS almacenado same-origin | 🟡 Medio | 5.7 |
| 33 | **[StreamWave]** 🏆 Path Traversal en `?language=` → código fuente + compromiso cruzado de PixelForge | 🔴 Crítico | 7.9 |
| 34 | **[StreamWave]** XSS reflejado en el buscador (`?q=`), sin autenticación | 🟠 Alto | 6.1 |

---

## 📚 Para profundizar

| Quiero... | Voy a... |
|---|---|
| Leer el proceso completo, app por app | [`auditoria/`](auditoria/00-reconocimiento-general.md) |
| Leer un hallazgo concreto, de forma autocontenida | [`writeups/`](writeups/README.md) |
| El informe técnico formal (CVSS, CWE, remediación) | [`docs/informe-BigShop.pdf`](docs/informe-BigShop.pdf) |

---

## 🧰 Herramientas y scripts propios

- [`scripts/mfa_bruteforce.py`](scripts/mfa_bruteforce.py) — fuerza bruta concurrente del OTP del MFA, explotando el bypass de rate-limit por `X-Forwarded-For`.
- [`scripts/pixelforge_avatar_rce_shell.php`](scripts/pixelforge_avatar_rce_shell.php) — webshell mínimo (`system($_GET['cmd'])`) usado como avatar para confirmar la RCE de PixelForge.
- [`scripts/pixelforge_avatar_xss_poc.svg`](scripts/pixelforge_avatar_xss_poc.svg) / [`pixelforge_avatar_xss_cookie_steal.svg`](scripts/pixelforge_avatar_xss_cookie_steal.svg) — SVG con `onload` para confirmar que el mismo formulario de avatar tampoco filtra SVGs con JS embebido.
- [`scans/wpscan-bigshop-puerto80.txt`](scans/wpscan-bigshop-puerto80.txt) — output completo de WPScan contra WordPress (puerto 80).
- [`scripts/streamwave_idor_watch_scan.py`](scripts/streamwave_idor_watch_scan.py) — escáner propio (sin dependencias externas) del IDOR de StreamWave: barre las 26.000 combinaciones posibles del ID de vídeo (`HEAD` para detectar existencia, `GET` anónimo para clasificar público/privado y extraer título/owner/descripción). Resultados en [`scans/streamwave-idor-full-scan.json`](scans/streamwave-idor-full-scan.json) y [`scans/streamwave-idor-private-videos.csv`](scans/streamwave-idor-private-videos.csv).
- [`scripts/streamwave_ssrf_portscan.py`](scripts/streamwave_ssrf_portscan.py) — escáner de puertos internos vía el SSRF ciego de `/api/fetch-thumb`: se autentica solo, barre un rango de puertos clasificando abierto-HTTP/abierto-no-HTTP/cerrado, y compara cada ruta sensible encontrada contra su respuesta externa real para confirmar bypass de control de acceso por IP sin falsos positivos. Resultado en [`scans/streamwave-ssrf-portscan-full.json`](scans/streamwave-ssrf-portscan-full.json).
- [`scripts/streamwave_like_race_condition.py`](scripts/streamwave_like_race_condition.py) — PoC de la condición de carrera en `/api/videos/{id}/like` y `/unlike`: se autentica solo, resetea el vídeo, dispara N peticiones concurrentes con una sola sesión y mide el incremento/decremento real del contador contra el esperado (±1).
- [`scripts/streamwave_jwt_auth_bypass.py`](scripts/streamwave_jwt_auth_bypass.py) — PoC del bypass de autenticación JWT `alg:none`: forja un token con `role:admin` sin firma, lo usa contra `/api/me` y `/api/admin/users` (dump completo de usuarios), y si encuentra la cuenta `admin`, prueba automáticamente el login real de sesión con la contraseña filtrada.
- [`scripts/streamwave_lfi_scan.py`](scripts/streamwave_lfi_scan.py) — escáner del Path Traversal en `?language=`: prueba una lista de ficheros sensibles (incluidos pseudo-ficheros `/proc`) a distintas profundidades de `../`, sin autenticación ni dependencias externas.

---

<div align="center">

**José Gómez García** · TFM — Máster en Ciberseguridad y Hacking Ético

*Laboratorio con fines educativos. Todas las vulnerabilidades se explotaron exclusivamente en el entorno de laboratorio Docker, sin alcance a sistemas de producción.*

</div>
