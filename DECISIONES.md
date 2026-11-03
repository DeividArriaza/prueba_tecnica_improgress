# Decisiones y supuestos

## Alcance y estrategia

Se carga el DDL recibido sin modificaciones. Se extienden explícitamente las interfaces: el extractor declara checksum en metadata y el loader recibe el contexto transaccional y publica métricas. Una prueba conecta componentes alternativos. Los CSV originales permanecen intactos. La unidad de confirmación es una fuente/fecha: centros y resultados se confirman por separado; si resultados falla, centros puede estar cargado y la reejecución es segura.

## Decisiones técnicas

| Decisión | Alternativas | Motivo |
|---|---|---|
| csv de Python y listas en memoria | pandas, Polars, Spark | Las fuentes mayores tienen unas 20 mil filas; no necesitamos cálculos vectorizados ni un motor distribuido. Leer textos evita perder ceros iniciales. Se retira pandas del template porque no se utiliza. Para millones de filas habría que hacer staging por bloques y validaciones SQL. |
| psycopg2 y SQL por lotes | SQLAlchemy, INSERT individual | El esquema es fijo; SQL explícito permite explicar transacciones, bloqueos y actualizaciones sin un ORM. Los identificadores se componen con psycopg2.sql y los valores se parametrizan. |
| Canonización en mayúsculas sin acentos | title case, inferir nombres correctos | Unifica variantes para comparar. La escritura original queda en los CSV y en los rechazos/advertencias; no afirmamos corregir la ortografía. Los códigos no se convierten a números. |
| Deduplicar después de normalizar | Antes de limpiar | Dos representaciones equivalentes no deben crear entidades diferentes. Copias exactas se cuentan aparte; si una clave presenta atributos distintos, se rechaza el grupo completo sin escoger una fila arbitraria. |
| Comparación staging y UPDATE/INSERT | TRUNCATE, agregar UNIQUE, solo hash | Conserva IDs y evita vaciar tablas; el DDL no permite ON CONFLICT sobre centros/resultados. Un bloqueo global serializa nuestros pipelines y el bloqueo de tabla impide escrituras concurrentes durante el merge. Las restricciones propuestas se documentan aparte. |
| Comparar el contenido además de su hash | Omitir toda carga cuyo hash ya se vio | Una reejecución puede reparar datos faltantes en el destino. El hash identifica el archivo, no sustituye la validación ni es una marca de éxito. |
| Prefect separado del ETL | Airflow, cron | Permite observar ejecuciones y definir reintentos sin exigir el orquestador para ejecutar el CLI. Airflow agrega infraestructura para este alcance; cron necesita implementar seguimiento adicional. |

## Supuestos de negocio

- Una vuelta vacía en legislativa o municipal equivale a ronda 1. Una vuelta vacía presidencial se rechaza.
- La fuente usa coma para miles en enteros y coma o punto decimal en coordenadas. Un formato ambiguo o inválido no se convierte silenciosamente a cero.
- Sexo, área y coordenadas pueden ser nulos porque el modelo los permite y su ausencia no impide identificar la entidad. Fechas del padrón e identificadores sí son obligatorios.
- Las fechas del padrón deben estar entre 1900-01-01 y la fecha de corte, y la inscripción no puede ser posterior a la última actualización. No se confunde la fecha del archivo con la fecha de modificación de cada persona.
- Una baja es un cambio explícito de estado: suspendido o fallecido. Se conserva el registro; los conteos activos filtran estado_registro='activo'. Ausencia en el snapshot no implica borrar: requiere aclaración del proveedor. Una fila rechazada conserva el último valor válido en el destino, si existía.
- Se admite reprocesar la fecha más reciente. Una carga directa anterior al watermark se rechaza. Para corregir historia, rebuild-padron reconstruye todos los snapshots en una tabla temporal y publica atómicamente sin retroceder el corte vigente.

## Hallazgos concretos y tratamiento

