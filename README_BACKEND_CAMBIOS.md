# Sistema de Pacientes Crónicos - Backend

## Módulos implementados
- `/auth` registro, login y perfil
- `/pacientes` CRUD de pacientes
- `/medicamentos` CRUD de medicamentos
- `/historial-clinico` historial médico por paciente
- `/pedidos` pedidos de medicamentos con descuento automático de stock
- `/alertas` alertas de refill automáticas y manuales

## Colecciones Firebase RTDB
- `users`
- `pacientes`
- `medicamentos`
- `historial_clinico`
- `pedidos`
- `alertas`
- `counters`

## Variables recomendadas
- `FIREBASE_DB_URL`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `JWT_SECRET`
- `JWT_EXPIRES`
- `ALERT_SCAN_INTERVAL_SECONDS`
- `ENABLE_ALERT_SCANNER`
- `ALERT_WINDOW_DAYS`

## Ejemplos rápidos
### Crear paciente
POST `/pacientes`
```json
{
  "nombres": "María",
  "apellidos": "López",
  "telefono": "55554444",
  "enfermedades_cronicas": ["diabetes", "hipertension"],
  "alergias": ["penicilina"],
  "numero_expediente": "EXP-001"
}
```

### Crear medicamento
POST `/medicamentos`
```json
{
  "codigo": "MET-500",
  "nombre": "Metformina 500 mg",
  "precio": 10.5,
  "stock": 100,
  "stock_minimo": 15,
  "refill_dias": 30
}
```

### Crear pedido
POST `/pedidos`
```json
{
  "paciente_id": "ID_DEL_PACIENTE",
  "dias_alerta_anticipacion": 5,
  "items": [
    {
      "medicamento_codigo": "MET-500",
      "cantidad": 2
    }
  ]
}
```

### Ejecutar escaneo manual de alertas
POST `/alertas/scan`
