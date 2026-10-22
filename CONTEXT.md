CONTEXT.md - Uso de herramientas de IA y trabajo realizado

Este archivo cumple el requisito del TPFI de registrar el uso de IA. Se utilizó Claude (Anthropic) como asistente para el diseño, la generación de código y la resolución de errores. El autor instaló el entorno, configuró AWS, ejecutó y probó cada programa, corrigió los problemas que fueron apareciendo y es responsable del contenido entregado.

1. Resumen de lo realizado por el autor
Preparación del entorno: Python, entorno virtual, boto3, AWS CLI y aws configure con las credenciales de la cátedra, primero en Linux y luego en Windows.
Lectura de los enunciados y del material de referencia de la cátedra (IS2_TPFI_*), y definición del alcance de cada entrega.
Ejecución de todas las herramientas de calidad (black, ruff, mypy, pyright, bandit, pytest) y corrección de lo que fallaba.
Pruebas reales contra DynamoDB: set, get, list y subscribe, y verificación de los registros de auditoría en CorporateLog.
Creación del repositorio privado en GitHub, control de que no se subieran credenciales y puesta en verde del CI.
Generación del esqueleto con CookieCutter y decisión de qué adoptar.
Revisión y entendimiento del código para poder explicarlo y defenderlo.
2. Estado de cada consigna del enunciado
Consigna	Estado	Dónde
singletonproxyobserver.py (servidor, {-p=port}{-v}, puerto 8080 por defecto)	Hecha	raíz, tpfi/server.py
singletonclient.py (-i=input.json {-o=output.json}{-v})	Hecha	raíz, tpfi/clients.py
observerclient.py ({-s=host}{-p=port}{-o=output.json}, reintento cada 30 s)	Hecha	raíz, tpfi/clients.py
Patrón Singleton para CorporateData y CorporateLog	Hecha	tpfi/singleton.py, tpfi/db/
Patrón Observer para las suscripciones	Hecha	tpfi/observer.py
Patrón Proxy con pista de auditoría en CorporateLog	Hecha	tpfi/proxy.py
Logging con -v	Hecha	tpfi/logging_setup.py
Pruebas de aceptación (camino feliz con CorporateLog, argumentos mal formados en cada programa, requerimiento sin datos mínimos, servidor caído, doble arranque)	Hechas	tests/test_acceptance.py
Pruebas que demuestran los patrones	Hechas	tests/test_singleton.py, test_observer.py, test_proxy.py
UML de actividad (proxy) y de estado (observer)	Hecha	docs/uml/
Entorno virtual y requirements.txt	Hecha	venv/ (local), requirements.txt
Esqueleto CookieCutter	Hecha	docs/cookiecutter.md
CONTEXT.md, README.md, CHANGELOG.md, VERSION, BUILD	Hecha	raíz
Licencia MIT	Hecha	LICENSE
Documentación con pdoc	Configurada (se genera en el CI y con pdoc tpfi -o docs/api)	.github/workflows/ci.yml
ruff, black, PEP 8 y PEP 257	Hecha	pyproject.toml
mypy y pyright	Hecha	pyproject.toml
pytest con cobertura >= 85 %	Hecha	pyproject.toml
bandit	Hecha	pyproject.toml
CI/CD en GitHub Actions	Hecha (en verde)	.github/workflows/ci.yml
Trufflehog	No realizada (opcional); se controló a mano con git grep	-
3. Registro de consultas a la IA
2026-10-13
Instalación de boto3, AWS CLI y configuración de credenciales a partir de la nota de aplicación "Arquitectura AWS Python".
Error externally-managed-environment en Ubuntu: se resolvió con un entorno virtual.
Error ModuleNotFoundError: boto3: el entorno virtual no estaba activado.
Primer avance del TPFI a partir del enunciado: esqueleto del proyecto, singletons, observer, proxy, protocolo y tests iniciales.
Error de pyproject.toml ("Cannot declare ('tool', 'ruff') twice"): se unificaron las secciones duplicadas.
Test fallando en decode con bytes no UTF-8: se movió la decodificación dentro del try.
Avisos de ruff (D301) y pyright (atributo Table de boto3): se ajustó el docstring y se tipó el recurso como Any.
Análisis del script IS2_TPFI_insert.py para definir los campos de auditoría.
Consulta sobre si es válido usar IA y resumen del avance para el profesor.
2026-10-20
Continuación hasta completar las consignas: servidor TCP, singletonclient, observerclient, interfaz DataService, descubrimiento de claves, tests de aceptación, diagramas UML (Graphviz), README y CHANGELOG.
2026-10-21 / 2026-10-22
Reinstalación del entorno en Windows (Python, venv, AWS CLI).
Test de reintentos del observer fallando en Windows: las conexiones rechazadas tardan unos 2 s, así que se cambió para leer los reintentos desde un archivo en lugar de contarlos por tiempo.
Revisión de .gitignore para no subir credenciales, y primer push al repositorio privado.
Falla del CI por ruff W292 (falta de salto de línea final): se corrigió con black . y el CI quedó en verde.
Generación del esqueleto con cookiecutter-pypackage. Se adoptó el andamiaje del repositorio y se descartó el layout src/ (detalle en docs/cookiecutter.md).
Mejora del README y armado de la demostración con tres terminales.