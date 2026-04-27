# Simulador de Rede de Filas

Simulador de redes de sistemas de fila com roteamento probabilístico (G/G/C/K).

## Como executar

```bash
python queue_simulator.py
```

## Configuração do Modelo

O modelo implementado segue a especificação da imagem com três filas interconectadas:

### Arquitetura da Rede

```
Chegadas (2.4min) → Fila 1 (G/G/1) → [80%] → Fila 2 (G/G/2/5) → Saída
                                    → [20%] → Fila 3 (G/G/2/10) → Saída
```

### Especificações das Filas

| Fila | Tipo | Servidores | Capacidade | Tempo de Serviço |
|------|------|-----------|-----------|-----------------|
| FILA1 | G/G/1 | 1 | ∞ | 1.0 - 2.0 min |
| FILA2 | G/G/2/5 | 2 | 5 | 4.0 - 6.0 min |
| FILA3 | G/G/2/10 | 2 | 10 | 5.0 - 15.0 min |

### Parâmetros de Simulação

- **Primeiro cliente**: 2.4 minutos
- **Número de aleatórios**: 100.000
- **Roteamento de FILA1**: 80% → FILA2, 20% → FILA3
- **Saídas**: FILA2 e FILA3 encaminham 100% para saída

## Configuração do Arquivo model.yml

O arquivo `model.yml` contém:

```yaml
arrivals:
   FILA1: 2.4

queues:
   FILA1:
      servers: 1
      capacity: 10000
      minService: 1.0
      maxService: 2.0
   FILA2:
      servers: 2
      capacity: 5
      minService: 4.0
      maxService: 6.0
   FILA3:
      servers: 2
      capacity: 10
      minService: 5.0
      maxService: 15.0

network:
   - source: FILA1
     target: FILA2
     probability: 0.8
   - source: FILA1
     target: FILA3
     probability: 0.2
   - source: FILA2
     target: EXIT
     probability: 1.0
   - source: FILA3
     target: EXIT
     probability: 1.0
```

## Parâmetros de Fila (Queue)

- **name**: string - identificador da fila (ex: "G/G/1")
- **B**: tupla (min, max) - intervalo de tempo de serviço
- **C**: inteiro - número de servidores
- **K**: inteiro - capacidade máxima da fila
- **A**: tupla (min, max) - intervalo de tempo entre chegadas (opcional, apenas para fila de origem)

## Saída da Simulação

A simulação gera relatórios incluindo:

- **Distribuição de estados**: tempo acumulado em cada estado (n clientes na fila)
- **Clientes perdidos**: clientes rejeitados por falta de capacidade
- **Tempo total**: duração total da simulação
- **Resumo geral**: informações consolidadas de todas as filas

### Exemplo de Uso Customizado

Para modificar o modelo, edite a função `main()` em [queue_simulator.py](queue_simulator.py):

```python
# Criar filas com parâmetros customizados
queue_1 = Queue(name="G/G/1", B=(1.0, 2.0), C=1, K=10000, A=(1.0, 2.0))
queue_2 = Queue(name="G/G/2/5", B=(4.0, 6.0), C=2, K=5)
queue_3 = Queue(name="G/G/2/10", B=(5.0, 15.0), C=2, K=10)

queues = [queue_1, queue_2, queue_3]

# Executar simulação
simulator = QueueSimulator(queues=queues, count=100_000, first_arrival_time=2.4)

# Configurar roteamento
routing_map = {
    0: [(0.8, 1), (0.2, 2)],  # 80% FILA1→FILA2, 20% FILA1→FILA3
}
simulator.scheduler.set_routing(routing_map)

simulator.run()
```
