# Phase 2 Architectural Decisions

**Date:** 2026-01-09
**Author:** Opus 4.5 Architecture Review
**Status:** Approved for Implementation

---

## Executive Summary

After reviewing the Phase 1 foundation (1,173 lines across 10 files), I recommend the following architectural decisions for the 4 critical systems:

| System | Decision | Rationale |
|--------|----------|-----------|
| Standards Learning | **Rule-based extraction** with confidence scoring | CAD is structured data, not ML problem |
| Batch Orchestration | **ProcessPoolExecutor + SQLite state** | CPU-bound parsing, crash recovery |
| PDM Integration | **Interface abstraction, Mock-first** | Cross-platform dev, production COM |
| Persistence | **Hybrid: YAML configs + SQLite state** | Human-editable configs, queryable history |

---

## Decision 1: Standards Learning System

### Recommendation: Rule-Based Extraction with Statistical Confidence

**NOT ML-based pattern detection.** Here's why:

#### Why Rule-Based (Not ML)

1. **CAD files are structured data** - Layers, dimensions, and blocks have deterministic properties. This is not a fuzzy pattern recognition problem.

2. **Explainability requirement** - Users must understand WHY a layer was mapped. "The model predicted this" is unacceptable for engineering standards.

3. **Limited training data** - You'll have 10-50 sample pairs, not thousands. ML needs volume; rule extraction works with small samples.

4. **Auditable output** - The generated `StandardConfig` must be reviewable and editable by CAD administrators.

5. **Deterministic results** - Same inputs must always produce same outputs. ML introduces variance.

#### Architecture

```
src/integration/learning/
├── __init__.py
├── base_learner.py          # Abstract interface
├── layer_learner.py          # Layer mapping extraction
├── dimension_learner.py      # Dimension style extraction
├── title_block_learner.py    # Title block field mapping
├── confidence.py             # Statistical confidence calculation
├── learning_engine.py        # Orchestrates all learners
└── models.py                 # LearnedRule, LearningResult dataclasses
```

#### Core Algorithm

```python
@dataclass
class LearnedRule:
    """Single learned mapping rule."""
    rule_type: str  # "layer_mapping", "dimension_style", "property_mapping"
    source_pattern: str  # What to match in old file
    target_value: Any  # What to produce in new file
    confidence: float  # 0.0-1.0 based on sample agreement
    sample_count: int  # How many samples contributed
    exceptions: List[str]  # Samples that disagreed

class LearningEngine:
    """Orchestrates standards learning from sample pairs."""

    def learn(self,
              old_samples: List[Path],
              new_samples: List[Path],
              min_confidence: float = 0.8) -> StandardConfig:
        """
        Compare old/new sample pairs and extract mapping rules.

        Algorithm:
        1. Parse all old samples → extract layers, dims, title blocks
        2. Parse all new samples → extract same
        3. For each old layer, find corresponding new layer by:
           - Entity content similarity (same entities, different layer name)
           - Positional correspondence (title block in same location)
           - Attribute tag matching (PART_NUMBER → Part Number)
        4. Calculate confidence = (agreeing_samples / total_samples)
        5. Filter rules below min_confidence threshold
        6. Generate StandardConfig with learned mappings
        """
```

#### Confidence Scoring

```python
def calculate_confidence(observations: List[Observation]) -> float:
    """
    Calculate confidence score for a learned rule.

    Formula: confidence = (majority_count / total_count) * consistency_factor

    Where consistency_factor penalizes contradictory mappings:
    - All samples agree: 1.0
    - 90% agree: 0.95
    - 80% agree: 0.85
    - <70% agree: Rule rejected
    """
    if not observations:
        return 0.0

    # Count how many samples support each mapping
    mapping_counts = Counter(obs.target_value for obs in observations)
    majority_count = mapping_counts.most_common(1)[0][1]
    total_count = len(observations)

    agreement_ratio = majority_count / total_count

    # Penalize disagreement
    if agreement_ratio < 0.7:
        return 0.0  # Too much disagreement, reject rule

    consistency_factor = 0.5 + (agreement_ratio * 0.5)
    return agreement_ratio * consistency_factor
```

#### Layer Mapping Detection

