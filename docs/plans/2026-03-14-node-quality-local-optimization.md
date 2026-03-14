# Node Quality Local Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete local optimization pipeline on top of the current NoMoreWalls fetch flow so the repo can acquire nodes, preserve provenance, benchmark node quality locally, filter/rank candidates, and emit optimized local subscription artifacts without breaking the current public-generation path.

**Architecture:** Keep [fetch.py](E:/github/NoMoreWalls/fetch.py) as the acquisition and public artifact generator. Add a new local optimization layer that consumes a structured node snapshot exported from `fetch.py`, performs passive scoring plus active local benchmarking through a temporary Mihomo instance, caches results, and writes optimized outputs to a separate local artifact directory. Do not overwrite the existing root `list*` outputs until the optimized path proves stable.

**Tech Stack:** Python 3.8+, PyYAML, requests, pytest, local Mihomo executable with external-controller API, JSONL/CSV/Markdown artifacts, PowerShell and WSL helper scripts.

---

## Repository Context

- Current source ingress lives in [sources.list](E:/github/NoMoreWalls/sources.list) and [dynamic.py](E:/github/NoMoreWalls/dynamic.py).
- Current parse, merge, de-dup, adblock merge, and artifact generation all live inside [fetch.py](E:/github/NoMoreWalls/fetch.py).
- Current public outputs are root `list.txt`, `list_raw.txt`, `list.yml`, `list.meta.yml`, `list_result.csv`, and `snippets/*.yml`.
- Current provenance is partial: `used[hash][sourceId] = n.name` in [fetch.py](E:/github/NoMoreWalls/fetch.py), but it is not persisted as a reusable local quality dataset.
- Current repo has no test suite, no structured intermediate snapshot, no local active benchmark runner, no score cache, no ranked output path, and no operator report for why one node beat another.

## Target End State

- `python fetch.py` still works and still produces the current public outputs.
- `python optimize_local.py` reads a structured snapshot from the latest fetch run and produces local-only optimized outputs.
- Local optimization is configurable through `local_quality.yml`, not by hard-coding weights into `fetch.py`.
- The optimizer can run in three modes:
  - `snapshot-only`
  - `passive-score-only`
  - `full-probe`
- Optimized outputs land in `artifacts/local/` and never silently replace public outputs.
- Every filtered-out node has a machine-readable reason.
- Active probing is cached and resumable.

## File Map To Introduce

