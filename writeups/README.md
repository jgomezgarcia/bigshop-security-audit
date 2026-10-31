# 📝 Writeups individuales — BigShop

Un writeup visual independiente por cada hallazgo técnico: contexto, explotación paso a paso con capturas, impacto y remediación. Pensados para leerse sueltos — cada uno es autocontenido, sin depender del README principal ni del PDF.

Son **20 páginas** para **19 hallazgos** de la [tabla principal](../README.md#-hallazgos-confirmados): el bypass del rate-limit del MFA (`F-007`) tiene su propia página aunque el informe formal lo integra dentro de la cadena completa (`F-009`) — aquí se cuenta aparte por ser una técnica con entidad propia.

➡️ Volver al [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)

---

## 🏄 PenguinWave (puerto 8080)

| # | Writeup | Severidad |
|---|---|:---:|
| F-001 | [Cookie de sesión sin atributos de seguridad](F-001-cookie-sesion-sin-atributos.md) | 🟠 Alto |
| F-002 | [Credenciales por defecto (admin/admin)](F-002-credenciales-por-defecto-admin-admin.md) | 🔴 Crítico |
| F-003 | [XSS almacenado en reviews de producto](F-003-xss-almacenado-reviews.md) | 🟠 Alto |
| F-004 | [XSS reflejado en buscador](F-004-xss-reflejado-buscador.md) | 🟠 Alto |
| F-005 | [Manipulación de precio (descuento al 100%)](F-005-manipulacion-precio-descuento.md) | 🟡 Medio |
| F-006 | [IDOR en facturas (invoice.php)](F-006-idor-facturas-invoice.md) | 🟡 Medio |
| F-007 | [Bypass de rate-limit del MFA vía X-Forwarded-For](F-007-bypass-ratelimit-mfa-xff.md) | 🟠 Alto |
| F-008 | [Reviews ilimitadas / rating bombing](F-008-reviews-ilimitadas-rating-bombing.md) | 🟡 Medio |
| F-009 | [🏆 Cadena completa de compromiso de la cuenta administradora](F-009-cadena-completa-compromiso-admin.md) | 🔴 Crítico |
| F-010 | [CSRF en envío de reviews](F-010-csrf-envio-reviews.md) | 🟡 Medio |
| F-011 | [🏆 IDOR masivo en Developer API](F-011-idor-masivo-developer-api.md) | 🔴 Crítico |

## 🎮 PixelForge (puerto 10000)

| # | Writeup | Severidad |
|---|---|:---:|
| F-012 | [Inyección SQL en login.php — bypass de autenticación](F-012-sqli-login-bypass-auth.md) | 🔴 Crítico |
| F-013 | [🏆 Subida de fichero sin restricciones → RCE](F-013-subida-fichero-rce.md) | 🔴 Crítico |
| F-014 | [Política de registro débil](F-014-politica-registro-debil.md) | 🟡 Medio |
| F-015 | [🏆 Cadena completa: invitado anónimo → RCE](F-015-cadena-completa-invitado-rce.md) | 🔴 Crítico |
| F-016 | [Escalada de privilegios local (www-data → pepe)](F-016-escalada-privilegios-sudo-php.md) | 🟠 Alto |
| F-017 | [Secretos y credenciales en texto plano](F-017-secretos-credenciales-config-php.md) | 🔴 Crítico |
| F-018 | [🏆 Toma de cuenta admin vía tokens filtrados en mail.log](F-018-toma-cuenta-tokens-mail-log.md) | 🔴 Crítico |

## 🌐 WordPress (puerto 80)

| # | Writeup | Severidad |
|---|---|:---:|
| F-019 | [Enumeración masiva de usuarios sin autenticación](F-019-enumeracion-usuarios-wordpress.md) | 🟡 Medio |
| F-020 | [Denegación de servicio parcial vía wp-cron.php](F-020-dos-wp-cron.md) | 🟡 Medio |

---

<div align="center">

*Laboratorio con fines educativos — TFM, Máster en Ciberseguridad y Hacking Ético.*

</div>
