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