- Create: `quality/__init__.py`
- Create: `quality/models.py`
- Create: `quality/config.py`
- Create: `quality/provenance.py`
- Create: `quality/passive_score.py`
- Create: `quality/mihomo_config.py`
- Create: `quality/probe_runner.py`
- Create: `quality/cache.py`
- Create: `quality/ranking.py`
- Create: `quality/output_writer.py`
- Create: `quality/reporting.py`
- Create: `optimize_local.py`
- Create: `local_quality.yml`
- Create: `scripts/run-fetch-local.ps1`
- Create: `scripts/run-optimize-local.ps1`
- Create: `scripts/run-optimize-local.sh`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/sample_snapshot.jsonl`
- Create: `tests/fixtures/sample_probe_results.json`
- Create: `tests/test_snapshot_export.py`
- Create: `tests/test_passive_score.py`
- Create: `tests/test_probe_cache.py`
- Create: `tests/test_output_writer.py`
- Create: `tests/test_optimize_local_cli.py`
- Create: `docs/local-optimization.md`
- Modify: `fetch.py`
- Modify: `requirements.txt`
- Modify: `README.md`

## Task 1: Establish the Local Optimization Contract

**Files:**
- Create: `quality/__init__.py`
- Create: `quality/models.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/sample_snapshot.jsonl`
- Create: `tests/test_snapshot_export.py`
- Modify: `requirements.txt`

**Step 1: Write the failing snapshot contract test**

Write `tests/test_snapshot_export.py` with assertions for:
- a `NodeSnapshot` record
- a `NodeProvenance` record
- a stable `node_hash`
- fields for `protocol`, `server`, `port`, `name`, `source_ids`, `source_names`, `raw_name`, `merged_at`

Example assertion:

```python
def test_snapshot_record_has_required_fields(sample_snapshot_record):
    assert sample_snapshot_record.node_hash
    assert sample_snapshot_record.protocol in {"vmess", "vless", "trojan", "ss", "ssr", "hysteria2"}
    assert isinstance(sample_snapshot_record.source_ids, list)
    assert sample_snapshot_record.port > 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_snapshot_export.py -q`

Expected: FAIL with `ModuleNotFoundError` for `quality.models` or missing contract objects.

**Step 3: Add the minimal model layer**

Implement `quality/models.py` with dataclasses or `TypedDict` models for:
- `NodeSnapshot`
- `NodeProvenance`
- `PassiveScore`
- `ProbeResult`
- `RankedNode`

Do not add scoring logic yet. Keep it to schema, parsing helpers, and serialization helpers.

**Step 4: Add test tooling**

Append `pytest` to [requirements.txt](E:/github/NoMoreWalls/requirements.txt).

Run: `pip install -r requirements.txt`

Expected: pytest becomes available in the repo environment.

**Step 5: Run the contract test again**

Run: `python -m pytest tests/test_snapshot_export.py -q`

Expected: PASS.

**Step 6: Commit**

```bash
git add requirements.txt quality/__init__.py quality/models.py tests/
git commit -m "test: add node snapshot contract"
```

## Task 2: Export a Structured Snapshot From the Existing Fetch Pipeline

**Files:**
- Create: `quality/provenance.py`
- Modify: `fetch.py`
- Test: `tests/test_snapshot_export.py`

**Step 1: Write the failing fetch snapshot export test**

Add a test that exercises a tiny merged dataset and asserts that `fetch.py` can emit:
- `artifacts/quality/node_snapshot.jsonl`
- `artifacts/quality/source_summary.csv`
- `artifacts/quality/unknown_nodes.txt`

Example assertion:

```python
def test_fetch_exports_quality_snapshot(tmp_path, monkeypatch):
    export_paths = run_export(tmp_path)
    assert export_paths.snapshot.exists()
    assert export_paths.source_summary.exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_snapshot_export.py -q`

Expected: FAIL because no export function exists yet.

**Step 3: Implement structured export without changing public outputs**

Modify [fetch.py](E:/github/NoMoreWalls/fetch.py) so that after merge and before writing final subscription files it also writes:
- `artifacts/quality/node_snapshot.jsonl`
- `artifacts/quality/source_summary.csv`
- `artifacts/quality/merge_stats.json`
- `artifacts/quality/unknown_nodes.txt`

Snapshot fields must include:
- stable `node_hash`
- merged node payload
- normalized name
- raw protocol
- source ids and source names
- whether the node supports Clash
- whether the node supports Meta
- whether the node supports Ray

**Step 4: Keep provenance tied to existing merge state**

Reuse the existing `used` map in [fetch.py](E:/github/NoMoreWalls/fetch.py) instead of inventing a second provenance mechanism.

**Step 5: Run the export test again**

Run: `python -m pytest tests/test_snapshot_export.py -q`

Expected: PASS.

**Step 6: Smoke-check the script**

Run: `python -m py_compile fetch.py dynamic.py optimize_local.py`

Expected: PASS for the existing scripts and placeholder CLI if present.

**Step 7: Commit**

```bash
git add fetch.py quality/provenance.py tests/test_snapshot_export.py
git commit -m "feat: export structured node snapshot"
```

## Task 3: Add Local Quality Configuration and Passive Scoring

**Files:**
- Create: `local_quality.yml`
- Create: `quality/config.py`
- Create: `quality/passive_score.py`
- Create: `tests/test_passive_score.py`
- Modify: `README.md`

**Step 1: Write the failing passive score test**

Create tests for scoring rules such as:
- prefer `hysteria2`, `tuic`, `vless-reality` over weaker candidates
- penalize fake-looking names and broken metadata
- reward multi-source provenance
- reward category confidence from `NoMoreWalls.categories`
- cap one source from dominating the shortlist

Example assertion:

```python
def test_multi_source_hysteria2_scores_higher_than_single_source_ss():
    assert score(hy2_candidate) > score(ss_candidate)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_passive_score.py -q`

Expected: FAIL because no scorer exists yet.

**Step 3: Add `local_quality.yml`**

Define explicit knobs for:
- protocol weights
- region quotas
- minimum source diversity
- banned keywords
- preferred categories
- candidate shortlist limits
- probe URLs
- timeouts
- cache TTLs

Keep this file local-optimizer-specific. Do not overload [config.yml](E:/github/NoMoreWalls/config.yml) with probe weights.

**Step 4: Implement passive scoring**

Implement `quality/passive_score.py` to compute a score breakdown with:
- protocol score
- provenance score
- metadata quality score
- category confidence score
- fake-risk penalty
- duplicate-conflict penalty

The output must preserve a per-factor breakdown so later reports can explain rankings.

**Step 5: Reuse existing repo knowledge**

Read categories from [config.yml](E:/github/NoMoreWalls/config.yml) `NoMoreWalls.categories` when useful, but keep optimizer-specific thresholds in `local_quality.yml`.

**Step 6: Run tests**

Run: `python -m pytest tests/test_passive_score.py -q`

Expected: PASS.

**Step 7: Commit**

```bash
git add local_quality.yml quality/config.py quality/passive_score.py tests/test_passive_score.py README.md
git commit -m "feat: add passive node quality scoring"
```

## Task 4: Build a Temporary Mihomo Config Generator for Active Probing

**Files:**
- Create: `quality/mihomo_config.py`
- Create: `tests/test_optimize_local_cli.py`
- Modify: `snippets/example.yml`

**Step 1: Write the failing temp-config generation test**

Create a test asserting the generated config:
- injects shortlisted proxies
- creates stable proxy groups
- exposes external-controller on a configurable local port
- uses probe URLs from `local_quality.yml`

Example assertion:

```python
def test_build_probe_config_includes_shortlisted_candidates():
    config = build_probe_config(sample_ranked_nodes, probe_settings)
    assert config["proxies"]
    assert any(group["name"] == "QUALITY-PROBE" for group in config["proxy-groups"])
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimize_local_cli.py -q`

Expected: FAIL because no probe config builder exists yet.

**Step 3: Implement the temp config builder**

Use the existing output structure from [snippets/example.yml](E:/github/NoMoreWalls/snippets/example.yml) as the base, then inject:
- candidate proxies
- probe-only proxy groups
- local-only external controller
- deterministic ports

The builder must never mutate the committed template file in place.

**Step 4: Run test again**

Run: `python -m pytest tests/test_optimize_local_cli.py -q`

Expected: PASS for config generation.

**Step 5: Commit**

```bash
git add quality/mihomo_config.py tests/test_optimize_local_cli.py snippets/example.yml
git commit -m "feat: add temporary mihomo probe config builder"
```

## Task 5: Add the Active Probe Runner and Failure Classification

**Files:**
- Create: `quality/probe_runner.py`
- Modify: `optimize_local.py`
- Create: `tests/test_probe_cache.py`

**Step 1: Write the failing probe runner test**

Create tests for:
- Mihomo process launch command generation
- external-controller delay API parsing
- timeout mapping
- failure classification into `connect_failed`, `tls_failed`, `timeout`, `auth_failed`, `empty_result`

Example assertion:

```python
def test_parse_delay_response_marks_success():
    result = parse_delay_response({"delay": 183})
    assert result.ok is True
    assert result.latency_ms == 183
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_cache.py -q`

Expected: FAIL because the runner does not exist yet.

**Step 3: Implement `quality/probe_runner.py`**

The runner must:
- create a temporary Mihomo config
- start Mihomo in a subprocess
- wait for controller health
- query `/proxies/<name>/delay`
- tear down cleanly even on exceptions

Do not hard-code a single path to Mihomo. Resolve from:
- CLI flag
- `local_quality.yml`
- environment variable

**Step 4: Implement passive-only fallback**

If Mihomo is unavailable, `optimize_local.py` must support a passive-only mode instead of crashing.

**Step 5: Run probe tests**

Run: `python -m pytest tests/test_probe_cache.py -q`

Expected: PASS.

**Step 6: Commit**

```bash
git add quality/probe_runner.py optimize_local.py tests/test_probe_cache.py
git commit -m "feat: add active mihomo probe runner"
```

## Task 6: Add Probe Cache, Resume Support, and Network Profile Awareness

**Files:**
- Create: `quality/cache.py`
- Modify: `quality/probe_runner.py`
- Modify: `optimize_local.py`
- Test: `tests/test_probe_cache.py`

**Step 1: Write the failing cache behavior tests**

Cover:
- cache hit by `node_hash`
- cache bust when probe URL set changes
- cache bust when network profile changes
- stale reuse in report-only mode
- resume after partial probe interruption

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_cache.py -q`

