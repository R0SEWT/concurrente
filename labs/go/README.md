# labs/go

Módulo `upc.edu.pe/concurrente`. Un paquete por semana (`week01/`, `week02/`, …),
más `cofinanciamiento/`, que es el trabajo del curso y cruza las dos unidades.

## Requisitos

Go 1.26.7, instalado desde los repos de Fedora (`sudo dnf install golang`).

## Uso

```bash
go test -race ./...              # la red de seguridad; -race NO es opcional acá
go run -race ./week01/cmd/race   # ver el detector reportando la carrera
go vet ./...
```

## Reglas

- **TDD**: el test antes que la goroutine.
- **Siempre `-race`**. Un test de concurrencia que pasa sin `-race` no demuestra nada:
  el entrelazado malo simplemente no ocurrió esta vez.
- Un test no puede *afirmar* que hay una carrera sin volverse flaky. Los ejemplos
  incorrectos van a `weekNN/cmd/<demo>/`, no al test suite.
- Lo que el test no cubre — que el algoritmo sea correcto bajo *todos* los
  entrelazados — se verifica en `../spin/`.
