# !depende

`!depende` is a small dependency-maintenance and deployment concept for people who keep many projects on one machine and need a repeatable way to answer four questions:

- Which projects declare dependencies?
- Which dependency sets are locked and reproducible?
- Which direct dependencies are outdated?
- Which projects can be tested, built, and optionally deployed in a controlled way?

The repository version is intentionally anonymized. It contains public-safe documentation, public-safe example configuration, and two heavily commented educational Python scripts.

## Why This Exists

The work started from a practical maintenance problem: keeping dozens of local projects healthy without manually checking every `package.json`, `composer.json`, lockfile, test command, and production deployment path every day.

The resulting concept is a simple operator toolkit:

1. Inventory dependency manifests.
2. Produce a human-readable dependency report.
3. Record project-level test/build/deploy commands in a JSON config.
4. Keep deployment disabled by default.
5. Require explicit confirmation before real execution or deployment.

## What It Gives the User

- A single place to reason about dependency maintenance.
- A documented difference between manifests, lockfiles, runtime dependencies, and dev dependencies.
- A repeatable pipeline for install/update, test, build, and optional deploy.
- A safe default mode: dry-run.
- A clear split between public educational files and private operational files.
- Line-by-line educational versions of the script in English and Polish.

## Public Files

These files are safe to keep in a public repository:

| File | Purpose |
| --- | --- |
| `README.md` | GitHub-rendered overview and usage documentation. |
| `prot_maintenance_anon_commented_en.py` | Public-safe English version with line-by-line explanations. |
| `prot_maintenance_anon_commented_pl.py` | Public-safe Polish version with line-by-line explanations. |
| `prot-maintenance.anonymized.example.json` | Public-safe example configuration with fake host, user, and paths. |
| `dependency_report_generator.py` | Public-safe generator for human-readable dependency reports in English or Polish. |

## Private Operational Files

The following file types should stay private unless they are fully sanitized:

| File type | Why it should stay private |
| --- | --- |
| Real maintenance config | May contain local paths, production paths, project names, or server layout. |
| Dependency inventory reports | May reveal private project names and stack details. |
| Outdated caches | May reveal package choices and project structure. |
| Remote path validation output | May reveal production directory layout. |
| Real deployment script | May contain environment-specific assumptions. |

## How The Concept Evolved

### 1. Workspace inventory

The first step was to scan the workspace for dependency manifests such as:

- `package.json`
- `composer.json`
- `requirements.txt`
- `pyproject.toml`
- lockfiles such as `package-lock.json` and `composer.lock`

That inventory made it possible to see which directories were real projects and which were generated artifacts, vendored code, virtual environments, or caches.

### 2. Human-readable dependency report

The raw JSON inventory was not useful enough for a human operator. It was converted into an HTML report that explained:

- what the numbers mean,
- what a manifest is,
- what a lockfile is,
- which projects have lockfiles,
- which direct dependencies are outdated,
- which results are missing because of timeouts or unsupported tooling.

### 3. Maintenance orchestrator

The Python script was then introduced to make the process repeatable:

1. Install locked dependencies, or update dependencies when explicitly requested.
2. Run configured tests.
3. Run configured builds.
4. Optionally deploy with `rsync` over SSH.
5. Optionally run remote post-deploy commands.

### 4. Report generator module

A separate public-safe generator was added for the human-readable dependency report. It reads an inventory JSON and an optional outdated-cache JSON, then renders a standalone HTML report in English or Polish.

### 5. Remote path mapping

The private operational version can map local projects to remote production paths. In the private workflow, this was done by inspecting remote directories and application metadata such as environment names and application URLs.

The public version does not include real paths or server details.

### 6. Educational anonymized versions

The final public-safe versions were created for documentation and teaching:

- English version: `prot_maintenance_anon_commented_en.py`
- Polish version: `prot_maintenance_anon_commented_pl.py`

Both are intentionally verbose and explain the code line by line.

## Configuration Model

The configuration file has two main sections:

```json
{
  "ssh": {
    "host": "deploy.example.com",
    "port": 22,
    "user": "deploy_user",
    "identity_file": "~/.ssh/id_ed25519"
  },
  "projects": []
}
```