Expected: FAIL for cache behaviors.

**Step 3: Implement cache layout**

Use:
- `cache/local_quality/probe_cache.json`
- `cache/local_quality/session_state.json`
- `artifacts/quality/probe_history.jsonl`

Cache key should include:
- `node_hash`
- probe target URL list hash
- timeout profile
- local network profile hash
- mihomo version

**Step 4: Add resume semantics**

If the process stops midway, the next run should continue from unprobed nodes unless `--clear-cache` is set.

**Step 5: Run tests**

Run: `python -m pytest tests/test_probe_cache.py -q`

Expected: PASS.

**Step 6: Commit**

```bash
git add quality/cache.py quality/probe_runner.py optimize_local.py tests/test_probe_cache.py
git commit -m "feat: add resumable probe cache"
```

## Task 7: Build Ranking, Diversity Control, and Local Optimized Output Writers

**Files:**
- Create: `quality/ranking.py`
- Create: `quality/output_writer.py`
- Create: `tests/test_output_writer.py`
- Modify: `optimize_local.py`

**Step 1: Write the failing ranking/output tests**

Test that the final pipeline:
- combines passive score and active probe score
- enforces per-region caps
- enforces source diversity
- drops repeated low-quality clones
- writes optimized outputs without touching root `list*`

Example assertion:

```python
def test_write_local_outputs_keeps_root_outputs_untouched(tmp_path):
    outputs = write_local_outputs(tmp_path, ranked_nodes)
    assert outputs.local_meta.exists()
    assert not (tmp_path / "list.meta.yml").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_output_writer.py -q`

Expected: FAIL because the ranking/output layer does not exist yet.

**Step 3: Implement ranking**

Combine:
- passive score
- active latency
- success rate
- region diversity bonus
- source diversity bonus
- instability penalty

Keep the final ranking formula in one place only: `quality/ranking.py`.

**Step 4: Implement output writers**

Write:
- `artifacts/local/list.local.txt`
- `artifacts/local/list.local.yml`
- `artifacts/local/list.local.meta.yml`
- `artifacts/local/snippets/nodes.local.yml`
- `artifacts/local/snippets/nodes.local.meta.yml`
- `artifacts/quality/ranking.csv`

Do not overwrite the public root `list.txt`, `list.yml`, `list.meta.yml`.

**Step 5: Run output tests**

Run: `python -m pytest tests/test_output_writer.py -q`

Expected: PASS.

**Step 6: Commit**

```bash
git add quality/ranking.py quality/output_writer.py optimize_local.py tests/test_output_writer.py
git commit -m "feat: write optimized local node outputs"
```

## Task 8: Add Operator CLI, Reports, and End-to-End Workflow Scripts