```python
class LayerLearner:
    """Extracts layer mapping rules from sample pairs."""

    def learn_layer_mappings(self,
                              old_drawing: ParsedDrawing,
                              new_drawing: ParsedDrawing) -> List[LearnedRule]:
        """
        Detect layer mappings by entity correspondence.

        Strategy:
        1. Build entity fingerprints for each layer (entity types, positions)
        2. Match old layers to new layers by fingerprint similarity
        3. Extract the name mapping (old_name → new_name)
        4. Also extract property changes (color, line_type, line_weight)
        """
        old_fingerprints = self._build_layer_fingerprints(old_drawing)
        new_fingerprints = self._build_layer_fingerprints(new_drawing)

        mappings = []
        for old_layer, old_fp in old_fingerprints.items():
            best_match = self._find_best_match(old_fp, new_fingerprints)
            if best_match and best_match.similarity > 0.8:
                mappings.append(LearnedRule(
                    rule_type="layer_mapping",
                    source_pattern=old_layer,
                    target_value=best_match.layer_name,
                    confidence=best_match.similarity,
                    sample_count=1,
                    exceptions=[]
                ))
        return mappings

    def _build_layer_fingerprints(self, drawing: ParsedDrawing) -> Dict[str, LayerFingerprint]:
        """Create fingerprint of each layer's entity content."""
        fingerprints = {}
        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])
            fingerprints[layer_name] = LayerFingerprint(
                entity_types=Counter(e.dxftype() for e in entities),
                entity_count=len(entities),
                bounding_box=self._calculate_bounds(entities),
                has_text=any(e.dxftype() in ("TEXT", "MTEXT") for e in entities),
                has_dimensions=any(e.dxftype().startswith("DIM") for e in entities),
            )
        return fingerprints
```

#### Sample Requirements

| Requirement | Value | Rationale |
|-------------|-------|-----------|
| Minimum samples | 3 pairs | Statistical significance for confidence |
| Recommended | 5-10 pairs | Better confidence, edge case coverage |
| Maximum useful | ~20 pairs | Diminishing returns beyond this |

#### Output Format

The learning engine outputs a complete `StandardConfig` (already defined in Phase 1) with:
- `layer_mapping`: Dict of old → new layer names
- `layer_standards`: Target layer properties learned from new samples
- `dimension_standards`: Extracted dimension styles
- `property_mappings`: Title block field mappings

Plus a `LearningReport` for human review:
```yaml
learning_report:
  generated_at: "2026-01-09T12:00:00"
  sample_pairs_analyzed: 8
  rules_generated: 24
  rules_rejected: 3
  average_confidence: 0.92

  layer_mappings:
    - old: "0"
      new: "CONSTRUCTION"
      confidence: 1.0
      samples_agreed: 8/8

    - old: "DIMS"
      new: "DIMENSIONS"
      confidence: 0.875
      samples_agreed: 7/8
      exception_files: ["sample_5_old.dxf"]

  warnings:
    - "Layer 'LEGACY-NOTES' not found in any new sample"
    - "3 rules rejected due to low confidence (<0.7)"
```

#### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Rule-based** (chosen) | Explainable, auditable, works with few samples, deterministic | Requires structured comparison logic |
| ML/Pattern detection | Could find subtle patterns | Black box, needs lots of data, overkill |
| Manual mapping only | Simple | Defeats automation purpose |

---

## Decision 2: Batch Orchestration

### Recommendation: ProcessPoolExecutor + SQLite State Machine

**Key insight:** CAD file parsing with ezdxf is CPU-bound (pure Python parsing). We need true parallelism via processes, not threads.

#### Architecture

```
src/orchestration/
├── __init__.py
├── batch_processor.py       # Main orchestration logic
├── worker.py                 # Single-file processing function
├── state_machine.py          # SQLite-backed state management
├── checkpoint.py             # Progress checkpointing
├── rollback.py               # Backup and restore logic
├── progress.py               # Progress reporting (Rich console)
└── models.py                 # BatchConfig, WorkerResult dataclasses
```

#### Parallel Processing Strategy

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterator
import os

@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_workers: int = None  # None = os.cpu_count()
    chunk_size: int = 10     # Files per progress update
    continue_on_error: bool = True
    max_failures: int = 50   # Stop batch if exceeded
    checkpoint_interval: int = 10  # Persist state every N files