### SSH Fields

| Field | Meaning |
| --- | --- |
| `host` | Remote SSH host. |
| `port` | Remote SSH port. |
| `user` | SSH username. |
| `identity_file` | Optional private key path. |

### Project Fields

| Field | Meaning |
| --- | --- |
| `name` | Stable project name used in logs and `--only`. |
| `path` | Local project directory. |
| `enabled` | Whether the script may process this project. |
| `deploy` | Whether the project may be deployed when `--deploy` is passed. |
| `remote_path` | Remote destination directory. |
| `test_commands` | Commands that must pass before build/deploy. |
| `build_commands` | Commands run after tests. |
| `remote_commands` | Commands run on the server after upload. |
| `excludes` | Extra `rsync` exclude patterns. |

## Safety Model

The script intentionally requires multiple explicit choices before it can change production.

### Default: dry-run

Running the script without `--execute` prints commands but does not run them.

```bash
python3 prot_maintenance_anon_commented_en.py --config maintenance.config.json
```

### Real local execution

To actually install dependencies, run tests, and run builds:

```bash
python3 prot_maintenance_anon_commented_en.py --execute --config maintenance.config.json
```

### Dependency updates

To update dependency versions:

```bash
python3 prot_maintenance_anon_commented_en.py --execute --apply-updates --config maintenance.config.json
```

### Deployment

Deployment requires both a global flag and a per-project flag:

```bash
python3 prot_maintenance_anon_commented_en.py --execute --deploy --config maintenance.config.json
```

The project must also have:

```json
{
  "deploy": true
}
```

This double switch prevents accidental upload.

## Build From Scratch

### 1. Create a starter config

```bash
python3 prot_maintenance_anon_commented_en.py \
  --init-config \
  --root /workspace \
  --config maintenance.config.json
```

### 2. Edit the config

Set at least:

- `ssh.host`
- `ssh.port`
- `ssh.user`
- `path`
- `remote_path`
- `enabled`
- `test_commands`
- `build_commands`
- `remote_commands`
- `excludes`

Keep `deploy` set to `false` until the remote path has been manually verified.

### 3. Run a dry-run

```bash
python3 prot_maintenance_anon_commented_en.py --config maintenance.config.json
```

### 4. Run tests/builds for one project

```bash
python3 prot_maintenance_anon_commented_en.py \
  --execute \
  --only example-backend \
  --config maintenance.config.json
```

### 5. Run updates only after reviewing the plan

```bash
python3 prot_maintenance_anon_commented_en.py \
  --execute \
  --apply-updates \
  --only example-backend \
  --config maintenance.config.json
```

### 6. Deploy only after remote path verification

```bash
python3 prot_maintenance_anon_commented_en.py \
  --execute \
  --deploy \
  --only example-backend \
  --config maintenance.config.json
```

## Generate A Human-Readable Dependency Report

`dependency_report_generator.py` turns dependency inventory data into a standalone HTML report. It supports English and Polish output.

### Input files

The generator expects:

- an inventory JSON with a top-level `rows` list,
- optionally, an outdated-cache JSON keyed by `project/path::npm` or `project/path::composer`.

### English report

```bash
python3 dependency_report_generator.py \
  --inventory dependency-inventory.json \
  --outdated-cache dependency-outdated-cache.json \
  --output dependency-report-en.html \
  --lang en
```

### Polish report

```bash
python3 dependency_report_generator.py \
  --inventory dependency-inventory.json \
  --outdated-cache dependency-outdated-cache.json \
  --output dependency-report-pl.html \
  --lang pl
```

### Without outdated cache

```bash
python3 dependency_report_generator.py \
  --inventory dependency-inventory.json \
  --output dependency-report.html \
  --lang en
```

When no outdated cache is provided, the report still explains manifests, lockfiles and dependency counts, but marks outdated data as unavailable.

## Important Risks

### `rsync --delete`

The deploy command uses `rsync --delete`. This is useful for clean deployment, but dangerous if `remote_path` points to the wrong directory.

