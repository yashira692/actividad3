# Documentación de pruebas realizadas

## 1. Pruebas unitarias

Las reglas de puntuación están aisladas en `app/scoring.py`. Esto permite probar la lógica sin depender de Flask, Docker ni PostgreSQL.

Ejecutar localmente dentro del proyecto:

```bash
python -m pytest tests
```

Casos cubiertos:

- Marcador exacto otorga 5 puntos.
- Ganador correcto otorga 3 puntos cuando no hay exactitud.
- Diferencia de goles correcta otorga 2 puntos cuando coincide el sentido del resultado.
- Empate correcto se reconoce como ganador correcto.
- Predicción con más de 24 horas de anticipación suma 1 punto.
- Predicción con exactamente 24 horas no recibe bonus.
- Bonus de racha suma 2 puntos por cada tres aciertos consecutivos.

## 2. Prueba funcional manual

1. Levantar el sistema:

```bash
docker compose up --build -d
```

2. Abrir:

```text
http://localhost:8080
```

3. Crear una sala.
4. Copiar el código de invitación.
5. Registrar dos o más participantes.
6. Guardar predicciones para distintos partidos.
7. Publicar resultados oficiales desde la misma pantalla.
8. Actualizar la tabla general y verificar el cálculo de puntaje.

## 3. Evidencia de balanceo

Ejecutar varias veces:

```bash
curl http://localhost:8080/api/health
```

El campo `node` debe alternar entre diferentes contenedores backend, según la distribución de Nginx.

También puede revisarse con:

```bash
docker compose ps
```

Debe observarse la base de datos, Nginx y tres servicios de aplicación.

## 4. Stress testing con k6

El archivo `stress/k6-stress.js` realiza carga gradual contra `/api/health` y `/api/matches`.

Ejemplo de ejecución:

```bash
k6 run stress/k6-stress.js
```

O indicando URL:

```bash
BASE_URL=http://localhost:8080 k6 run stress/k6-stress.js
```

Umbrales definidos:

- Tasa de error HTTP menor al 5%.
- Percentil 95 de latencia menor a 800 ms.

## 5. Criterios de aceptación

El sistema se considera correcto si:

- La app web carga desde `localhost:8080`.
- Se pueden crear salas y participantes.
- Se pueden registrar predicciones antes del cierre.
- Se pueden publicar resultados.
- La tabla general se recalcula automáticamente.
- Existen tres instancias backend activas.
- El balanceador distribuye tráfico entre nodos.
- Las pruebas unitarias de puntuación pasan correctamente.
