# STORY-slim-044: MQ Topic Dependency

| Field | Value |
|-------|-------|
| ID | STORY-slim-044 |
| Status | Done |
| Priority | P3 — Impact 3, Effort 3 |
| Release | 2.5.0 |

## Background

STORY-slim-042 handles synchronous service dependencies (API calls, docker-compose links). Many microservice architectures also use asynchronous message queues (Kafka, RabbitMQ, SQS) where services communicate via topics/queues. This story extends `ServiceParser` to detect producer/consumer relationships from configuration files and source code patterns.

## Requirements

### R1: MQ topic node kind (MUST)

The WorkflowGraph MUST support `topic` as a valid node kind, representing a message queue topic/queue.

### R2: Publish/subscribe edge relations (MUST)

The WorkflowGraph MUST support `publishes` and `subscribes` as valid edge relations:
- `publishes`: service → topic (producer)
- `subscribes`: topic → service (consumer)

### R3: Configuration-based MQ detection (MUST)

`ServiceParser` MUST scan for MQ configuration patterns:
- Kafka: `kafka` section in docker-compose, `application.yml` with `spring.kafka.consumer.group-id`
- RabbitMQ: `rabbitmq` service in docker-compose, `*.json` with queue declarations
- Generic: Environment variables like `*_QUEUE_URL`, `*_TOPIC_ARN` in docker-compose

### R4: Source code pattern scanning (SHOULD)

`ServiceParser` SHOULD scan source code for common MQ patterns:
- Python: `producer.send()`, `consumer.subscribe()`, `@app.task` (Celery)
- Node: `channel.publish()`, `channel.consume()`
- Go: `kafka.NewProducer`, `kafka.NewConsumer`
- Java: `@KafkaListener`, `KafkaTemplate.send()`

### R5: Impact traversal through topics (MUST)

`reverse_reach()` MUST traverse through topic nodes: changing a producer → affects the topic → affects all consumers.

## Acceptance Criteria

### AC1: Topic nodes created from docker-compose (R1, R3)

- **Given** a `docker-compose.yml` with a `kafka` or `rabbitmq` service and environment vars referencing topic names
- **When** calling `ServiceParser().parse(root)`
- **Then** the graph contains `topic` nodes for detected queue/topic names

### AC2: Publish/subscribe edges (R2, R3)

- **Given** a service `order-service` that publishes to topic `order-events` and `notification-service` subscribes
- **When** parsing the project
- **Then** edges exist: `order-service --publishes--> order-events`, `order-events --subscribes--> notification-service`

### AC3: Impact through MQ (R5)

- **Given** a graph with `order-service` → `order-events` → `notification-service`
- **When** calling `reverse_reach("order-service")`
- **Then** the result includes `order-events` and `notification-service`

### AC4: Source code producer detection (R4)

- **Given** a Python file containing `producer.send('order-events', ...)`
- **When** scanning source code for MQ patterns
- **Then** a `publishes` edge is created from the owning service to `order-events`

## Target Call Chain

```
ServiceParser.parse(root)
  → _parse_docker_compose(root, graph)      # existing (STORY-slim-042)
  → _parse_openapi(root, graph)             # existing (STORY-slim-042)
  → _parse_proto_files(root, graph)         # existing (STORY-slim-042)
  → _parse_mq_config(root, graph)           # NEW — docker-compose env vars, config files
  → _scan_mq_source_patterns(root, graph)   # NEW — source code pattern matching
  → return graph
```

## Implementation Steps

| Step | File | Action | Dependencies | Risk |
|------|------|--------|-------------|------|
| 1 | `tests/unit/test_story_slim044.py` | TDD: tests for MQ config and source pattern detection | STORY-slim-042 | Low |
| 2 | `src/pactkit/skills/visualize.py` | Implement `_parse_mq_config()` | STORY-slim-042 | Medium |
| 3 | `src/pactkit/skills/visualize.py` | Implement `_scan_mq_source_patterns()` | STORY-slim-042 | High |
| 4 | `src/pactkit/skills/visualize.py` | Integrate MQ parsing into ServiceParser.parse() | Steps 2-3 | Low |

## Security Scope

| Check | Applicable | Reason |
|-------|------------|--------|
| SEC-1 Input validation | Medium | Scans source code with regex — no eval/exec |
| SEC-2 through SEC-7 | N/A | No auth, crypto, injection, or network changes |
| SEC-8 Dependencies | N/A | No new dependencies |

## Out of Scope

- Runtime MQ tracing (production monitoring)
- Dead letter queue analysis
- Topic schema validation (Avro/Protobuf schema registry)
- Message flow rate or throughput analysis
