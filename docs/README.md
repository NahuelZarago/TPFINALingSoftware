# Documentación

- `uml/proxy_activity.png|svg|dot`: UML de actividad (patrón Proxy).
- `uml/observer_state.png|svg|dot`: UML de estado (patrón Observer).
- `api/`: documentación de la API generada con `pdoc tpfi -o docs/api`
  (la regenera el workflow de CI en cada push/PR; no se versiona).

Para regenerar los diagramas: `dot -Tpng -Gdpi=140 uml/proxy_activity.dot -o uml/proxy_activity.png`.
