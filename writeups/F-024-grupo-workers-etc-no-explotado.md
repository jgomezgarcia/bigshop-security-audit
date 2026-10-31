# 🔐 F-024 — Grupo `workers` con permisos de escritura en /etc (no explotado)

![Severidad](https://img.shields.io/badge/severidad-medio-yellow) ![CVSS](https://img.shields.io/badge/CVSS-6.0-yellow) ![CWE](https://img.shields.io/badge/CWE-732-blue) ![App](https://img.shields.io/badge/app-WordPress-informational)

> [!IMPORTANT]
> `/etc` es escribible por el grupo `workers` sin *sticky bit* — una vía real a root para quien pertenezca a ese grupo. Identificado durante la post-explotación, pero **no explotable** desde el usuario obtenido en esta auditoría.

## 📖 Contexto

Con la shell de [F-022](F-022-rce-theme-file-editor.md), se enumeraron las vías habituales de escalada de privilegios (SUID, sudo, capabilities, cron). La mayoría no dio nada — pero los permisos de `/etc` destacaron.

## 🔬 Explotación paso a paso (investigación, no explotación)

**La idea en una frase:** en Linux, el permiso que decide si puedes borrar o sustituir un archivo no es el del archivo, sino el de la carpeta que lo contiene — y la carpeta que guarda los archivos más sensibles del sistema (`/etc`) estaba abierta a un grupo que no debería tener acceso.

Piensa en `/etc` como un cajón de archivador, y cada fichero dentro (`passwd`, `sudoers`, `cron.d/*`) como una carpeta individual que dice "propiedad de root, no tocar". Esa etiqueta solo importa para leer o modificar el *contenido* de la carpeta — para sacarla entera y poner una propia en su lugar, lo único que hace falta es tener la **llave del cajón**. Normalmente esa llave la tiene solo `root`:

```bash
stat /etc
```

```
Uid: (    0/    root)   Gid: ( 1000/ workers)
Access: (0775/drwxrwxr-x) — sin sticky bit
```

Aquí, el grupo `workers` también tiene esa llave. Existe una protección estándar justo para este problema: el *sticky bit* — es la razón por la que `/tmp` (que todo el mundo puede escribir) no deja borrar los archivos de otros ahí, solo los propios. `/etc` no tiene esa protección en este caso. Resultado: cualquier miembro de `workers` podría borrar `/etc/passwd` y poner una versión propia dándose a sí mismo acceso root, sustituir `/etc/sudoers`, o colar una tarea en `/etc/cron.d/` que se ejecute automáticamente como root — sin necesitar permiso sobre esos ficheros individuales, solo sobre el directorio que los contiene.

**Por qué no se pudo explotar:**

```bash
id
# uid=997(bigshop) gid=997(bigshop) groups=997(bigshop)

cat /etc/group | grep workers
# workers:x:1000:pepe
```

El usuario obtenido (`bigshop`) **no pertenece** al grupo `workers` — el único miembro es `pepe`, sin ninguna vía encontrada para pivotar desde `bigshop` (sin `sudo`, sin sus credenciales).

## 💥 Impacto

> [!CAUTION]
> Riesgo real de escalada a root para **cualquier proceso o cuenta comprometida que sí pertenezca al grupo `workers`** — no aplica al vector de entrada confirmado en esta auditoría (WordPress corre como `bigshop`), pero es una debilidad de configuración del sistema que debe corregirse igualmente.

## 🛡️ Remediación

- `/etc` nunca debe ser escribible por un grupo no administrativo. Corregir permisos a `755 root:root`.
- Revisar qué proceso de aprovisionamiento del contenedor dejó `/etc` con ese grupo y permiso — probablemente un error de build, no una decisión intencionada.

## Hallazgos relacionados

- [F-022](F-022-rce-theme-file-editor.md) — el acceso de shell desde el que se investigó esta vía.
- [F-025](F-025-cadena-completa-wordpress.md) — por qué la cadena se detiene aquí sin llegar a root.

---

⬅ [Volver al índice de writeups](README.md) · [README principal](../README.md) · [Informe técnico (PDF)](../docs/informe-BigShop.pdf)
