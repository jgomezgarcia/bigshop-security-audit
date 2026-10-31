# 🌐 WordPress (puerto 80)

⬅ [PixelForge](../pixelforge/README.md) · [README principal](../../README.md)

**Estado:** 🚧 en curso — 2 hallazgos confirmados ([ver tabla](../../README.md#-hallazgos-confirmados) · [writeups individuales](../../writeups/))

Tienda/escuela de surf ficticia, "Salt & Stoke Surf Co.".

## Reconocimiento

Accediendo directamente por IP (`172.17.0.2`) se sirve el vhost **por defecto** de Apache (instalación WordPress genérica, "Hello world!") — el sitio real solo aparece enviando `Host: bigshop.local`, confirmando virtual-hosting:

```bash
echo "172.17.0.2  bigshop.local" | sudo tee -a /etc/hosts
```

<img src="../../assets/35-wordpress-home-salt-stoke.png" width="650">

Reconocimiento manual de las rutas críticas de WordPress, antes de automatizar:

| Ruta | Resultado |
|---|---|
| `/wp-json/wp/v2/users` | Lista usuarios sin autenticación |
| `/xmlrpc.php` | Habilitado — acepta `POST` |
| `/wp-cron.php` | Accesible, se ejecuta en cada visita |

WPScan confirma y amplía el reconocimiento manual (output completo en [`scans/wpscan-bigshop-puerto80.txt`](../../scans/wpscan-bigshop-puerto80.txt)):

```bash
wpscan --url http://bigshop.local -e vp,vt,u --random-user-agent
```

WordPress 7.1.4 (última versión), tema **Twenty Twenty-One** al día (sin CVEs), plugin **`booking-calendar-pro` v2.4.1** con un XSS reflejado conocido vía `calendar_id` ([CVE-2024-12077](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-12077), *pendiente de explotar*), registro de usuarios abierto, y 29 usuarios enumerados.

## Cronología de la auditoría

<details open>
<summary><b>1️⃣ Enumeración masiva de usuarios sin autenticación (29 cuentas)</b></summary>

<br>

Combinando la API REST y el generador RSS (confirmado con `wpscan -e u`), se identificaron **29 cuentas reales**, incluida `admin`:

<img src="../../assets/37-wordpress-wpjson-users.png" width="650">

```
admin, Jack Osei, Luna De La Cruz, William Ferro, Harper Lemos, Amelia Santos,
James Moreau, Charlotte King, Ethan Walsh, ava-thompson, charlotte-king,
emma-castillo, ethan-walsh, harper-lemos, isabella-dubois, jack-osei,
james-moreau, kelly-rincon, liam-okafor, lucas-fischer, luna-delacruz,
mateo-silva, mia-nakamura, noah-bennett, oliver-reyes, sofia-marino, william-ferro
```

Diccionario completo de usuarios válidos sin adivinar ni uno — incluida la cuenta `admin`, el objetivo de mayor valor.

</details>

<details>
<summary><b>2️⃣ Denegación de servicio parcial vía wp-cron.php</b></summary>

<br>

`wp-cron.php` se ejecuta en **cada visita**, no en segundo plano. Primera prueba, sin efecto perceptible:

```bash
ab -n 5000 -c 50 -k http://bigshop.local/wp-cron.php
```

Segunda prueba, con mayor intensidad — avance notablemente más lento, interrumpida manualmente tras 12.000 de 20.000 peticiones:

```bash
ab -n 20000 -c 300 -k http://bigshop.local/wp-cron.php
```

<img src="../../assets/36-wordpress-wpcron-dos-ab-slow.png" width="500">

No se confirmó caída total en las pruebas realizadas (nota de alcance: al interrumpirse con `Ctrl+C`, `ab` no imprimió estadísticas finales — la evidencia de impacto es cualitativa, no una cifra exacta), pero el patrón de ralentización progresiva (50→300 de concurrencia) indica un servicio expuesto a un ataque de disponibilidad escalable. No se escaló más allá de esta prueba: el mismo host aloja las otras 3 apps del laboratorio, incluida StreamWave, aún pendiente de auditar. Lab reiniciado tras la prueba.

</details>

*(pendiente: explotación del XSS reflejado en `booking-calendar-pro`, y revisión del registro de usuarios abierto)*

---

⬅ [README principal](../../README.md)