class BatchProcessor:
    """Orchestrates parallel file processing."""

    def __init__(self,
                 config: BatchConfig,
                 state_manager: StateManager,
                 progress_callback: Callable = None):
        self.config = config
        self.state = state_manager
        self.progress = progress_callback

    def process_batch(self,
                      files: List[Path],
                      processor: Callable[[Path], WorkerResult]) -> BatchResult:
        """
        Process files in parallel with checkpointing.

        Flow:
        1. Initialize batch in SQLite state
        2. Filter already-completed files (resume support)
        3. Submit to ProcessPoolExecutor
        4. Collect results, update state, checkpoint
        5. Return aggregate BatchResult
        """
        # Resume support: skip already-processed files
        pending_files = self.state.get_pending_files(files)

        if not pending_files:
            return self.state.get_batch_result()

        max_workers = self.config.max_workers or os.cpu_count()
        failure_count = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files
            future_to_file = {
                executor.submit(processor, f): f
                for f in pending_files
            }

            # Process as completed (not in order)
            for i, future in enumerate(as_completed(future_to_file)):
                file_path = future_to_file[future]

                try:
                    result = future.result(timeout=300)  # 5 min per file
                    self.state.record_success(file_path, result)
                except Exception as e:
                    failure_count += 1
                    self.state.record_failure(file_path, str(e))

                    if failure_count >= self.config.max_failures:
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise BatchAbortedError(f"Too many failures: {failure_count}")

                # Checkpoint periodically
                if (i + 1) % self.config.checkpoint_interval == 0:
                    self.state.checkpoint()

                # Progress callback
                if self.progress:
                    self.progress(completed=i+1, total=len(pending_files))

        self.state.finalize()
        return self.state.get_batch_result()
```

#### State Management with SQLite

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

class StateManager:
    """SQLite-backed state management for crash recovery."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS migrations (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        profile TEXT,
        config JSON
    );

    CREATE TABLE IF NOT EXISTS migration_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_id TEXT REFERENCES migrations(id),
        file_path TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        backup_path TEXT,
        output_path TEXT,
        error TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        processing_time REAL,
        changes JSON,
        UNIQUE(migration_id, file_path)
    );

    CREATE INDEX IF NOT EXISTS idx_items_status ON migration_items(migration_id, status);
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._connection() as conn:
            conn.executescript(self.SCHEMA)

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_pending_files(self, files: List[Path]) -> List[Path]:
        """Return files not yet successfully processed."""
        with self._connection() as conn:
            completed = set(
                row["file_path"] for row in
                conn.execute(
                    "SELECT file_path FROM migration_items WHERE status = 'completed'"
                ).fetchall()
            )
        return [f for f in files if str(f) not in completed]

    def record_success(self, file_path: Path, result: WorkerResult):
        """Record successful file processing."""
        with self._connection() as conn:
            conn.execute("""
                UPDATE migration_items
                SET status = 'completed',
                    output_path = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    processing_time = ?,
                    changes = ?
                WHERE file_path = ?
            """, (str(result.output_path), result.processing_time,
                  json.dumps(result.changes), str(file_path)))

    def checkpoint(self):
        """Force WAL checkpoint for durability."""
        with self._connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
```

#### Rollback Strategy

```python
import shutil
from datetime import datetime

class RollbackManager:
    """Manages file backups and rollback operations."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path, migration_id: str) -> Path:
        """
        Create full copy backup before modification.

        Strategy: Full file copy (not diff-based)
        Rationale:
        - CAD files are binary/semi-binary, diffs not practical
        - Storage is cheap, reliability is critical
        - Simple restore: just copy back
        """
        backup_subdir = self.backup_dir / migration_id
        backup_subdir.mkdir(parents=True, exist_ok=True)

        # Preserve directory structure in backup
        relative_path = file_path.name
        backup_path = backup_subdir / f"{relative_path}.bak"

        shutil.copy2(file_path, backup_path)  # Preserves metadata
        return backup_path

    def rollback_file(self, backup_path: Path, original_path: Path):
        """Restore single file from backup."""
        if not backup_path.exists():
            raise RollbackError(f"Backup not found: {backup_path}")
        shutil.copy2(backup_path, original_path)

    def rollback_migration(self, migration_id: str, state: StateManager):
        """Rollback entire migration."""
        items = state.get_migration_items(migration_id)

        for item in items:
            if item.backup_path and item.status == 'completed':
                self.rollback_file(Path(item.backup_path), Path(item.file_path))
                state.update_status(item.id, 'rolled_back')

    def cleanup_old_backups(self, max_age_days: int = 30):
        """Remove backups older than max_age_days."""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.stat().st_mtime < cutoff:
                shutil.rmtree(backup_dir)
```

#### Error Recovery Strategy

