# CONTEXT.md - Uso de herramientas de IA

Registro de prompts utilizados (requisito del TPFI). Herramienta: Claude
(Anthropic). El código fue revisado, ejecutado y verificado por el autor.

## 2026-10-13

1. "necesito hacer todo esto" (adjunto: nota de aplicación Arquitectura AWS Python).
   Resultado: guía de instalación de boto3, AWS CLI y configuración de credenciales.
2. Consulta por el error `externally-managed-environment` en Ubuntu.
   Resultado: uso de un entorno virtual (venv).
3. Consulta por `ModuleNotFoundError: boto3` (venv no activado).
4. "empecemos hacer algo un 20-30% hoy" (adjunto: enunciado del TPFI).
   Resultado: esqueleto del proyecto, singletons, observer, proxy, protocolo y tests.
5. Error de `pyproject.toml` ("Cannot declare ('tool', 'ruff') twice").
   Resultado: unificar las secciones duplicadas.
6. Salida de pytest con un test fallando (`decode` con bytes no UTF-8).
   Resultado: mover la decodificación dentro del `try`.
7. Avisos de ruff (D301) y pyright (atributo `Table` de boto3).
   Resultado: ajuste del docstring y tipado del recurso como `Any`.
8. Consulta sobre el script `IS2_TPFI_insert.py` (campos del log).
9. "armame un texto de todo lo que hiciste" y consulta sobre si es válido usar IA.

## 2026-10-20

10. "continuemos Y terminemos todo".
    Resultado: servidor TCP, `singletonclient`, `observerclient`, interfaz
    `DataService`, descubrimiento de claves, tests de aceptación, diagramas UML
    (Graphviz) y actualización de README y CHANGELOG.

## 13. Instalación en Windows, prueba real en AWS, CI y CookieCutter (2026-10-21/22)

- Reinstalación del entorno en Windows (Python, venv, AWS CLI, `aws configure`).
- Prueba real contra DynamoDB: set/get/list y registros de auditoría en CorporateLog,
  verificados con `ver_log.py` (filtra por CPUid).
- Se corrigió el test de reintentos del observer para Windows: los connect rechazados tardan
  unos 2 s, así que ahora se leen los reintentos de un archivo en lugar de contarlos por tiempo.
- Primer push a GitHub (repositorio privado) con `.gitignore` ampliado para credenciales.
  El CI falló por ruff W292 (falta de salto de línea final); se corrigió con `black .`
  y quedó en verde.
- Esqueleto CookieCutter generado con `cookiecutter-pypackage`; se adoptó el andamiaje del
  repositorio y se descartó el layout `src/` (detalle en `docs/cookiecutter.md`).
- Prompt usado con la IA: "Se generó el esqueleto, estos son los archivos, ¿cuáles copio?".
