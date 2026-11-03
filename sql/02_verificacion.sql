-- Consultas de solo lectura.
SELECT 'centros' AS tabla, count(*) AS filas FROM electoral.centros_votacion
UNION ALL SELECT 'mesas', count(*) FROM electoral.mesas_votacion
UNION ALL SELECT 'resultados', count(*) FROM electoral.resultados_elecciones
UNION ALL SELECT 'empadronados', count(*) FROM electoral.empadronados;

SELECT estado_registro, count(*) FROM electoral.empadronados GROUP BY estado_registro;

-- Deben devolver cero filas.
SELECT codigo_centro_votacion, count(*) FROM electoral.centros_votacion
GROUP BY codigo_centro_votacion HAVING count(*) > 1;
SELECT anio_eleccion,tipo_eleccion,vuelta,codigo_mesa,partido,count(*)
FROM electoral.resultados_elecciones
GROUP BY anio_eleccion,tipo_eleccion,vuelta,codigo_mesa,partido HAVING count(*) > 1;
SELECT e.id_empadronado FROM electoral.empadronados e
LEFT JOIN electoral.centros_votacion c USING (codigo_centro_votacion)
WHERE c.id_centro IS NULL;

SELECT observacion FROM electoral.carga_log
WHERE proceso='watermark:empadronados' ORDER BY id_log DESC LIMIT 1;
SELECT proceso,observacion,fecha FROM electoral.carga_log ORDER BY id_log DESC LIMIT 10;
