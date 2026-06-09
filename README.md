# Predictor Mundial - Laboratorio de Despliegue de Instancias Virtualizadas

Proyecto completo para una aplicación educativa de predicción de resultados de partidos del Mundial. Incluye desarrollo de aplicación, contenerización con Docker, escalamiento horizontal, balanceo de carga, documentación y pruebas.

## Funcionalidades implementadas

- Creación de salas/grupos con código de invitación.
- Registro de participantes por sala.
- Listado de partidos programados.
- Registro y actualización de predicciones antes del cierre.
- Publicación de resultados oficiales.
- Tabla general de participantes y puntaje acumulado.
- Reglas de puntuación del laboratorio.
- API REST documentada.
- Tres instancias de backend detrás de Nginx.
- PostgreSQL como base de datos compartida.
- Pruebas unitarias para la lógica de puntuación.
- Script de stress testing con k6.

## Estructura

```text
mundial-predictor-jfarfan/
├── app/
│   ├── app.py
│   ├── db.py
│   ├── scoring.py
│   ├── static/
│   └── templates/
├── docs/
│   ├── api.md
│   ├── arquitectura.md
│   ├── manual_usuario.md
│   └── pruebas.md
├── stress/
│   └── k6-stress.js
├── tests/
│   └── test_scoring.py
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── requirements.txt
└── enunciado/
```

## Requisitos

- Docker Desktop o Docker Engine.
- Docker Compose.
- Opcional: k6 para stress testing.
- Opcional: Python 3.11 para pruebas unitarias locales.

## Ejecución con Docker

Desde la carpeta del proyecto:

```bash
docker compose up --build -d
```

Abrir en el navegador:

```text
http://localhost:8080
```

Ver contenedores:

```bash
docker compose ps
```

Detener:

```bash
docker compose down
```

Detener y borrar datos de PostgreSQL:

```bash
docker compose down -v
```

## Evidenciar balanceo de carga

Ejecutar varias veces:

```bash
curl http://localhost:8080/api/health
```

La respuesta contiene el campo `node`, que permite verificar qué instancia respondió.

También la página web muestra el nodo que atendió la solicitud.

## Reglas de puntuación

El sistema aplica las siguientes reglas:

1. **Resultado exacto:** 5 puntos si el marcador pronosticado coincide con el resultado oficial.
2. **Ganador correcto:** 3 puntos si acierta ganador o empate, aunque no acierte marcador exacto.
3. **Diferencia correcta:** 2 puntos si acierta el margen de goles y el sentido del resultado.
4. **Bonus por racha:** 2 puntos extra por cada tres aciertos consecutivos de ganador.
5. **Predicción anticipada:** 1 punto extra si se registra con más de 24 horas de anticipación.

Criterio aplicado para evitar doble conteo: si el marcador es exacto, se otorgan 5 puntos y no se suman adicionalmente los puntos por ganador ni diferencia. Si no es exacto, sí pueden sumarse ganador correcto y diferencia correcta.

## Pruebas unitarias

Instalar dependencias localmente:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ejecutar:

```bash
python -m pytest tests
```

## Stress testing

Con el sistema levantado:

```bash
k6 run stress/k6-stress.js
```

O:

```bash
BASE_URL=http://localhost:8080 k6 run stress/k6-stress.js
```

## Flujo recomendado de demostración

1. Levantar el proyecto con Docker Compose.
2. Crear una sala.
3. Registrar dos participantes.
4. Guardar predicciones para varios partidos.
5. Publicar resultados oficiales.
6. Actualizar la tabla general.
7. Ejecutar `curl /api/health` varias veces para mostrar balanceo.
8. Mostrar `docs/arquitectura.md` y `docs/pruebas.md` como documentación del entregable.

## Nota académica

La aplicación es educativa y no involucra dinero real, apuestas, pagos ni recompensas económicas.
