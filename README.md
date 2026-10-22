# TPFI - Patrón Proxy/Singleton/Observer en entorno AWS

Trabajo Práctico Final Integrador de Ingeniería de Software II (UADER-FCyT).

Servidor de aplicaciones que actúa como **proxy** de acceso a las tablas DynamoDB
`CorporateData` y `CorporateLog`, con el acceso físico implementado como
**singletons** y la notificación de cambios a los clientes suscriptos mediante
**observer**. Versión 0.2.0 (build 2).

## Estado

| Entregable del enunciado | Estado |
|---|---|
| `singletonproxyobserver.py` (servidor TCP) | Hecho |
| `singletonclient.py` | Hecho |
| `observerclient.py` | Hecho |
| Singleton (CorporateData / CorporateLog), Observer, Proxy | Hecho |
| Auditoría en CorporateLog (UUID, sesión, acción, ID, timestamp) | Hecho |
| UML de actividad (proxy) y de estado (observer) | Hecho (`docs/uml/`) |
| Tests unitarios + aceptación (cobertura >= 85 %) | Hecho |
| ruff, black, mypy, pyright, bandit, pdoc, CI en GitHub | Configurados (ver "Calidad") |
| Esqueleto CookieCutter | Pendiente de generar (estructura equivalente armada a mano) |

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
aws configure   # datos de IS2_TPFI_credentials.json (nunca subir a Git)
```

## Uso

Servidor (puerto por defecto `*:8080`):

```bash
python singletonproxyobserver.py {-p=port} {-v}
```

Cliente de consulta/actualización (`ACTION` = `get`, `set` o `list`):

```bash
python singletonclient.py -i=input.json {-o=output.json} {-s=hostname} {-p=port} {-v}
```

Cliente observador (queda suscripto; reintenta cada 30 s si se corta):

```bash
python observerclient.py {-s=hostname} {-p=port} {-o=output.json} {-r=segundos} {-v}
```

`-v` activa los mensajes de debug por salida estándar. Códigos de salida de los
clientes: `0` ok, `1` servidor inalcanzable, `2` argumentos o archivo inválidos,
`3` el servidor respondió Error.

Ejemplos de `input.json`:

```json
{"UUID": "123456789", "ACTION": "get", "ID": "UADER-FCyT-IS2"}
{"UUID": "123456789", "ACTION": "list"}
{"UUID": "123456789", "ACTION": "set", "ID": "UADER-FCyT-IS2", "cp": "3260", "sede": "FCyT"}
```

En `set`, los campos no informados no se modifican y, si la clave no existe,
se crea el registro con los campos no informados en blanco.

## Protocolo

JSON en UTF-8, un mensaje por línea. El cliente envía el requerimiento y el
servidor responde:

| Acción | Respuesta | Conexión |
|---|---|---|
| `get` | el registro de CorporateData | se cierra |
| `set` | el registro modificado (también se retransmite a los observers) | se cierra |
| `list` | array con todos los registros | se cierra |
| `subscribe` | acuse `{"UUID", "ACTION": "subscribe", "STATUS": "OK"}` y luego un registro por cada `set` | queda abierta |
| (cualquier falla) | `{"UUID", "ACTION", "STATUS": "Error", "ERROR": "..."}` | se cierra |

## Arquitectura

```
singletonclient.py ──┐                         ┌─> CorporateDataDB (singleton) ─> DynamoDB CorporateData
observerclient.py ───┼─ TCP ─> ProxyServer ─> CorporateDataProxy ─> CorporateLogDB (singleton) ─> DynamoDB CorporateLog
                     │         (hilo por       └─> SubscriptionManager (observer) ─> sockets suscriptos
                     │          conexión)
```

| Patrón | Dónde | Cómo se cumple |
|---|---|---|
| Singleton | `tpfi/singleton.py`, `tpfi/db/*.py` | `SingletonMeta` (thread-safe); `CorporateDataDB` y `CorporateLogDB` la usan |
| Observer | `tpfi/observer.py` | `Observer` (ABC), `SocketObserver`, `Subject`, `SubscriptionManager`; los caídos se eliminan solos |
| Proxy | `tpfi/proxy.py`, `tpfi/service.py` | `CorporateDataProxy` y `CorporateDataDB` implementan `DataService`; el proxy audita y notifica antes/después de delegar |

Diagramas: [`docs/uml/proxy_activity.png`](docs/uml/proxy_activity.png) (actividad) y
[`docs/uml/observer_state.png`](docs/uml/observer_state.png) (estado).

Estructura:

```
singletonproxyobserver.py  singletonclient.py  observerclient.py   (programas)
tpfi/
  config.py logging_setup.py singleton.py protocol.py service.py net.py
  observer.py proxy.py server.py clients.py cliargs.py
  db/data_table.py db/log_table.py db/keys.py
  apps/        (main() de cada programa)
tests/         (unitarios, de servidor/cliente y de aceptación)
docs/uml/      (diagramas)
```

## Calidad

```bash
black .                          # formatea (ejecutar primero)
ruff check .
black --check .
mypy
pyright
pytest                           # exige cobertura >= 85 %
bandit -r tpfi -c pyproject.toml
pdoc tpfi -o docs/api
```

El workflow `.github/workflows/ci.yml` ejecuta todo lo anterior en cada push/PR
y publica la documentación generada como artefacto.

## Pruebas

- Unitarias y de integración: tablas DynamoDB falsas en memoria y sockets reales
  en localhost (no tocan AWS).
- Aceptación (`tests/test_acceptance.py`): lanzan los tres programas como
  procesos con los comandos del enunciado y verifican el impacto en
  CorporateData y CorporateLog: camino feliz de cada acción, argumentos
  malformados de cada programa, requerimientos sin datos mínimos, cliente con
  servidor caído y doble arranque del servidor.
- Patrones: tests específicos verifican el singleton (una instancia, thread-safe),
  el observer (interfaz abstracta, baja de suscriptores caídos) y el proxy
  (misma interfaz que el sujeto real, auditoría antes de delegar).

## Supuestos

- El nombre de la clave de partición de ambas tablas se consulta a DynamoDB
  (`key_schema`); si la cuenta no permite `DescribeTable` se usa `id`.
- Los campos de auditoría extra (`CPUid`, `platform`, `machine`, `processor`,
  `node`) son atributos adicionales; DynamoDB no exige un esquema fijo.
- `observerclient` agrega cada notificación al archivo `-o` como una línea JSON.

## Licencia

MIT. Ver `LICENSE`.