| Scenario | Behavior |
|----------|----------|
| Single file parse error | Log error, continue batch, mark file as failed |
| Transformation error | Rollback that file's backup, continue batch |
| Worker crash | Re-submit file (ProcessPoolExecutor handles this) |
| Batch abort (too many failures) | Checkpoint current state, rollback all completed |
| Process kill (Ctrl+C) | SQLite WAL survives, resume on restart |
| System crash | Resume from last checkpoint on restart |

#### Progress Reporting

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console

class ProgressReporter:
    """Rich-based progress reporting."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def create_progress(self, total: int) -> Progress:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TextColumn("[dim]{task.fields[rate]:.1f} files/sec[/dim]"),
            console=self.console,
        )
```

#### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **ProcessPoolExecutor** (chosen) | True parallelism, clean API, good error handling | IPC overhead, can't share state |
| multiprocessing.Pool | Lower-level control | Messier API, same overhead |
| asyncio | Good for I/O-bound | ezdxf is CPU-bound, no benefit |
| Threading | Simpler | GIL blocks CPU-bound work |

---

## Decision 3: PDM Integration

### Recommendation: Interface Abstraction with Mock-First Development

**Key insight:** We need to develop on Linux/Mac but deploy on Windows with SolidWorks PDM. Abstract the interface, implement mock first.

#### Architecture

```
src/integration/pdm/
├── __init__.py
├── base_client.py           # Abstract PDMClient interface
├── mock_client.py            # File-system based mock
├── com_client.py             # Windows COM interface (production)
├── models.py                 # PDMFile, CheckInResult, etc.
├── property_handler.py       # Custom property CRUD
└── vault_config.py           # Vault connection settings
```

#### Abstract Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

class PDMFileState(Enum):
    """File state in PDM vault."""
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CHECKED_OUT_BY_OTHER = "checked_out_by_other"
    NOT_IN_VAULT = "not_in_vault"

@dataclass
class PDMFile:
    """Represents a file in the PDM vault."""
    path: Path
    vault_path: str  # Path within vault
    state: PDMFileState
    version: int
    checked_out_by: Optional[str] = None
    custom_properties: Dict[str, str] = None

@dataclass
class CheckInResult:
    """Result of a check-in operation."""
    success: bool
    new_version: int
    error: Optional[str] = None

class PDMClient(ABC):
    """Abstract interface for PDM operations."""

    @abstractmethod
    def connect(self, vault_name: str, **kwargs) -> bool:
        """Connect to PDM vault."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from vault."""
        pass

    @abstractmethod
    def get_file_state(self, vault_path: str) -> PDMFile:
        """Get current state of a file."""
        pass

    @abstractmethod
    def checkout(self, vault_path: str, local_path: Path) -> bool:
        """Check out file for editing."""
        pass

    @abstractmethod
    def checkin(self,
                local_path: Path,
                vault_path: str,
                comment: str = "") -> CheckInResult:
        """Check in modified file."""
        pass

    @abstractmethod
    def add_file(self,
                 local_path: Path,
                 vault_folder: str,
                 comment: str = "") -> CheckInResult:
        """Add new file to vault."""
        pass

    @abstractmethod
    def get_custom_properties(self, vault_path: str) -> Dict[str, str]:
        """Get custom properties (data card values)."""
        pass

    @abstractmethod
    def set_custom_properties(self,
                               vault_path: str,
                               properties: Dict[str, str]) -> bool:
        """Set custom properties."""
        pass

    @abstractmethod
    def undo_checkout(self, vault_path: str) -> bool:
        """Undo checkout, discarding changes."""
        pass
```

#### Mock Implementation (Development)

```python
import json
from pathlib import Path
from datetime import datetime
import shutil

