# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-10-20

### Added
- Servidor TCP `singletonproxyobserver.py` (`tpfi/server.py`): un hilo por
  conexión, `get`/`set`/`list` responden y cierran, `subscribe` deja el socket
  abierto como observer. Falla con código 1 si el puerto ya está en uso.
- `singletonclient.py` y `observerclient.py` con los argumentos del enunciado
  (`-i`, `-o`, `-s`, `-p`, `-v`) más `-r` (segundos entre reintentos).
- `ObserverClient`: reconecta cada 30 s (parametrizable) y vuelve a suscribirse.
- Interfaz común `DataService` (sujeto real y proxy) para el patrón Proxy.
- Descubrimiento automático de la clave de partición de las tablas DynamoDB.
- Diagramas UML (actividad del proxy y estado del observer) en `docs/uml/`.
- Tests de aceptación que ejecutan los programas como procesos reales.

### Changed
- Protocolo alineado al enunciado: `get`/`set` responden con el registro,
  `list` con un array y los fallos con `{"STATUS": "Error", "ERROR": ...}`.
  Los observers reciben el registro modificado.
- La auditoría usa los campos `UUID`, `sessionid`, `action`, `timestamp`,
  `CPUid` y datos de `platform`.
- `CorporateDataProxy` ya no maneja sockets: el servidor registra al observer.

### Fixed
- `protocol.decode` levanta `ProtocolError` ante bytes que no son UTF-8 válido.
- Tipado del recurso boto3 (pyright) y docstring de `encode` (ruff D301).
- `socket.timeout` reemplazado por `TimeoutError` (ruff UP041).

## [0.1.0] - 2026-10-13

### Added
- Esqueleto del proyecto (paquete `tpfi`, tests, CI, configuración de herramientas).
- `SingletonMeta` (metaclase thread-safe).
- `CorporateDataDB` y `CorporateLogDB`: acceso a DynamoDB como singletons.
- `SubscriptionManager` / `SocketObserver`: patrón Observer.
- `CorporateDataProxy`: patrón Proxy para get/set/list/subscribe con auditoría.
- Protocolo JSON (framing por línea) y validación de requerimientos.
- Tests unitarios con tablas DynamoDB falsas.