| Fuente | Hallazgo / ejemplo | Tratamiento |
|---|---|---|
| Centros | 98 filas; 0104001 tiene 8 y 9 mesas | Ambas filas contradictorias a cuarentena; no inventar la capacidad correcta. El catálogo válido queda con 95 centros; sus dependientes se rechazan por falta de catálogo. Una copia exacta adicional se elimina. |
| Padrón | 25 copias exactas en cada archivo | Conservar una fila por ID y contabilizar duplicadas. |
| Textos | Sololá / mayúsculas / espacios repetidos | Canonización consistente; preservar códigos y el archivo original. |
| Categorías | FEMENINO / f; U / URBANA; 26 a 35 / 26-35 | Mapeos explícitos en config.yaml; los valores desconocidos fuera del dominio se rechazan. |
| Resultados | U.N.E., UNE y une | Canonizar a UNE. Esto descubre conflictos de clave que no eran visibles en los textos originales: no sumar ni elegir entre votos distintos de un mismo partido y mesa. |
| Resultados | Centro 0104999 inexistente | Cuarentena; no crear centros ficticios. |
| Resultados | Votos negativos o votantes mayores que empadronados | Rechazar toda la elección/vuelta/mesa afectada para no cargar un resultado parcial. También se rechazan totales de mesa distintos entre partidos. |
| Resultados | Mesa 0105003-03, presidencial 2023, vuelta 2: 194+221+14+5=434, total declarado 435 | Advertencia de conciliación sin corregir valores. La discrepancia aparece en las 11.564 filas que sobreviven a las reglas estrictas. No hay fuente autorizada para elegir qué cifra corregir. Se permite almacenar con advertencia; no se certifica la suma para análisis de participación. En producción requiere resolver con el proveedor o bloquear su publicación. |

## Política de calidad y métricas

### Escritura de Petén y codificación del texto

Revisión específica del CSV de centros: nombre_departamento presenta `Petén` (5 filas), `Peten` (2), `PETÉN` (2), ` Petén ` (2) y `petén` (2). Son variantes de acentos, espacios y mayúsculas; no se encontraron cadenas como `PetÃ©n` ni el carácter de reemplazo Unicode en los CSV examinados. La transformación actual las convierte a `PETEN`, por decisión explícita de comparación sin acentos. En PostgreSQL se verificaron 13 centros con codigo_departamento `17` y nombre `PETEN`.

El extractor ya interpreta los archivos con `utf-8-sig` y falla si los bytes no son UTF-8 válidos; esa variante admite también el marcador BOM. Se verificó server_encoding=UTF8 y client_encoding=UTF8 en la conexión de Python. UTF-8 permite conservar la tilde, pero no agrega una tilde que falta por escritura ni repara automáticamente texto que ya fue mal decodificado y guardado. Una consola configurada de otra manera puede mostrar mal caracteres que sí están almacenados correctamente.

**Decisión actual:** normalizar representaciones y mantener la escritura original en los CSV. **Alternativa para nombres de presentación:** usar un catálogo geográfico verificado, relacionado por código, para mostrar `Petén` conservando su ortografía. Esa alternativa todavía no está implementada. No aplicar reemplazos globales a nombres de centros, municipios o direcciones: podrían modificar textos que no representan el departamento. Si aparece texto corrupto, comprobar bytes y codificación de origen y registrar una corrección dirigida; evitar ignorar errores de decodificación o convertir repetidamente el texto a ciegas.

Errores de registro van a output/<run_id>/quarantine.jsonl, con línea, original, transformado y motivo. Advertencias van a warnings.jsonl. Error de estructura, archivo faltante, catálogo vacío, fallo SQL o fuente sin filas válidas detiene el proceso con código de error. No se actualiza el watermark si la transacción falla.

metrics.json registra filas leídas, válidas, rechazadas, duplicadas, insertadas, actualizadas, sin cambios, advertencias y duración. Se cumple leídas = válidas + rechazadas + duplicadas. Cargadas significa insertadas + actualizadas; una reejecución puede tener válidas > 0 y cargadas = 0. Los resúmenes exitosos y el watermark se guardan en carga_log dentro de la misma transacción. Los fallos se conservan en archivos y stderr, incluso cuando PostgreSQL no está disponible.

## Fuera de alcance

No se desarrolla dashboard ni se migra el modelo. El historial de asignaciones se propone, no se agrega al DDL entregado. La conexión de alertas externas requiere configurar ALERT_WEBHOOK_URL; sin él queda una alerta en Prefect/stderr. La entrega se realiza mediante PR abierto hacia main, sin fusionarlo. No hay certificación de resultados cuya suma no concilia. Dependencias directas fijadas; un lock completo de transitivas y digest de imágenes sería el siguiente paso para una reproducción estricta.

## Decisiones que requieren especial atención al revisar la entrega

### Rechazar una mesa completa cuando contiene registros inválidos