class MockPDMClient(PDMClient):
    """
    File-system based mock for development and testing.

    Simulates PDM vault using local directory structure:
    .mock_vault/
    ├── files/              # Actual files
    ├── metadata/           # JSON metadata per file
    ├── versions/           # Version history
    └── checkouts.json      # Current checkout state
    """

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.files_dir = vault_root / "files"
        self.metadata_dir = vault_root / "metadata"
        self.versions_dir = vault_root / "versions"
        self.checkouts_file = vault_root / "checkouts.json"
        self._connected = False

    def connect(self, vault_name: str, **kwargs) -> bool:
        """Initialize mock vault structure."""
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        if not self.checkouts_file.exists():
            self.checkouts_file.write_text("{}")

        self._connected = True
        return True

    def get_file_state(self, vault_path: str) -> PDMFile:
        """Check mock vault for file state."""
        file_path = self.files_dir / vault_path
        metadata_path = self.metadata_dir / f"{vault_path}.json"

        if not file_path.exists():
            return PDMFile(
                path=file_path,
                vault_path=vault_path,
                state=PDMFileState.NOT_IN_VAULT,
                version=0
            )

        metadata = json.loads(metadata_path.read_text())
        checkouts = json.loads(self.checkouts_file.read_text())

        if vault_path in checkouts:
            state = PDMFileState.CHECKED_OUT
            checked_out_by = checkouts[vault_path]["user"]
        else:
            state = PDMFileState.CHECKED_IN
            checked_out_by = None

        return PDMFile(
            path=file_path,
            vault_path=vault_path,
            state=state,
            version=metadata.get("version", 1),
            checked_out_by=checked_out_by,
            custom_properties=metadata.get("properties", {})
        )

    def checkout(self, vault_path: str, local_path: Path) -> bool:
        """Simulate checkout by copying file."""
        file_state = self.get_file_state(vault_path)

        if file_state.state == PDMFileState.NOT_IN_VAULT:
            raise PDMError(f"File not in vault: {vault_path}")

        if file_state.state == PDMFileState.CHECKED_OUT:
            raise PDMError(f"File already checked out by: {file_state.checked_out_by}")

        # Copy to local
        shutil.copy2(self.files_dir / vault_path, local_path)

        # Record checkout
        checkouts = json.loads(self.checkouts_file.read_text())
        checkouts[vault_path] = {
            "user": "mock_user",
            "local_path": str(local_path),
            "timestamp": datetime.now().isoformat()
        }
        self.checkouts_file.write_text(json.dumps(checkouts, indent=2))

        return True

    def checkin(self,
                local_path: Path,
                vault_path: str,
                comment: str = "") -> CheckInResult:
        """Simulate check-in with version increment."""
        metadata_path = self.metadata_dir / f"{vault_path}.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

        # Increment version
        old_version = metadata.get("version", 0)
        new_version = old_version + 1

        # Archive old version
        if old_version > 0:
            version_dir = self.versions_dir / vault_path
            version_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.files_dir / vault_path,
                        version_dir / f"v{old_version}")

        # Copy new file
        vault_file = self.files_dir / vault_path
        vault_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, vault_file)

        # Update metadata
        metadata["version"] = new_version
        metadata["last_modified"] = datetime.now().isoformat()
        metadata["comment"] = comment
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Clear checkout
        checkouts = json.loads(self.checkouts_file.read_text())
        checkouts.pop(vault_path, None)
        self.checkouts_file.write_text(json.dumps(checkouts, indent=2))

        return CheckInResult(success=True, new_version=new_version)

    def set_custom_properties(self,
                               vault_path: str,
                               properties: Dict[str, str]) -> bool:
        """Set properties in metadata JSON."""
        metadata_path = self.metadata_dir / f"{vault_path}.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

        metadata.setdefault("properties", {}).update(properties)
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return True
```

#### COM Implementation (Production)

```python
import sys
from pathlib import Path
from typing import Dict

# Only import on Windows
if sys.platform == "win32":
    import comtypes.client
    from comtypes.gen import EdmLib  # Generated from PDM type library

