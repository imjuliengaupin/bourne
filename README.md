<a name="readme-top"></a>

<div align="center">
  <a>
    <img src="./demo/images/logo.png" width="80" height="80">
  </a>

<h3 align="center">Bourne</h3>

[![CI/CD](https://github.com/imjuliengaupin/bourne/actions/workflows/devops.yml/badge.svg?branch=PROD)](https://github.com/imjuliengaupin/bourne/actions/workflows/devops.yml)
[![Coverage](https://coveralls.io/repos/github/imjuliengaupin/bourne/badge.svg?branch=PROD)](https://coveralls.io/github/imjuliengaupin/bourne?branch=PROD)

<a href="#demo">View Demo</a>
·
<a href="#cicd">View Docs</a>
·
<a href="#️architecture">View Architecture</a>

</div>

## :gear: Features

- [x] **Multi-agent orchestration**: Modular agents for data ingestion, validation, transformation, and storage.
- [x] **Extensible agent framework**: Easily add new agent types or transformation modes.
- [x] **Dynamic terminal dashboard**: Live workflow progress, color-coded statuses, and real-time logs.
- [x] **Live data preview**: Before/after record comparison with field-level change highlighting.
- [x] **Config-driven pipelines**: Easily customize workflows and connectors via external JSON files.
- [x] **Support for JSON and NDJSON**: Ingestion and output for both formats.
- [x] **Schema validation**: Input/output validation using Pydantic v2 (TypeAdapter.validate_python).
- [x] **Retry logic and dependency handling**: Automatic retries, dependency resolution, and stall detection.

<br />

_See [open issues](https://github.com/imjuliengaupin/bourne/issues) for a full list of proposed features and known issues._

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :repeat: <a name="ci-cd">CI/CD</a>

- [x] **Automated builds**: Push and pull requests trigger a [GitHub Actions](https://docs.github.com/en/actions/using-workflows) workflow
- [x] **Code linting**: Enforced with `pylint`
- [x] **Static type checking**: Enforced with `mypy`
- [x] **Unit testing**: Automated with `pytest`
- [x] **Code coverage**: Measured with `pytest-cov` and reported to [Coveralls](https://coveralls.io/)
- [x] **Documentation generation**: Automated with `pdoc3`

<br />

_See the latest [workflow runs and artifacts](https://github.com/imjuliengaupin/bourne/actions) for build status and reports._

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :building_construction: Architecture

[![Open in Eraser](https://img.shields.io/badge/Open%20in-Eraser-blue?logo=eraser&style=for-the-badge)](https://app.eraser.io/workspace/LDgZLTRhjaVsKpyiZU0B)

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :computer: Demo

Live rendering of agent workflow progress and logs in a terminal dashboard.
<img src="./demo/images/demo.gif" width="700">

<br/>

Live rendering of data before **and** after agent transformations are applied. Activates during any `DataTransformationAgent` workflow step, where transformations applied are highlighted in
<span style="color:#5fc98f"><b>green</b></span>).

Sample transformation exhibited: `lowercase_keys`

<img src="./demo/images/preview.png" width="700">

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>

## :pencil: <a name="license">License</a>

All rights reserved.

This source code is proprietary. Unauthorized copying, modification, distribution, or use is prohibited without explicit permission from the author.

<p align="right">
    (<a href="#readme-top">back to top</a>)
</p>
