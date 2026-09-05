# Laboratorio 01: Estructuras de Control en Go

Solución del laboratorio de **Programación Concurrente y Distribuida**. El
programa simula un procesador de pagos (PSP) y cubre validación, cálculo de
comisiones, clasificación de riesgo, procesamiento de lotes y control de flujo.

## Requisitos

- Go 1.22 o posterior.

## Ejecución

Desde `labs/go`:

```bash
go run ./week02
```

Salida:

```text
=== Procesamiento de lote ===
Pagos válidos: 4
Total procesado: 10900.00
Pagos sospechosos: 1

=== Control de flujo ===
Pago procesado: 100.00
Pago procesado: 200.00
Pago procesado: 300.00
Límite de seguridad alcanzado: 15000.00. Procesamiento detenido.

=== Caso integrador ===
Tx 1: Aprobada | Comisión: 3.00 | Riesgo: Aprobado
Tx 2: Rechazada | Monto inválido
Tx 3: Revisión manual | Comisión: 60.00
Tx 4: Aprobada | Comisión: 7.00 | Riesgo: Riesgo alto

=== Bonus: validación de horario ===
10:00 permitido: true
18:00 permitido: false
```

## Pruebas

```bash
go test -race ./...
go vet ./...
```

Las pruebas cubren casos válidos, límites (`0`, `5000`, `10000` y horario),
normalización de entradas, métodos desconocidos, prioridad de reglas y el flujo
integrador completo.

## Organización

- `main.go`: datos de ejemplo y presentación de resultados.
- `psp.go`: reglas de negocio y caso integrador.
- `psp_test.go`: pruebas unitarias de todas las partes y del bonus.

El paquete forma parte del módulo `upc.edu.pe/concurrente` definido en
`labs/go/go.mod`.

## Decisiones tomadas

1. Las validaciones se aplican en este orden: monto, moneda y estado del
   usuario. Se retorna el primer incumplimiento para producir un motivo de
   rechazo determinista.
2. Monedas, países y métodos de pago se normalizan para tolerar mayúsculas,
   minúsculas y espacios accidentales.
3. La comisión representa solo el importe cobrado por el PSP. Por ejemplo,
   Visa sobre `100` retorna `3`, no `103`.
4. En riesgo, `monto > 5000` tiene precedencia y produce `Revisión manual`, tal
   como aparece primero en el enunciado. Si no se cumple, un país distinto de
   `PE` produce `Riesgo alto`.
5. El total del lote suma únicamente pagos mayores que cero. La cantidad de
   sospechosos es un subconjunto de los pagos válidos.
6. Una transacción mayor que `10000` activa el corte y no llega a procesarse;
   tampoco se recorren elementos posteriores.
7. Para el bonus, el horario de operación es el intervalo `[09:00, 18:00)`:
   las 09:00 están incluidas y las 18:00 ya no.

El laboratorio se mantiene secuencial deliberadamente: el objetivo evaluado es
el uso de `if`, `switch`, `for`, `continue` y `break`; introducir goroutines en
esta etapa añadiría complejidad sin aportar a la rúbrica.
