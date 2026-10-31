# 📝 F-014 — Política de registro débil

![Severidad](https://img.shields.io/badge/severidad-medio-yellow) ![CVSS](https://img.shields.io/badge/CVSS-5.3-yellow) ![CWE](https://img.shields.io/badge/CWE-521-blue) ![App](https://img.shields.io/badge/app-PixelForge-purple)

> [!IMPORTANT]
> `register.php` no aplica ninguna validación real del lado del servidor: contraseña de 1 carácter aceptada, sin verificación de email, cuenta operativa al instante. Por sí solo es un fallo moderado — pero es la llave que convierte el RCE de subida de ficheros en un fallo alcanzable por **cualquier visitante anónimo**.

## 📖 Contexto

Al auditar el flujo de alta de PixelForge, `register.php` resultó aceptar prácticamente cualquier entrada sin fricción. No es un fallo espectacular por sí mismo, pero resultó ser la pieza que faltaba para entender por qué el RCE de [F-013](F-013-subida-fichero-rce.md) es explotable sin necesidad de la inyección SQL de [F-012](F-012-sqli-login-bypass-auth.md).

## 🔬 Explotación paso a paso

**1. Registrar una cuenta con datos mínimos/inventados:**

```
POST /register.php
username=qatester1&email=qatester1@example.com&password=a
→ 302 Found, Location: /login.php
```

Contraseña de **un solo carácter**, aceptada sin queja. El email (`qatester1@example.com`) es inventado — no hay ningún correo de confirmación ni estado "pendiente de verificar".

**2. Confirmar que la cuenta ya es completamente funcional:**

```
POST /login.php
username=qatester1&password=a
→ 302 Found, Location: /account.php
```

Login inmediato con esa misma contraseña de un carácter.

**3. Bonus — qué recibe la cuenta nueva:** 50 créditos ("Forge wallet") y 3 juegos ya en su biblioteca (`Aether Drift`, `Hollowpeak`, `Voidcell`) de regalo. No es en sí un fallo de seguridad, pero confirma que no hay ninguna fricción real entre "visitante anónimo" y "cuenta funcional con acceso al área autenticada".

## 💥 Impacto

> [!CAUTION]
> Por sí solo, un bajo nivel de exigencia en el registro no es crítico. El impacto real es que **elimina cualquier coste o fricción para un atacante** que quiera llegar al área autenticada: no necesita un email real, ni una contraseña memorable, ni esperar ninguna verificación — justo lo que necesita para alcanzar el formulario de subida de avatar de [F-013](F-013-subida-fichero-rce.md), convirtiendo la ejecución remota de código en un fallo alcanzable por **cualquier visitante anónimo**, sin depender siquiera de la inyección SQL de [F-012](F-012-sqli-login-bypass-auth.md). Ver la cadena completa en [F-015](F-015-cadena-completa-invitado-rce.md).

## 🛡️ Remediación

- Exigir una política de contraseña mínima razonable (longitud ≥ 8–10, sin necesidad de complejidad excesiva) validada en servidor, no solo en el cliente.
- Verificar la propiedad del email mediante un enlace/token de confirmación antes de activar la cuenta, o al menos antes de habilitar funciones sensibles como la subida de ficheros.
- Aplicar algún control anti-automatización en el registro (CAPTCHA, rate-limit por IP) si el abuso de cuentas desechables es una preocupación del negocio.

## 🔗 Hallazgos relacionados

- [F-013 — Subida de fichero sin restricciones → RCE](F-013-subida-fichero-rce.md): el destino final al que da acceso una cuenta recién registrada.
- [F-012 — Inyección SQL en login.php](F-012-sqli-login-bypass-auth.md): la ruta alternativa (Ruta A) que llega al mismo RCE sin pasar por el registro.
- [F-015 — Cadena completa: invitado anónimo → RCE](F-015-cadena-completa-invitado-rce.md): documenta esta vía (Ruta B) de principio a fin.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