**Files:**
- Create: `quality/reporting.py`
- Create: `scripts/run-fetch-local.ps1`
- Create: `scripts/run-optimize-local.ps1`
- Create: `scripts/run-optimize-local.sh`
- Create: `docs/local-optimization.md`
- Modify: `README.md`
- Modify: `optimize_local.py`

**Step 1: Write the failing CLI/report test**

Create tests asserting the CLI supports:
- `--snapshot-only`
- `--passive-only`
- `--full-probe`
- `--mihomo-path`
- `--reuse-cache`
- `--clear-cache`
- `--report-only`

Example assertion:

```python
def test_cli_report_only_uses_existing_artifacts(tmp_path):
    result = run_cli(["--report-only", "--artifacts-dir", str(tmp_path)])
    assert result.exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimize_local_cli.py -q`

Expected: FAIL because the CLI is incomplete.

**Step 3: Implement operator reports**

Generate:
- `artifacts/quality/summary.md`
- `artifacts/quality/top_nodes.csv`
- `artifacts/quality/filter_reasons.csv`
- `artifacts/quality/source_reputation.csv`

Every filtered node must carry a reason code and a human-readable reason.

**Step 4: Add scripts for Windows and WSL**

Create:
- `scripts/run-fetch-local.ps1`
- `scripts/run-optimize-local.ps1`
- `scripts/run-optimize-local.sh`

Each script must:
- use repo-relative paths safely
- create output directories if missing
- print the final artifact paths

**Step 5: Document the workflow**

Update [README.md](E:/github/NoMoreWalls/README.md) and add `docs/local-optimization.md` with:
- prerequisite installation
- Mihomo path setup
- recommended command order
- cache directory meanings
- how to inspect failed probes

**Step 6: Run the end-to-end tests**

Run:
- `python -m pytest tests -q`
- `python -m py_compile fetch.py dynamic.py optimize_local.py`

Expected: PASS.

**Step 7: Do a manual smoke run**

Run:

```bash
python fetch.py
python optimize_local.py --passive-only
python optimize_local.py --full-probe --reuse-cache
```

Expected:
- snapshot artifacts appear under `artifacts/quality/`
- local optimized outputs appear under `artifacts/local/`
- public root `list*` files are still generated by `fetch.py`

**Step 8: Commit**

```bash
git add quality/ optimize_local.py scripts/ docs/ README.md tests/
git commit -m "feat: add local node quality optimization pipeline"
```

## Acceptance Criteria

- `python fetch.py` remains backward-compatible for the current repo use case.
- A structured node snapshot is emitted on every fetch run.
- Local optimization can run without mutating public output files.
- Passive-only mode works without Mihomo installed.
- Full-probe mode works with Mihomo installed and configured.
- Probe cache is resumable and keyed by network profile.
- Reports explain every score and every filter decision.
- Tests cover snapshot export, passive scoring, probe cache, output writing, and CLI behavior.

## Recommended Implementation Order

1. Contract and fixtures
2. Snapshot export
3. Passive scoring
4. Mihomo temp config builder
5. Active probe runner
6. Cache and resume
7. Ranking and local outputs
8. CLI, docs, scripts, smoke run

## Commands the Engineer Should Use Constantly

```bash
python -m pytest tests/test_snapshot_export.py -q
python -m pytest tests/test_passive_score.py -q
python -m pytest tests/test_probe_cache.py -q
python -m pytest tests/test_output_writer.py -q
python -m pytest tests/test_optimize_local_cli.py -q
python -m pytest tests -q
python -m py_compile fetch.py dynamic.py optimize_local.py
python fetch.py
python optimize_local.py --passive-only
python optimize_local.py --full-probe --reuse-cache
```

## Non-Goals for the First Iteration

- Do not replace public root `list*` outputs with optimized local outputs.
- Do not rewrite [sources.list](E:/github/NoMoreWalls/sources.list) source strategy in the same branch.
- Do not move the entire repo into a package refactor before the optimizer works.
- Do not build cross-machine distributed probing in v1.
- Do not add database infrastructure in v1; JSONL/CSV/cache files are enough.
