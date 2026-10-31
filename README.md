<div align="center">

# 🛒 BigShop — Auditoría de Seguridad Web

### Trabajo de Fin de Máster · Máster en Ciberseguridad y Hacking Ético

![Status](https://img.shields.io/badge/estado-en%20curso-yellow)
![Target](https://img.shields.io/badge/objetivo-172.17.0.2-blue)
![Findings](https://img.shields.io/badge/hallazgos-24-critical)
![License](https://img.shields.io/badge/uso-educativo-lightgrey)

</div>

---

## 📋 Resumen

Auditoría de seguridad de caja negra realizada, en el marco de un TFM, sobre **BigShop**, un laboratorio Docker con **4 aplicaciones web** desplegadas sobre un mismo host. Adoptamos el rol de auditores externos contratados por la empresa cliente ficticia *BigShop*, partiendo únicamente de una dirección IP.

> 🚧 **Estado:** **3 de 4 aplicaciones auditadas por completo** — **PenguinWave** (puerto 8080, 10 hallazgos), **PixelForge** (puerto 10000, 7 hallazgos, con dos rutas independientes hasta ejecución remota de código y dos rutas independientes adicionales de toma de cuenta administradora) y **WordPress** (puerto 80, 7 hallazgos, compromiso total del servidor vía fuerza bruta → RCE → secretos expuestos). La aplicación restante (puerto 9090, StreamWave) sigue pendiente.

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

---

<div align="center">

**Jose Gomez Garcia** · TFM — Máster en Ciberseguridad y Hacking Ético

*Laboratorio con fines educativos. Todas las vulnerabilidades se explotaron exclusivamente en el entorno de laboratorio Docker, sin alcance a sistemas de producción.*

</div>