class COMPDMClient(PDMClient):
    """
    SolidWorks PDM COM interface for Windows production.

    Requires:
    - Windows OS
    - SolidWorks PDM client installed
    - PDM vault accessible
    """

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("COM PDM client only available on Windows")

        self._vault = None
        self._connected = False

    def connect(self, vault_name: str, **kwargs) -> bool:
        """Connect to PDM vault via COM."""
        try:
            # Create PDM vault interface
            vault_mgr = comtypes.client.CreateObject("ConisioLib.EdmVault")

            # Login (uses Windows credentials by default)
            vault_mgr.LoginAuto(vault_name, 0)

            self._vault = vault_mgr
            self._connected = True
            return True

        except Exception as e:
            raise PDMConnectionError(f"Failed to connect to vault '{vault_name}': {e}")

    def checkout(self, vault_path: str, local_path: Path) -> bool:
        """Check out file via COM API."""
        try:
            folder = self._vault.GetFolderFromPath(str(local_path.parent))
            file_obj = folder.GetFile(local_path.name)

            # Check out
            file_obj.LockFile(folder.ID, 0)  # 0 = current version

            # Get local copy
            file_obj.GetFileCopy(0, str(local_path))

            return True

        except Exception as e:
            raise PDMError(f"Checkout failed: {e}")

    def checkin(self,
                local_path: Path,
                vault_path: str,
                comment: str = "") -> CheckInResult:
        """Check in file via COM API."""
        try:
            folder = self._vault.GetFolderFromPath(str(local_path.parent))
            file_obj = folder.GetFile(local_path.name)

            # Check in
            file_obj.UnlockFile(0, comment)  # 0 = flags

            new_version = file_obj.CurrentVersion

            return CheckInResult(success=True, new_version=new_version)

        except Exception as e:
            return CheckInResult(success=False, new_version=0, error=str(e))

    def set_custom_properties(self,
                               vault_path: str,
                               properties: Dict[str, str]) -> bool:
        """Set data card variables via COM."""
        try:
            folder_path = str(Path(vault_path).parent)
            file_name = Path(vault_path).name

            folder = self._vault.GetFolderFromPath(folder_path)
            file_obj = folder.GetFile(file_name)

            # Get card variables interface
            var_mgr = self._vault.CreateUtility(17)  # EdmUtility.VariableMgr

            for prop_name, prop_value in properties.items():
                var_mgr.SetVar(file_obj.ID, prop_name, prop_value)

            return True

        except Exception as e:
            raise PDMError(f"Failed to set properties: {e}")
```

#### Factory Pattern

```python
import os

def create_pdm_client(mode: str = "auto") -> PDMClient:
    """
    Factory to create appropriate PDM client.

    Args:
        mode: "mock", "com", or "auto"
              - mock: Always use MockPDMClient
              - com: Always use COMPDMClient (Windows only)
              - auto: Use COM if on Windows with PDM, else mock
    """
    if mode == "mock":
        vault_path = Path(os.environ.get("MOCK_VAULT_PATH", ".mock_vault"))
        return MockPDMClient(vault_path)

    if mode == "com":
        return COMPDMClient()

    # Auto-detect
    if sys.platform == "win32":
        try:
            # Check if PDM is installed
            import comtypes.client
            comtypes.client.CreateObject("ConisioLib.EdmVault")
            return COMPDMClient()
        except:
            pass

    # Fall back to mock
    vault_path = Path(os.environ.get("MOCK_VAULT_PATH", ".mock_vault"))
    return MockPDMClient(vault_path)
```

#### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Mock-first** (chosen) | Cross-platform dev, testable, no PDM dependency | Must maintain parity with COM |
| COM-first | "Real" from start | Windows-only dev, slow iteration |
| REST wrapper | Modern, cross-platform | PDM doesn't have REST API natively |

---

## Decision 4: Persistence Strategy

### Recommendation: Hybrid - YAML for Configs, SQLite for State

**Key insight:** Different data has different characteristics. Configs should be human-editable and version-controllable. State should be queryable and crash-safe.

#### Architecture

```
src/data/repositories/
├── __init__.py
├── base_repository.py        # Abstract interface
├── standards_repository.py   # YAML-based standards storage
├── migration_repository.py   # SQLite-based migration history
├── config_repository.py      # YAML profile management
└── database.py               # SQLite connection management
```

#### Storage Separation

| Data Type | Storage | Format | Rationale |
|-----------|---------|--------|-----------|
| Standards configs | `config/standards/` | YAML | Human-editable, git-versioned |
| Migration profiles | `config/profiles/` | YAML | Human-editable, git-versioned |
| Migration history | `data/migrations.db` | SQLite | Queryable, ACID, crash-safe |
| Learned rules | `config/learned/` | YAML | Reviewable before use |
| Runtime state | `data/migrations.db` | SQLite | Resume support |

#### Abstract Repository Interface

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Abstract repository interface."""

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        """Retrieve by ID."""
        pass

    @abstractmethod
    def list(self, **filters) -> List[T]:
        """List with optional filters."""
        pass

    @abstractmethod
    def save(self, entity: T) -> None:
        """Create or update."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete by ID."""
        pass
```

#### Standards Repository (YAML)

