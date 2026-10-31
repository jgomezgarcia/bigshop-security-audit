# 🔑 F-017 — Secretos y credenciales en texto plano en inc/config.php

![Severidad](https://img.shields.io/badge/severidad-cr%C3%ADtico-critical) ![CVSS](https://img.shields.io/badge/CVSS-8.6-red) ![CWE](https://img.shields.io/badge/CWE-798-blue) ![App](https://img.shields.io/badge/app-PixelForge-purple)

> [!IMPORTANT]
> Un único fichero de configuración en texto plano contiene credenciales reales de base de datos, la contraseña del administrador en claro, y secretos con forma de producción de seis integraciones de terceros (PayPal, AWS, Discord, Mailgun, Cloudflare, JWT).

## 📖 Contexto

Con el acceso de [F-016 — Escalada de privilegios local](F-016-escalada-privilegios-sudo-php.md) (shell como `pepe`), el siguiente paso de post-explotación es buscar ficheros de configuración de la aplicación.

## 🔬 Explotación paso a paso

**1. Leer el fichero de configuración:**

```bash
# vía la shell de 'pepe' obtenida en F-016
cat /var/www/gamestore/inc/config.php
```

Contiene, todo en texto plano, sin ningún gestor de secretos ni separación por entorno:

- **Credenciales de base de datos:** `$DB_USER = 'gameuser'`, `$DB_PASS = 'gamepass'`, `$DB_HOST` (vía `getenv('GS_DB_HOST')`), `$DB_NAME = 'gamestore'`.
- **La contraseña real del administrador, en claro, en el propio código de seed:**
  ```php
  ['administrator', 'admin@pixelforge.gg', md5('letmein'), 'admin', 9999],
  ```
  Confirma de forma definitiva que las contraseñas se almacenan con **MD5 sin salt** (ya se sospechaba por el error de MariaDB de [F-012](F-012-sqli-login-bypass-auth.md)).
- **Secretos de integraciones de terceros:** `PAYPAL_CLIENT_ID`/`PAYPAL_CLIENT_SECRET` (con `PAYPAL_ENV = 'production'`), `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (+ `AWS_S3_BUCKET`), `DISCORD_BOT_TOKEN`, `MAILGUN_API_KEY`, `CLOUDFLARE_API_TOKEN`, y `JWT_SECRET`.

**2. Confirmar la contraseña del admin por login normal** (sin SQLi, sin reset):

```bash
curl -s -i -X POST http://172.17.0.2:10000/login.php -d "username=administrator&password=letmein"
# → 302 Found, Location: /dashboard.php
```

**3. Conectar directamente a la base de datos** (`GS_DB_HOST` resultó ser `127.0.0.1` — MariaDB corre en el propio host):

```bash
mysql -h 127.0.0.1 -u gameuser -pgamepass gamestore -e "select id,username,email,password,role,credits from users;"
```

Las 11 cuentas (7 de seed + 4 creadas durante la auditoría) salen con sus hashes MD5 reales — confirmando que **todas** las contraseñas de la plataforma se almacenan igual de débilmente, no solo la del admin. El hash actual de `administrator` (`200ceb26807d6bf99fd6f4f0d1ca54d4`) coincide exactamente con `md5("administrator")` — confirma a nivel de base de datos que el cambio de contraseña de [F-018](F-018-toma-cuenta-tokens-mail-log.md) quedó persistido de verdad.

La tabla `password_resets` confirma además que la expiración de 30 minutos **sí está implementada en servidor** y que el flag `used` se marca correctamente al consumir un token — el diseño del mecanismo de reseteo en sí es razonable; el único fallo real sigue siendo la exposición del token en `mail.log` ([F-018](F-018-toma-cuenta-tokens-mail-log.md)).

### 🧐 Nota honesta sobre los secretos de terceros

Los valores concretos presentan características propias de datos de relleno de laboratorio, no de secretos reales: el `AWS_ACCESS_KEY_ID` (`AKIAI44QH8DHBEXAMPLE`) termina literalmente en `EXAMPLE`, el sufijo que usa la documentación oficial de AWS para sus claves de ejemplo; varios otros valores siguen el mismo patrón de relleno. **No se ha intentado usar ninguno de estos secretos contra las APIs reales de AWS/PayPal/Discord/Mailgun/Cloudflare** — estaría fuera del alcance autorizado de este compromiso y sería potencialmente ilegal si alguno resultara ser válido.

Esto **no reduce la severidad del hallazgo**: el fallo real es de diseño — secretos con forma de producción hardcodeados en un único fichero PHP en texto plano, alcanzable por cualquiera que consiga leer un fichero del servidor. En un despliegue real con valores genuinos, el impacto de cada uno sería:

| Secreto | Impacto si fuera real |
|---|---|
| `PAYPAL_CLIENT_SECRET` (producción) | Fraude financiero directo: iniciar reembolsos, consultar transacciones |
| `AWS_ACCESS_KEY_ID`/`SECRET` | Desde filtrar/borrar el bucket S3 hasta pivotar a otros servicios de la cuenta AWS |
| `DISCORD_BOT_TOKEN` | Control del bot oficial de la comunidad |
| `MAILGUN_API_KEY` | Enviar correo desde el dominio legítimo — infraestructura de phishing con reputación ya verificada |
| `CLOUDFLARE_API_TOKEN` | Manipulación de DNS: redirección del dominio, interceptación de tráfico |
| `JWT_SECRET` | Forjar tokens de sesión/API válidos como cualquier usuario, incluido admin |

## 💥 Impacto

> [!CAUTION]
> Compromiso directo y confirmado de la base de datos de la aplicación y de la cuenta administradora por una contraseña real, trivial y de diccionario (`letmein`) — sin necesitar la SQLi de [F-012](F-012-sqli-login-bypass-auth.md) en absoluto. Si las otras aplicaciones de BigShop comparten patrones de configuración o credenciales, este fichero es también el punto de partida natural para probar reutilización de credenciales entre apps.

## 🛡️ Remediación

- Cargar todos los secretos exclusivamente desde variables de entorno o un gestor de secretos dedicado (Vault, AWS Secrets Manager, Docker secrets) — nunca hardcodeados en código fuente versionado.
- Rotar inmediatamente todas estas credenciales, considerándolas comprometidas.
- Eliminar las contraseñas de seed en texto plano del código: generar contraseñas aleatorias por entorno en el primer arranque.

## 🔗 Hallazgos relacionados

- [F-016 — Escalada de privilegios local](F-016-escalada-privilegios-sudo-php.md): el acceso como `pepe` que permitió leer este fichero.
- [F-018 — Toma de cuenta vía tokens filtrados en mail.log](F-018-toma-cuenta-tokens-mail-log.md): la segunda ruta independiente de toma de cuenta admin, confirmada aquí a nivel de base de datos.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
