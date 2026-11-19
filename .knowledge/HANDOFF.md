# HANDOFF - localdoc-agent

**Fecha:** 2026-11-19 00:02 GMT-3
**Proyecto:** localdoc-agent
**Branch:** main
**Repo:** https://github.com/gonzoblasco/localdoc-agent
**Autor:** Kanam (CORE)

> HANDOFF generado en el cierre de sesion (2026-11-19). Es el punto de entrada para continuar este proyecto. El informe detallado de la sesion vive en `memory/2026-11-19.md`.

---

## Que se hizo en esta sesion

Implementación y push del fix del verificador en localdoc-agent: normalización de artefactos de extracción y chequeo determinístico de literales del answer, con intentos/verification en el eval. Se corrigió el ejemplo de cláusula 4.2 en el artículo bilingüe del portfolio (ahora cláusula 2, que existe en el corpus demo) y se publicó.

## Estado actual

Tras el review del 2026-11-19: 25/25 tests verdes, HEAD `6594dde`; sitio 8a5f983 live.

## Sobre el nombre del proyecto

El repo, el directorio, la distribucion (`pyproject.toml`) y el slug del programa del Planner son `localdoc-agent`. **"Lucia" es una persona de ejemplo del ejercicio de diseno, no un cliente real**: no aparece en el README ni en ningun artefacto publico, y no debe presentarse como tal. El titulo y el brief del programa del Planner conservan el escenario original por ser registro historico.

## Proximos pasos

1. Rerun del eval con el 12B cuando esté instalado para medir first-try/retry; bio de GitHub; dev.to API key.

## Decisiones y contexto que no debe perderse

- El chequeo de literales se salta en deterministic_calc y canonicaliza fechas/montos. No se inventó el split de reintentos: el eval ahora lo registra.

## Archivos tocados

```
docs/CHANGELOG.md
docs/archive/CHANGELOG-archive.md
```

## Como continuar

1. Leer este HANDOFF (estado actual + proximos pasos).
2. Leer `memory/2026-11-19.md` para el informe completo de la sesion.
3. Verificar el estado real antes de actuar (git, tests, la DB).

---

*Generado por `scripts/session-handoff.py` (session-lifecycle). Se regenera en cada cierre de sesion.*
