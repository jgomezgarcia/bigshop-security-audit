# 🔓 F-032 — Política de contraseñas inexistente y sin rate-limit en login

![Severidad](https://img.shields.io/badge/severidad-medio-yellow) ![CWE](https://img.shields.io/badge/CWE--521-blue) ![App](https://img.shields.io/badge/app-StreamWave-red)

> [!NOTE]
> `/register` acepta contraseñas de un solo carácter, y `/login` no tiene rate-limit ni bloqueo de cuenta (20 intentos fallidos seguidos, todos `200` sin throttling). Su impacto práctico queda eclipsado por [F-030](F-030-jwt-auth-bypass-streamwave.md), que ya filtra todas las contraseñas reales — se documenta igualmente como debilidad estructural independiente.

## 🔬 Pruebas realizadas

```bash
# Contraseña de 1 caracter aceptada
curl -i -X POST http://172.17.0.2:9090/register -d "display_name=t&username=weak_pw_test&password=1"
# -> 302 Found

# Sin rate-limit: 20 intentos fallidos, todos 200
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://172.17.0.2:9090/login -d "username=admin&password=wrong$i"
done
# -> 200 200 200 200 ... (20 veces, sin bloqueo)
```

**Comprobación positiva:** no hay enumeración de usuarios vía `/login` — la respuesta ante usuario inexistente y ante contraseña incorrecta de un usuario real es idéntica (mismo `Content-Length`, mismo `ETag`). El registro sí rechaza correctamente usernames duplicados.

## 💥 Impacto

Combinado con la ausencia de rate-limit, cualquier contraseña débil sería fuerza-bruteable en un tiempo razonable. No es la vía principal de compromiso de esta auditoría (esa es [F-030](F-030-jwt-auth-bypass-streamwave.md)), pero existiría igualmente aunque se corrigiera el JWT.

## 🛡️ Remediación

- Longitud mínima (≥10-12 caracteres) y verificación contra listas de contraseñas filtradas conocidas.
- Rate-limiting / bloqueo temporal tras varios intentos fallidos, por IP y por cuenta.
- Mantener el comportamiento actual de no diferenciar "usuario inexistente" de "contraseña incorrecta".

---
⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