```python
from pathlib import Path
from typing import List, Optional
import yaml

class StandardsRepository(Repository[StandardConfig]):
    """YAML-based standards configuration storage."""

    def __init__(self, standards_dir: Path):
        self.standards_dir = standards_dir
        self.standards_dir.mkdir(parents=True, exist_ok=True)

    def get(self, name: str) -> Optional[StandardConfig]:
        """Load standard config by name."""
        file_path = self.standards_dir / f"{name}.yaml"

        if not file_path.exists():
            return None

        return StandardConfig.load_from_file(file_path)

    def list(self, drawing_type: str = None) -> List[StandardConfig]:
        """List all standards, optionally filtered by type."""
        standards = []

        for file_path in self.standards_dir.glob("*.yaml"):
            config = StandardConfig.load_from_file(file_path)

            if drawing_type is None or config.drawing_type == drawing_type:
                standards.append(config)

        return standards

    def save(self, config: StandardConfig) -> None:
        """Save standard config to YAML."""
        file_path = self.standards_dir / f"{config.name}.yaml"
        config.save_to_file(file_path)

    def get_latest(self, drawing_type: str = "general") -> Optional[StandardConfig]:
        """Get the latest version of standards for a drawing type."""
        candidates = self.list(drawing_type=drawing_type)

        if not candidates:
            return None

        # Sort by version (semantic versioning)
        from packaging.version import Version
        candidates.sort(key=lambda c: Version(c.version), reverse=True)

        return candidates[0]
```

#### Migration Repository (SQLite)

```python
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

class MigrationRepository(Repository[Migration]):
    """SQLite-based migration history storage."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS migrations (
        id TEXT PRIMARY KEY,
        profile TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT NOT NULL,
        standards_version TEXT,
        config JSON,
        stats JSON
    );

    CREATE TABLE IF NOT EXISTS migration_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_id TEXT NOT NULL REFERENCES migrations(id) ON DELETE CASCADE,
        file_path TEXT NOT NULL,
        status TEXT NOT NULL,
        backup_path TEXT,
        output_path TEXT,
        error TEXT,
        warnings JSON,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        processing_time REAL,
        changes JSON
    );

    CREATE INDEX IF NOT EXISTS idx_migration_status ON migrations(status);
    CREATE INDEX IF NOT EXISTS idx_migration_date ON migrations(created_at);
    CREATE INDEX IF NOT EXISTS idx_item_migration ON migration_items(migration_id);
    CREATE INDEX IF NOT EXISTS idx_item_status ON migration_items(status);
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.SCHEMA)

    def get(self, migration_id: str) -> Optional[Migration]:
        """Load migration with all items."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                "SELECT * FROM migrations WHERE id = ?",
                (migration_id,)
            ).fetchone()

            if not row:
                return None

            items = conn.execute(
                "SELECT * FROM migration_items WHERE migration_id = ?",
                (migration_id,)
            ).fetchall()

            return self._row_to_migration(row, items)

    def list(self,
             status: str = None,
             profile: str = None,
             since: datetime = None,
             limit: int = 100) -> List[Migration]:
        """List migrations with filters."""
        query = "SELECT * FROM migrations WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if profile:
            query += " AND profile = ?"
            params.append(profile)

        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            migrations = []
            for row in rows:
                items = conn.execute(
                    "SELECT * FROM migration_items WHERE migration_id = ?",
                    (row["id"],)
                ).fetchall()
                migrations.append(self._row_to_migration(row, items))

            return migrations

    def save(self, migration: Migration) -> None:
        """Save migration and all items (upsert)."""
        with sqlite3.connect(self.db_path) as conn:
            # Upsert migration
            conn.execute("""
                INSERT OR REPLACE INTO migrations
                (id, profile, created_at, started_at, completed_at, status,
                 standards_version, config, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                migration.migration_id,
                migration.profile,
                migration.created_at.isoformat(),
                migration.started_at.isoformat() if migration.started_at else None,
                migration.completed_at.isoformat() if migration.completed_at else None,
                migration.status.value,
                migration.standards_version,
                json.dumps({"parallel_workers": migration.parallel_workers}),
                json.dumps({
                    "total": migration.total_files,
                    "successful": migration.successful_files,
                    "failed": migration.failed_files,
                    "skipped": migration.skipped_files,
                })
            ))

            # Upsert items
            for item in migration.items:
                conn.execute("""
                    INSERT OR REPLACE INTO migration_items
                    (migration_id, file_path, status, backup_path, output_path,
                     error, warnings, started_at, completed_at, processing_time, changes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    migration.migration_id,
                    str(item.file_path),
                    item.status.value,
                    str(item.backup_path) if item.backup_path else None,
                    str(item.output_path) if item.output_path else None,
                    item.error,
                    json.dumps(item.warnings),
                    item.started_at.isoformat() if item.started_at else None,
                    item.completed_at.isoformat() if item.completed_at else None,
                    item.processing_time,
                    json.dumps(item.changes),
                ))

    def get_stats(self,
                  since: datetime = None,
                  profile: str = None) -> Dict[str, Any]:
        """Get aggregate statistics."""
        query = """
            SELECT
                COUNT(*) as total_migrations,
                SUM(json_extract(stats, '$.total')) as total_files,
                SUM(json_extract(stats, '$.successful')) as successful_files,
                SUM(json_extract(stats, '$.failed')) as failed_files,
                AVG(json_extract(stats, '$.successful') * 100.0 /
                    NULLIF(json_extract(stats, '$.total'), 0)) as avg_success_rate
            FROM migrations
            WHERE status = 'completed'
        """
        params = []

        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())

        if profile:
            query += " AND profile = ?"
            params.append(profile)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, params).fetchone()

            return dict(row)
```

