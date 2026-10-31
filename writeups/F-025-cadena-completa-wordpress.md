# ⛓️ F-025 — Cadena completa: de fuerza bruta a compromiso total del servidor

![Severidad](https://img.shields.io/badge/severidad-cr%C3%ADtico-critical) ![CVSS](https://img.shields.io/badge/CVSS-9.8-red) ![CWE](https://img.shields.io/badge/CWE-94-blue) ![App](https://img.shields.io/badge/app-WordPress-informational) 🏆

> [!IMPORTANT]
> Un diccionario de contraseñas + una función legítima del panel de administración (editor de archivos) = compromiso completo del servidor WordPress. Sin ningún CVE, sin ninguna técnica de explotación avanzada.

## 📖 Contexto

A diferencia de PenguinWave ([F-009](F-009-cadena-completa-compromiso-admin.md)) y PixelForge ([F-015](F-015-cadena-completa-invitado-rce.md)), la cadena de WordPress no tiene rutas alternativas — es una secuencia **lineal**, pero igual de completa en impacto final.

## 🔬 La cadena, eslabón a eslabón

```
F-019  Enumeración de usuarios (29 cuentas, admin incluida)
   ↓
F-021  Fuerza bruta sin rate-limit → admin:qwerty
   ↓
F-022  Theme File Editor → RCE → reverse shell como bigshop
   ↓
F-023  wp-config.php → credenciales BD + claves de autenticación + PII de 22 usuarios
   ↓
F-024  Intento de escalada de privilegios — identificado, no explotable desde bigshop
```

| Eslabón | Qué aporta |
|---|---|
| [F-019](F-019-enumeracion-usuarios-wordpress.md) | Diccionario de usuarios reales, incluida `admin`, sin autenticación |
| [F-021](F-021-fuerza-bruta-admin-qwerty.md) | `wp-login.php` sin rate-limit real → `qwerty` cae en segundos |
| [F-022](F-022-rce-theme-file-editor.md) | Editor de archivos del panel → RCE directa, sin exploits |
| [F-023](F-023-secretos-wp-config.md) | `wp-config.php`: BD + claves de autenticación + PII de 22 usuarios |
| [F-024](F-024-grupo-workers-etc-no-explotado.md) | Escalada identificada, no alcanzable desde el usuario comprometido |

## 💥 Impacto

> [!CAUTION]
> Compromiso administrativo y de ejecución de código del servidor WordPress completo, alcanzado íntegramente con técnicas de caja negra estándar (enumeración, fuerza bruta de diccionario, abuso de una función legítima del panel). No hizo falta ningún CVE del core, tema o plugins — el punto débil fue enteramente la gestión de credenciales y la falta de controles compensatorios (rate-limit, `DISALLOW_FILE_EDIT`, gestión de secretos).

A diferencia de PixelForge, no se alcanzó `root` del sistema operativo — la escalada quedó identificada pero no explotada ([F-024](F-024-grupo-workers-etc-no-explotado.md)), un resultado honesto que también forma parte del valor de la auditoría: no todo compromiso real llega a root, y reportarlo así (en vez de forzar o inventar una vía) es lo correcto.

## 🛡️ Remediación — por orden de prioridad

1. **Contraseña robusta + rate-limit real en `wp-login.php`** — corta la cadena en el primer eslabón.
2. **`DISALLOW_FILE_EDIT` en `wp-config.php`** — neutraliza la vía de RCE aunque una cuenta admin vuelva a comprometerse.
3. **Externalizar secretos de `wp-config.php`** a variables de entorno o gestor dedicado.
4. **Corregir los permisos de `/etc`** a nivel de sistema operativo, independientemente de que no se haya podido explotar en esta ocasión.

## Hallazgos relacionados

Todos los de esta cadena: [F-019](F-019-enumeracion-usuarios-wordpress.md) · [F-021](F-021-fuerza-bruta-admin-qwerty.md) · [F-022](F-022-rce-theme-file-editor.md) · [F-023](F-023-secretos-wp-config.md) · [F-024](F-024-grupo-workers-etc-no-explotado.md)

---

⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
