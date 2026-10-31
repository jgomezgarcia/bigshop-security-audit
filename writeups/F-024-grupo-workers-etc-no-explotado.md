# 🔐 F-024 — Grupo `workers` con permisos de escritura en /etc (no explotado)

![Severidad](https://img.shields.io/badge/severidad-medio-yellow) ![CVSS](https://img.shields.io/badge/CVSS-6.0-yellow) ![CWE](https://img.shields.io/badge/CWE-732-blue) ![App](https://img.shields.io/badge/app-WordPress-informational)

> [!IMPORTANT]
> `/etc` es escribible por el grupo `workers` sin *sticky bit* — una vía real a root para quien pertenezca a ese grupo. Identificado durante la post-explotación, pero **no explotable** desde el usuario obtenido en esta auditoría.

## 📖 Contexto

Con la shell de [F-022](F-022-rce-theme-file-editor.md), se enumeraron las vías habituales de escalada de privilegios (SUID, sudo, capabilities, cron). La mayoría no dio nada — pero los permisos de `/etc` destacaron.

## 🔬 Explotación paso a paso (investigación, no explotación)

```bash
stat /etc
```

```
Uid: (    0/    root)   Gid: ( 1000/ workers)
Access: (0775/drwxrwxr-x)
```

En Linux, para borrar o renombrar una entrada dentro de un directorio hace falta permiso de escritura sobre el **directorio contenedor**, no sobre el archivo en sí. Sin *sticky bit* (a diferencia de `/tmp`, que sí lo tiene por diseño), cualquier miembro del grupo `workers` podría **borrar y recrear ficheros críticos de `/etc`** (`cron.d/*`, `passwd`, `sudoers`...) aunque sean propiedad de `root` — por ejemplo, reemplazando un cron job legítimo por uno propio que se ejecute como root.

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
