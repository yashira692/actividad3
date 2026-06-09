# API REST principal

## Salud

```http
GET /api/health
```

Retorna estado y nodo que atendió la solicitud.

## Salas

```http
POST /api/rooms
Content-Type: application/json

{
  "name": "Mundial 2026",
  "owner_name": "Jaime"
}
```

```http
GET /api/rooms/{code}
```

```http
POST /api/rooms/{code}/participants
Content-Type: application/json

{
  "name": "Ana"
}
```

```http
GET /api/rooms/{code}/leaderboard
```

## Partidos

```http
GET /api/matches
```

```http
POST /api/matches
Content-Type: application/json

{
  "home_team": "Perú",
  "away_team": "Brasil",
  "starts_at": "2026-06-20T20:00:00Z"
}
```

```http
PATCH /api/matches/{match_id}/result
Content-Type: application/json

{
  "home_score": 2,
  "away_score": 1
}
```

## Predicciones

```http
POST /api/predictions
Content-Type: application/json

{
  "participant_id": "uuid",
  "match_id": "uuid",
  "pred_home": 2,
  "pred_away": 1
}
```

```http
GET /api/participants/{participant_id}/predictions
```