#### Configuration Example

```yaml
# config/standards/electrical_v2.yaml
name: electrical_v2
version: "2.0.0"
description: "Electrical drawing standards for 2026"
drawing_type: electrical

layer_standards:
  CONSTRUCTION:
    name: CONSTRUCTION
    color: 8
    line_type: CONTINUOUS
    line_weight: 13
    plot: false
    group: CONSTRUCTION

  DIMENSIONS:
    name: DIMENSIONS
    color: 3
    line_type: CONTINUOUS
    line_weight: 18
    plot: true
    group: ANNOTATION

layer_mapping:
  "0": "CONSTRUCTION"
  "DIMS": "DIMENSIONS"
  "DIM": "DIMENSIONS"
  "NOTES": "ANNOTATION"
  "TEXT": "ANNOTATION"

dimension_standards:
  default:
    arrow_size: 2.5
    text_height: 2.5
    text_offset: 1.0
    extension_line_offset: 1.5
    precision: 2
    units: mm
    layer: DIMENSIONS

title_block_standard:
  required_fields:
    - drawing_number
    - revision
    - title
    - date
    - author
  date_format: "%Y-%m-%d"
  revision_format: "^[A-Z]\\d{3}$"

property_mappings:
  PartNumber:
    property_name: PartNumber
    source: title_block
    source_key: drawing_number
    data_type: string
    required: true

  Revision:
    property_name: Revision
    source: title_block
    source_key: revision
    data_type: string
    required: true
```

#### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Hybrid YAML+SQLite** (chosen) | Best of both: editable configs, queryable state | Two storage systems |
| All SQLite | Single system, fully queryable | Configs not human-editable |
| All JSON/YAML | Simple, portable | No ACID, poor query support |
| Full ORM (SQLAlchemy) | Powerful | Overkill, heavyweight dependency |

---

## Implementation Priorities

Based on these architectural decisions, here's the recommended implementation order:

### Phase 2A: Core Infrastructure (Week 1-2)
1. **Persistence layer** (`src/data/repositories/`)
   - Database setup
   - Standards repository
   - Migration repository

2. **Transformation pipeline** (`src/core/transformers/`)
   - Layer transformer
   - Dimension transformer
   - Entity mapper

### Phase 2B: Processing Engine (Week 2-3)
3. **Validation system** (`src/core/validators/`)
   - Pre-migration validators
   - Post-migration validators

4. **Batch orchestration** (`src/orchestration/`)
   - Parallel processor
   - State machine
   - Rollback manager

### Phase 2C: Integration (Week 3-4)
5. **Standards learning** (`src/integration/learning/`)
   - Layer learner
   - Learning engine

6. **PDM integration** (`src/integration/pdm/`)
   - Mock client
   - Abstract interface

### Phase 2D: User Interface (Week 4)
7. **CLI commands** (`src/cli/`)
   - migrate command
   - validate command
   - learn command
   - rollback command

---

## Summary

| Decision | Choice | Key Rationale |
|----------|--------|---------------|
| Standards Learning | Rule-based extraction | CAD is structured data, need explainability |
| Batch Orchestration | ProcessPoolExecutor + SQLite | CPU-bound work, crash recovery |
| PDM Integration | Mock-first with interface | Cross-platform dev, testable |
| Persistence | YAML configs + SQLite state | Editable configs, queryable history |

These decisions prioritize:
1. **Reliability** - Crash recovery, rollback support
2. **Testability** - Mock implementations, abstract interfaces
3. **Maintainability** - Clean separation, standard patterns
4. **Practicality** - Works with real constraints (cross-platform dev, no ML training data)
