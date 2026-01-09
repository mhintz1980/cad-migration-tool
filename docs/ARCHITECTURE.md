# CAD Migration Tool - Architecture Documentation

## System Overview

The CAD Migration Tool is a modular, layered architecture designed for scalability, maintainability, and testability.

## Architecture Layers

### 1. Core Layer (src/core/)

**Responsibility:** Low-level CAD file operations

**Components:**
- **Parsers** - Read and parse CAD files into structured data
- **Transformers** - Apply transformations to CAD entities
- **Validators** - Validate drawings against standards

**Key Design Decisions:**
- Parsers return immutable `ParsedDrawing` dataclasses
- Transformers are stateless and composable
- Validators follow visitor pattern for extensibility

### 2. Data Layer (src/data/)

**Responsibility:** Data persistence and domain models

**Components:**
- **Models** - Domain entities (Standards, Migrations, FileRecords)
- **Repositories** - Data access abstraction using Repository pattern
- **Database** - SQLite connection management with WAL mode

**Key Design Decisions:**
- Generic Repository[T] pattern for type safety
- SQLite WAL mode for concurrent access and crash safety
- Dataclasses for immutable domain models

### 3. Orchestration Layer (src/orchestration/)

**Responsibility:** Batch processing and workflow coordination

**Components:**
- **BatchProcessor** - Main orchestrator
- **Worker** - Process pool worker function
- **StateManager** - Migration state tracking
- **RollbackManager** - Backup and restore
- **ProgressReporter** - User feedback

**Key Design Decisions:**
- ProcessPoolExecutor for CPU-bound parallelism
- Checkpoint-based crash recovery
- Functional worker design for multiprocessing compatibility

### 4. Integration Layer (src/integration/)

**Responsibility:** External system integrations

**Components:**
- **Learning System** - Standards learning from samples
- **PDM Integration** - Vault operations

**Key Design Decisions:**
- Plugin architecture for learners
- Abstract client interface for PDM
- Mock implementations for development

### 5. CLI Layer (src/cli/)

**Responsibility:** User interaction

**Components:**
- **Main** - CLI entry point
- **Command Groups** - migrate, learn, pdm, validate

**Key Design Decisions:**
- Click framework for robust CLI
- Rich library for beautiful output
- Command groups for organization

## Data Flow

### Migration Flow

```
Input Files
    ↓
[DXFParser] → ParsedDrawing
    ↓
[PreMigrationValidator] → ValidationResult
    ↓
[Transformers] → ParsedDrawing (modified)
    ↓
[PostMigrationValidator] → ValidationResult
    ↓
[Writer] → Output Files
```

### Batch Processing Flow

```
CLI Command
    ↓
[BatchProcessor.process_batch()]
    ↓
[StateManager.initialize()] → Create migration record
    ↓
[ProcessPoolExecutor] → Spawn workers
    ↓
[Worker.process_file()] × N (parallel)
    ↓
[StateManager.checkpoint()] (periodic)
    ↓
[ProgressReporter] → Live updates
    ↓
Results
```

### Learning Flow

```
Sample Files (old + new)
    ↓
[DXFParser] → ParsedDrawings
    ↓
[Learners] → Extract observations
    ↓
[ConfidenceScorer] → Calculate confidence
    ↓
[LearningEngine] → Merge rules
    ↓
StandardConfig → YAML export
```

## Design Patterns

### Repository Pattern
- Abstracts data access
- Enables testing with in-memory repositories
- Type-safe with generics

### Strategy Pattern
- Transformers are strategies
- Learners are strategies
- PDM clients are strategies

### Factory Pattern
- PDMClientFactory auto-detects platform
- Creates appropriate client implementation

### Observer Pattern
- ProgressReporter observes BatchProcessor
- Live updates without tight coupling

### State Machine Pattern
- Migration status transitions (PENDING → RUNNING → COMPLETED/FAILED)
- Enforces valid state transitions

## Concurrency Model

### ProcessPoolExecutor
- Used for CPU-bound CAD file processing
- Number of workers = CPU count (configurable)
- Avoids GIL limitations

### SQLite WAL Mode
- Write-Ahead Logging for concurrent access
- Multiple readers, single writer
- Checkpoint-based persistence

### Crash Recovery
- Periodic checkpoints (every N files)
- Resume from last checkpoint
- Idempotent operations

## Error Handling Strategy

### Validation Errors
- Collected, not raised
- Returned in ValidationResult
- User decides to proceed or abort

### Processing Errors
- Caught at worker level
- Recorded in database
- Batch continues with remaining files

### Fatal Errors
- Database corruption → detected via integrity checks
- Out of disk space → caught early
- Invalid configuration → fail fast at startup

## Testing Strategy

### Unit Tests
- Core parsers and transformers
- Validators
- Repositories (with in-memory database)

### Integration Tests
- Batch processor with real files
- PDM mock client
- CLI commands

### Manual Testing
- CLI help output
- Error messages
- Progress bars

## Performance Considerations

### Bottlenecks
1. **DXF parsing** - CPU-bound, addressed with parallelism
2. **File I/O** - Minimized with streaming where possible
3. **Database writes** - Batched with checkpoints

### Optimizations
1. **Parallel processing** - ProcessPoolExecutor
2. **SQLite WAL** - Concurrent reads
3. **Checkpoint intervals** - Configurable trade-off
4. **Progress updates** - Throttled to avoid overhead

## Security Considerations

### File Operations
- Path validation to prevent directory traversal
- Backup files isolated in dedicated directory

### Database
- Parameterized queries (SQLAlchemy)
- No user-supplied SQL

### PDM Integration
- Credentials not stored in code
- Mock client for development (no real credentials needed)

## Extensibility Points

### Adding New File Formats
1. Implement `BaseParser` interface
2. Register in parser factory
3. Add format-specific tests

### Adding New Transformers
1. Create transformer class
2. Add to transformation pipeline
3. Update standards config schema

### Adding New Learners
1. Implement `BaseLearner` interface
2. Add to `LearningEngine`
3. Update confidence scoring if needed

### Adding New PDM Systems
1. Implement `PDMClient` interface
2. Add to `PDMClientFactory`
3. Add platform detection logic

## Future Architecture Improvements

### Phase 3 Candidates
- Logging framework (structured logging)
- Monitoring/metrics (Prometheus-compatible)
- Plugin system for custom transformers
- Web UI for monitoring
- Docker containerization
- REST API for remote execution

### Scalability Improvements
- Distributed processing (Celery/RabbitMQ)
- Cloud storage integration (S3/Azure Blob)
- Horizontal scaling with task queue
- Load balancing across multiple machines