**Elegimos:** si una elección/vuelta/mesa contiene votos inválidos o un conflicto de partido, rechazar ese conjunto. **Alternativa:** cargar únicamente los partidos válidos. **Motivo:** mostrar solo una parte de los partidos podría aparentar un resultado completo y distorsionar comparaciones. **Consecuencia:** también se rechazan filas individualmente correctas de ese conjunto. Por eso hay 8.669 rechazos sobre 20.328 filas históricas; no debemos presentar esa cantidad como errores independientes de 8.669 filas. El reporte conserva el motivo de propagación y los motivos individuales.

### Conservar las discrepancias de suma como advertencias

**Elegimos:** almacenar las cifras sin corregirlas cuando las demás reglas se cumplen, registrando advertencias. **Alternativas:** rechazar también esas mesas o ajustar votos/totales para que cuadren. **Motivo:** el archivo contiene discrepancias sistemáticas y no hay una fuente autorizada para identificar la cifra correcta; ajustar sería inventar datos. **Consecuencia:** las 11.564 filas admitidas necesitan revisión antes de certificar sus resultados. Esta política sirve para conservar y examinar la información; cargarla no equivale a aprobarla para publicación. Si se exige conciliación estricta como condición de aceptación, deberá cambiarse la política y la cantidad admitida puede ser cero.

### Conservar el último registro válido de una persona

**Elegimos:** si el dato nuevo es rechazado, mantener el dato anterior válido. **Alternativa:** borrar a la persona o reemplazarla con un dato que no cumple las reglas. **Motivo:** un rechazo no demuestra una baja. **Consecuencia comprobada:** quedan 17.932 personas aunque el último archivo tenga 17.898 filas válidas; 34 corresponden a versiones anteriores retenidas. Esa información puede estar desactualizada y debe revisarse con la fuente. El modelo actual no permite marcar por fila su fecha de corte confiable sin evolucionar el esquema; esa limitación se documenta, no se oculta.

### Evitar que un reproceso antiguo retroceda el padrón

**Elegimos:** permitir reejecutar el corte vigente y rechazar fechas anteriores al watermark. **Alternativas:** sobrescribir sin protección, mantener versiones históricas nuevas o reconstruir todos los cortes posteriores. **Motivo:** sobrescribir puede deshacer traslados y bajas recientes; agregar historia modificaría el alcance del modelo entregado. **Consecuencia:** las correcciones de fechas antiguas requieren reconstrucción cronológica en una base separada y validación antes del cambio de destino. Esta es una limitación explícita de la primera versión.

## Dónde encontrar la justificación y su evidencia

- [MEJORAS_MODELO.md](docs/MEJORAS_MODELO.md): problemas ordenados por impacto, consecuencias, DER propuesto y migración. Son propuestas; no cambios aplicados al DDL.
- [ORQUESTACION.md](docs/ORQUESTACION.md): elección de herramienta, dependencias, horario, reintentos, alertas y recuperación por fechas.

Cada cambio posterior debe actualizar la decisión afectada, sus alternativas, su motivo y su evidencia. Distinguimos lo implementado, lo propuesto y lo pendiente para que la documentación describa el estado real del proyecto.


## Verificación final y decisiones operativas

La suite completa aprueba 32 casos tanto localmente como dentro de Docker: lectura CSV estricta, contratos alternativos, rutas configuradas, rechazo de imposibilidades aritméticas, traslados y bajas concretos, created_at estable, reintentos y alerta con mocks, idempotencia y reconstrucción atómica con rollback ante fallo. Los reportes intermedios de reconstrucción se marcan pendiente_commit y después ok o revertido.

La búsqueda de archivos y la carga usan el mismo path_pattern del YAML. quality.on_reject solo admite quarantine y rechaza explícitamente otros valores. La preparación inicial de Prefect también tiene reintentos. Para mantener centros estables frente a otros escritores, su catálogo se bloquea en modo SHARE durante las cargas dependientes.

Votos de un partido mayores que votantes, o nulos más blancos mayores que votantes, se rechazan. La advertencia de conciliación entre partidos no permite esas imposibilidades individuales. El CSV usa modo estricto y los sufijos de mesa aceptan dígitos ASCII positivos.

La reconstrucción exige conservar los snapshots del inicio del historial procesado y completar todos los días hasta el corte final, que no puede ser anterior al watermark. No cambia el DDL ni los archivos originales. El procesamiento sigue en memoria y no pretende cubrir volúmenes distribuidos. La alerta externa necesita un receptor configurado; la suite prueba su contrato sin enviar mensajes reales.
