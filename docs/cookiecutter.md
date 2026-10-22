# Esqueleto generado con CookieCutter

Se generó con `cookiecutter-pypackage` (audreyfeldroy) usando el nombre de proyecto
`TPFI` e import `tpfi`, licencia MIT, versión 0.2.0.

## Adoptado de la plantilla
- `.editorconfig`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Plantillas de issues y de pull request (`.github/`)
- Licencia MIT, nombre del paquete `tpfi` y metadatos del autor

## No adoptado (y por qué)
- Layout `src/`, `hatchling`, `uv`, `ty`, `typer` y `zensical`: el enunciado exige
  black, ruff, mypy, pyright, bandit y pdoc, y el CI ya los ejecuta con layout plano.
- Workflows de publicación en PyPI, CodeQL y zizmor: fuera del alcance del TP.
- `CHANGELOG/`: se mantiene `CHANGELOG.md` único, como pide el enunciado.
