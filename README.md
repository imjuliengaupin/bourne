<a name="readme-top"></a>

<div align="center">
  <a>
    <img src="./demo/images/logo.png" width="80" height="80">
  </a>

<h3 align="center">Bourne</h3>

<p>Enterprise-grade data pipeline orchestration for ETL workflows</p>

[![Build Status](https://img.shields.io/github/actions/workflow/status/imjuliengaupin/bourne/devops.yml?branch=PROD&style=for-the-badge&logo=github&label=CI/CD)](https://github.com/imjuliengaupin/bourne/actions/workflows/devops.yml)
[![Coverage](https://img.shields.io/coveralls/github/imjuliengaupin/bourne/PROD?style=for-the-badge&logo=coveralls&label=COVERAGE)](https://coveralls.io/github/imjuliengaupin/bourne?branch=PROD)
[![Artifacts](https://img.shields.io/badge/Actions-Artifacts-6c757d?style=for-the-badge&logo=github)](https://github.com/imjuliengaupin/bourne/actions/workflows/devops.yml?query=branch%3APROD)

<p align="center">
  <a href="#why-bourne">Why Bourne?</a> •
  <a href="#features">Features</a> •
  <a href="#use-cases">Use Cases</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#example-workflow-conceptual">Example Workflow</a> •
  <a href="#demo">Demo</a> •
  <a href="#quality-reliability">Quality & Reliability</a> •
  <a href="#license">License</a>
</p>

</div>

<br />

## <a name="why-bourne">Why Bourne?</a>

Modern data pipelines require flexibility, reliability, and visibility. Bourne delivers:

- **Modular agent architecture** - Build complex workflows from simple, reusable components
- **Real-time observability** - Live dashboard showing workflow progress, data transformations, and errors
- **Configuration-driven execution** - Define pipelines in JSON, no code changes needed
- **Enterprise-grade validation** - Multi-tier schema validation with automatic fallback strategies
- **Production-ready** - Comprehensive testing, retry logic, dependency resolution, and stall detection

<br />

## :gear: <a name="features">Features</a>

- [x] **Multi-agent orchestration**: Coordinate complex data workflows with automatic dependency resolution
- [x] **Extensible framework**: Add custom agents and transformation logic with minimal boilerplate
- [x] **Live terminal dashboard**: Real-time workflow progress visualization with color-coded statuses
- [x] **Field-level data preview**: Compare before/after transformations with highlighted changes
- [x] **JSON-first configuration**: Build entire pipelines with external JSON files—no code required
- [x] **Flexible data formats**: Native support for JSON and NDJSON ingestion and output
- [x] **Intelligent schema validation**: Pydantic v2-backed, multi-tier cascade that keeps validation succeeding across data variations
- [x] **Resilient execution**: Automatic retries, stall detection, and dependency handling
- [x] **Comprehensive test suite**: Full coverage with scenario-based end-to-end testing

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :bulb: <a name="use-cases">Use Cases</a>

**Data Integration & Normalization**

- Ingest data from multiple JSON sources
- Normalize key formats (camelCase → snake_case)
- Apply consistent schema validation
- Export unified, validated output

**ETL Pipeline Management**

- Complex multi-step workflows with task dependencies
- Schema transformation and validation at each stage
- Real-time monitoring of pipeline execution
- Automatic error recovery and retry logic

**Data Quality Assurance**

- Validate incoming data against strict schemas
- Identify and log transformation changes
- Track data lineage with automatic metadata
- Fail-fast strict mode for critical pipelines

**Custom Data Processing**

- Build domain-specific agents for specialized transformations
- Compose agents into production workflows
- Configuration-driven scaling across different data sources

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :rocket: <a name="quick-start">Quick Start</a>

### Prerequisites

- Python 3.13
- Git

### Installation

```bash
# Clone and install
git clone https://github.com/imjuliengaupin/bourne.git
cd bourne

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install core dependencies only
pip install -e .

# Run a sample workflow
python main.py \
  --workflow json/workflows/default/default.json \
  --connector json/connectors/default/single-record.json \
  --debug
```

**Command-line Arguments**

- `--workflow` (required): Point to any JSON workflow configuration
- `--connector` (required): Point to any JSON data connector configuration
- `--debug` (optional): Enable live terminal dashboard with progress visualization and real-time logging

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## 🏗️ <a name="how-it-works">How It Works</a>

### Architecture at a Glance

[![Open in Eraser](https://img.shields.io/badge/Open%20in-Eraser-blue?logo=eraser&style=for-the-badge)](https://app.eraser.io/workspace/LDgZLTRhjaVsKpyiZU0B)

<br />

Bourne orchestrates four core agents in configurable sequences:

| 🤖 Agent                    | 🎯 Purpose                                                   |
| --------------------------- | ------------------------------------------------------------ |
| **DataIngestionAgent**      | Reads JSON/NDJSON from files or APIs                         |
| **DataValidationAgent**     | Validates against expected schemas with intelligent fallback |
| **DataTransformationAgent** | Applies configurable key transformations and normalizations  |
| **DataStorageAgent**        | Persists processed data to files or external systems         |

Each agent is independent, reusable, and can be composed into complex workflows with automatic dependency resolution.

<br />

### Configuration-Driven Pipelines

Define your entire workflow in JSON—no Python code needed. Typical flow:

- **Ingest**: Pull JSON/NDJSON from a source connector
- **Validate**: Enforce schemas with automatic fallback (primary → fallback → manual)
- **Transform**: Apply key normalization modes and add lineage metadata
- **Save**: Persist processed data to the configured destination

Workflows automatically handle:

- Task dependency ordering
- Automatic retries on transient failures
- Stall detection and recovery
- Real-time progress tracking

<br />

### Transformations & Validation

Apply powerful transformations without writing code:

| 🛠️ Transformation  | 🎯 Use Case                                | 📊 Example                      |
| ------------------ | ------------------------------------------ | ------------------------------- |
| `lowercase_keys`   | Convert all keys to lowercase              | `FirstName` → `firstname`       |
| `uppercase_keys`   | Convert all keys to UPPERCASE              | `FirstName` → `FIRSTNAME`       |
| `snake_case_keys`  | Convert to Python/database friendly format | `FirstName` → `first_name`      |
| `camel_case_keys`  | Convert all keys to camelCase format       | `FirstName` → `firstName`       |
| `pascal_case_keys` | Convert all keys to PascalCase format      | `first_name` → `FirstName`      |
| `normalize_types`  | Coerce all values to string type           | `{"id": 123}` → `{"id": "123"}` |

Transformation metadata keys auto-match the selected transform mode; toggle inclusion with `include_transformation_metadata` (default: off).

Schema validation uses a cascading approach:

1. **Primary** - Full typed Pydantic validation
2. **Fallback** - Enhanced validation with type flexibility
3. **Manual** - String-normalized fallback for ambiguous data

This ensures your pipeline succeeds even with unexpected data variations.

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## 🧪 <a name="example-workflow-conceptual">Example Workflow (Conceptual)</a>

- **Source**: JSON/NDJSON ingested through a connector
- **Validate**: Schema-checked with graceful fallback to keep data flowing
- **Transform**: Key casing/normalization applied; transformation metadata added
- **Store**: Written to the configured output target
- **Observe**: Live dashboard shows task progress, retries, and data diffs

Note: Transformation automatically adds lineage metadata fields whose key casing matches the selected `transform_mode`.

<p align="right">
  (<a href="#readme-top">back to top</a>)
</p>

## 🎬 <a name="demo">Demo</a>

### Live Workflow Dashboard

Real-time visualization of agent execution, task dependencies, and data flow:

<!-- TODO: Update with new gif -->
<img src="./demo/images/demo.gif" width="700">

<br />

### Data Transformation Preview

See exactly what changed before and after transformations are applied. <span style="color:#6de896"><b>Highlighted</b></span> fields show which keys and values were modified:

<!-- TODO: Update with new image -->
<img src="./demo/images/preview.png" width="700">

Sample transformation exhibited: `lowercase_keys` with `include_transformation_metadata` fields enabled.

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## 💪🏼 <a name="quality-reliability">Quality & Reliability</a>

- **Comprehensive testing**: 21 end-to-end scenario tests + 12 unit tests validate all agents, connectors, and transformation modes
- **Continuous verification**: Automated CI/CD pipeline (GitHub Actions) with static type checking, linting, and coverage reporting (Coveralls)
- **Production-ready resilience**: Built-in retries, automatic dependency ordering, stall detection, and graceful validation fallback
- **Observable & maintainable**: Full-stack observability through live dashboard; clean, modular architecture for long-term maintenance

<p align="right">
  (<a href="#readme-top">back to top</a>)
</p>

## :pencil: <a name="license">License</a>

All rights reserved.

This source code is proprietary. Unauthorized copying, modification, distribution, or use is prohibited without explicit permission from the author.

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>