Before enabling deployment:

1. Confirm the remote path manually over SSH.
2. Run the script without `--execute`.
3. Run one project at a time with `--only`.
4. Enable `deploy=true` only for the verified project.

### Dependency updates

`composer update` and `npm update` can modify lockfiles. Treat dependency updates as code changes:

- review diffs,
- run tests,
- read major-version changelogs,
- deploy gradually.

### Python dependencies

The example script supports basic Python detection, but does not implement a full Python lockfile workflow. For serious Python services, add a lockfile-aware workflow such as `pip-tools`, `uv`, or Poetry.

## Recommended Repository Contents

For a public repository, keep only:

```text
README.md
dependency_report_generator.py
prot_maintenance_anon_commented_en.py
prot_maintenance_anon_commented_pl.py
prot-maintenance.anonymized.example.json
```

For a private operational repository, you may additionally keep:

```text
maintenance.config.json
dependency inventory reports
outdated caches
remote path validation reports
```

Only do that if the repository is private and does not contain secrets.

## Pre-Deploy Checklist

Use this checklist before enabling deployment for any real project:

- [ ] `remote_path` exists.
- [ ] `remote_path` was checked manually over SSH.
- [ ] `deploy` is still `false` during initial dry-run.
- [ ] dry-run output looks correct.
- [ ] tests pass for the target project.
- [ ] build passes for the target project.
- [ ] `.env`, logs, caches, and local-only files are excluded.
- [ ] `deploy=true` is enabled only for the verified project.
- [ ] deployment is run with `--only project-name`.

## Prompt History

This concept was built iteratively from the following user requests:

1. `prot dependencies`
2. `"How do you practically maintain these 50 projects? Do you check dependencies, updates, and package vulnerabilities in all of them every day?" Can you globally check dependency state in all subdirectories?`
3. `Process this JSON into some HTML with descriptions. I do not know what these numbers mean. I need context and outdated status.`
4. `Increase the scan limit to 600s and process the ones that did not finish last time.`
5. `Write a Python script that updates all packages, uploads them to production in the right place, and runs all tests in project directories.`
6. `Inspect the remote host and try to establish remote paths. I am counting on you. Set all of them to enabled.`
7. `Create an anonymized version, but with deeper comments. What every function, definition, and variable does.`
8. `Too few comments. Add them line by line. What exactly this code does. Preferably with links to documentation.`
9. `Add a comment for every line. Not every important line. For complete beginners.`
10. `Translate all existing comments to English in ...en.py and Polish in ...pl.py. Clean up indentation and duplicate/similar Polish-English comments, based on prot_maintenance_anon_commented.py.`
11. `Do these two new Python files pass syntax tests?`
12. `Create a dedicated !depende directory and move all these py, json and html files there.`
13. `Create a readme.html explaining how we got to this concept, what it gives the user, what must be changed and where, how to build it, and add the prompts I used. I need a beautiful description and all repository information.`
14. `GitHub shows the HTML code instead of nicely formatted text. How to fix it?`
15. `Do option 2, but in English. Commit README.md and remove readme.html from the repository.`
16. `Can we create a separate Python file that generates these human-readable dependency reports in Polish or English? Update README.md because this is an interesting new module.`

## Documentation Links

- Python `argparse`: https://docs.python.org/3/library/argparse.html
- Python `dataclasses`: https://docs.python.org/3/library/dataclasses.html
- Python `pathlib`: https://docs.python.org/3/library/pathlib.html
- Python `json`: https://docs.python.org/3/library/json.html
- Python `subprocess.run`: https://docs.python.org/3/library/subprocess.html#subprocess.run
- npm `ci`: https://docs.npmjs.com/cli/v10/commands/npm-ci
- npm `update`: https://docs.npmjs.com/cli/v10/commands/npm-update
- Composer `install`: https://getcomposer.org/doc/03-cli.md#install-i
- Composer `update`: https://getcomposer.org/doc/03-cli.md#update-u
- rsync manual: https://download.samba.org/pub/rsync/rsync.1
- OpenSSH client manual: https://man.openbsd.org/ssh
