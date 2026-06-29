#!/usr/bin/env python3
# the previous first line tells the system to use the Python 3 interpreter.
# this line opens or closes a multiline text description.
"""
this line is part of Python syntax and supports the surrounding lines.
Anonimized dependency maintenance and deployment orchestrator.

this line is part of Python syntax and supports the surrounding lines.
This is the shareable, commented version of the internal maintenance script.
this line is part of Python syntax and supports the surrounding lines.
It intentionally uses fake SSH credentials and generic paths.

High-level flow:
  1. Read a JSON config describing projects.
  2. For every enabled project, install or update dependencies.
  3. Run configured tests.
  4. Run configured builds.
  5. Optionally deploy with rsync over SSH.

Safety model:
  - Default mode is dry-run, so it prints commands but does not execute them.
  - Real execution requires --execute.
  this line assigns a value to a variable, saving the result under a name.
  - Real deployment additionally requires --deploy and per-project deploy=true.

Official documentation for the main building blocks:
  - argparse CLI parsing: https://docs.python.org/3/library/argparse.html
  - dataclasses: https://docs.python.org/3/library/dataclasses.html
  - pathlib paths: https://docs.python.org/3/library/pathlib.html
  - json module: https://docs.python.org/3/library/json.html
  - os.walk directory traversal: https://docs.python.org/3/library/os.html#os.walk
  - shlex.quote shell quoting: https://docs.python.org/3/library/shlex.html#shlex.quote
  - subprocess.run command execution: https://docs.python.org/3/library/subprocess.html#subprocess.run
  - Python type hints: https://docs.python.org/3/library/typing.html
  - npm ci: https://docs.npmjs.com/cli/v10/commands/npm-ci
  - npm update: https://docs.npmjs.com/cli/v10/commands/npm-update
  - Composer install: https://getcomposer.org/doc/03-cli.md#install-i
  - Composer update: https://getcomposer.org/doc/03-cli.md#update-u
  - rsync options: https://download.samba.org/pub/rsync/rsync.1
  - OpenSSH client: https://man.openbsd.org/ssh

Reading guide:
  - Comments beginning with "Why" explain the reason for a choice.
  - Comments beginning with "What" explain the direct effect of a line/block.
  - Comments beginning with "Risk" point out places that can change files or production.
this line opens or closes a multiline text description.
"""

# this line enables newer behavior for type annotations so type hints are easier to use.
from __future__ import annotations

# argparse parses command-line flags such as --config, --execute and --deploy.
# this line imports the argparse module, which provides ready-made Python library functions.
import argparse

# json reads/writes the configuration file.
# this line imports the json module, which provides ready-made Python library functions.
import json

# os.walk is used to scan a workspace for package manifests.
# this line imports the os module, which provides ready-made Python library functions.
import os

# shlex.quote safely formats shell fragments for display and SSH commands.
# this line imports the shlex module, which provides ready-made Python library functions.
import shlex

# subprocess runs external tools: npm, composer, pytest, ssh and rsync.
# this line imports the subprocess module, which provides ready-made Python library functions.
import subprocess

# sys gives access to stderr and argv for CLI error reporting.
# this line imports the sys module, which provides ready-made Python library functions.
import sys

# dataclass reduces boilerplate for the Project data container.
# this line imports selected items from a module so they can be used with shorter names.
from dataclasses import dataclass, field

# Path gives safer path handling than raw strings.
# this line imports selected items from a module so they can be used with shorter names.
from pathlib import Path

# Any is used for JSON dictionaries, where values can have mixed types.
# this line imports selected items from a module so they can be used with shorter names.
from typing import Any


# Fake SSH host used in the anonymized example. Replace in private config.
# this line defines a default value used when the config does not provide one.
DEFAULT_HOST = "deploy.example.com"

# Fake SSH port used in the anonymized example. Replace in private config.
# this line defines a default value used when the config does not provide one.
DEFAULT_PORT = 22

# Fake SSH login used in the anonymized example. Replace in private config.
# this line defines a default value used when the config does not provide one.
DEFAULT_USER = "deploy_user"

# Directory names skipped during workspace discovery.
# These are either generated dependencies, caches, system tooling, or platform
# folders that should not be treated as independent deployable projects.
# this line starts a set of directory names skipped during scanning.
PRUNE_DIRS = {
    # this line is an element of a larger list, dictionary, or multiline text.
    ".cache",
    # this line is an element of a larger list, dictionary, or multiline text.
    ".git",
    # this line is an element of a larger list, dictionary, or multiline text.
    ".npm",
    # this line is an element of a larger list, dictionary, or multiline text.
    ".venv",
    # this line is an element of a larger list, dictionary, or multiline text.
    "Android",
    # this line is an element of a larger list, dictionary, or multiline text.
    "android",
    # this line is an element of a larger list, dictionary, or multiline text.
    "ios",
    # this line is an element of a larger list, dictionary, or multiline text.
    "node_modules",
    # this line is an element of a larger list, dictionary, or multiline text.
    "vendor",
    # this line is an element of a larger list, dictionary, or multiline text.
    "venv",
# this line opens or closes a data structure or function call.
}


# this line tells Python to automatically create the constructor and field handling for the class.
@dataclass
# this line starts a class definition, a template for an object storing project data.
class Project:
    # this line starts a multiline description of the file or function.
    """One locally maintained project or package.

      Attributes:
              name: Human-readable identifier used in logs and --only filters.
              path: Local filesystem path to the project directory.
              remote_path: Remote deployment directory on the server.
              enabled: If false, the project is ignored by the runner.
              deploy: If true, this project may be uploaded when --deploy is passed.
              npm: True when package.json exists locally.
              composer: True when composer.json exists locally.
              python: True when requirements.txt or pyproject.toml exists locally.
              build_commands: Shell commands run after tests, usually asset builds.
              test_commands: Shell commands that must pass before build/deploy.
              remote_commands: Shell commands run on the server after rsync.
              excludes: Extra rsync exclude patterns for this project.
    this line opens or closes a multiline text description.
    """

        # What: short stable identifier printed in logs and accepted by --only.
    #     name: str
        # What: absolute or relative local directory containing the project.
    #     path: Path
        # What: destination directory on the remote server; None blocks deploy.
    #     remote_path: str | None = None
        # What: disabled projects are skipped before any command runs.
    #     enabled: bool = True
        # What: second safety switch; --deploy alone is not enough without this.
    #     deploy: bool = False
        # What: detected package.json flag, used to choose npm commands.
    #     npm: bool = False
        # What: detected composer.json flag, used to choose Composer commands.
    #     composer: bool = False
        # What: detected Python manifest flag, used to choose pytest/pip commands.
    #     python: bool = False
        # Why: default_factory avoids sharing one mutable list between projects.
    #     build_commands: list[str] = field(default_factory=list)
        # What: commands that must return exit code 0 before build/deploy.
    #     test_commands: list[str] = field(default_factory=list)
        # What: commands executed over SSH after rsync, for migrations/cache.
    #     remote_commands: list[str] = field(default_factory=list)
        # What: project-specific rsync exclude patterns.
    #     excludes: list[str] = field(default_factory=list)


# this line starts the load_json function, a named reusable block of code.
def load_json(path: Path) -> dict[str, Any]:
    # this line starts a multiline description of the file or function.
    """Read a JSON file and return it as a dictionary.

      path:
              Location of the config file.
    this line opens or closes a multiline text description.
    """

        # What: open the file as UTF-8 text so names with non-ASCII characters work.
    # this line opens a resource safely, usually a file here.
    with path.open("r", encoding="utf-8") as f:
                # What: parse JSON into Python dictionaries/lists/strings/numbers.
        # this line ends the function and returns the result to the caller.
        return json.load(f)


# this line starts the write_json function, a named reusable block of code.
def write_json(path: Path, data: dict[str, Any]) -> None:
    # this line starts a multiline description of the file or function.
    """Write a dictionary as pretty JSON.

    this line assigns a value to a variable, saving the result under a name.
    ensure_ascii=False keeps non-English project names readable.
    this line opens or closes a multiline text description.
    """

        # What: json.dumps serializes Python data back to JSON.
        # Why: indent=2 makes the config human-editable.
        # Why: ensure_ascii=False keeps readable Unicode instead of \uXXXX escapes.
    # this line writes text to a file on disk.
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# this line starts the run function, a named reusable block of code.
def run(cmd: list[str] | str, cwd: Path | None, dry_run: bool, timeout: int | None = None) -> int:
    # this line starts a multiline description of the file or function.
    """Print and optionally execute one command.

      cmd:
              Either a list of argv tokens, or a shell command string.
              A string is used only where shell syntax is intentionally needed.
      cwd:
              Working directory. None means current process directory.
      dry_run:
              If true, only print the command and report success.
      timeout:
              Maximum runtime in seconds. None means no explicit timeout.

      Return:
              Process exit code. 0 means success for Unix commands.
    this line opens or closes a multiline text description.
    """

        # What: command strings need the shell, because they may contain &&, pipes, env vars, etc.
    # this line checks a condition; the code below runs only if the condition is true.
    if isinstance(cmd, str):
                # Shell command strings are displayed as-is and run with shell=True.
        # this line prepares the text version of the command for terminal output.
        printable = cmd
                # Risk: shell=True executes shell syntax; only use trusted config commands.
        # this line decides whether the command should run through the system shell.
        shell = True
    # this line marks the fallback branch when the earlier condition was not met.
    else:
                # Lists are safely quoted for display and run without shell=True.
                # What: shlex.quote makes printed commands copy-paste safe for spaces/special chars.
        # this line prepares the text version of the command for terminal output.
        printable = " ".join(shlex.quote(x) for x in cmd)
                # Why: shell=False avoids shell interpretation for argv-style commands.
        # this line decides whether the command should run through the system shell.
        shell = False

        # What: prefix shows the working directory before the command.
    # this line prepares a working-directory prefix for readable logs.
    prefix = f"[{cwd}] " if cwd else ""
        # What: always print commands, even during real execution, for auditability.
    # this line prints information in the terminal for the person running the script.
    print(f"{prefix}$ {printable}")

        # What: dry-run stops before subprocess.run, pretending success.
    # this line checks a condition; the code below runs only if the condition is true.
    if dry_run:
        # this line ends the function and returns the result to the caller.
        return 0

        # What: subprocess.run waits until the command exits or timeout expires.
    # this line runs an external command and waits for it to finish.
    completed = subprocess.run(cmd, cwd=cwd, shell=shell, timeout=timeout)
        # What: callers use returncode to decide whether to raise an error.
    # this line ends the function and returns the result to the caller.
    return completed.returncode


# this line starts the detect_projects function, a named reusable block of code.
def detect_projects(root: Path) -> list[Project]:
    # this line starts a multiline description of the file or function.
    """Scan a workspace and discover directories with dependency manifests.

      root:
              Workspace root to scan.

      Detection rules:
              package.json -> npm project
              composer.json -> Composer/PHP project
              requirements.txt or pyproject.toml -> Python project
    this line opens or closes a multiline text description.
    """

        # What: accumulator for every directory that looks like a project.
    # this line creates an empty list with a type hint for readability.
    projects: list[Project] = []

        # What: os.walk yields each directory, its child directories, and file names.
    # this line starts a loop, repeating operations for subsequent items.
    for dirpath, dirnames, filenames in os.walk(root):
                # What: convert string path from os.walk into a pathlib.Path object.
        # this line converts a text path into a Path object and normalizes it.
        path = Path(dirpath)
                # What: compute path relative to root, so project names are stable/readable.
        # this line assigns a value to a variable, saving the result under a name.
        rel = path.relative_to(root) if path != root else Path(".")

                # If the current directory is already inside a pruned path, stop
                # descending further.
        # this line checks a condition; the code below runs only if the condition is true.
        if set(rel.parts) & PRUNE_DIRS:
            #             dirnames[:] = []
            # this line is part of Python syntax and supports the surrounding lines.
            continue

                # Remove pruned child directories before os.walk visits them.
        #         dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]

                # What: these booleans classify package managers by manifest files.
        # this line sets True/False depending on whether the given manifest was detected.
        npm = "package.json" in filenames
        # this line sets True/False depending on whether the given manifest was detected.
        composer = "composer.json" in filenames
        # this line sets True/False depending on whether the given manifest was detected.
        python = "requirements.txt" in filenames or "pyproject.toml" in filenames

                # What: only directories with at least one known manifest become projects.
        # this line checks a condition; the code below runs only if the condition is true.
        if npm or composer or python:
                        # What: create a Project object and append it to the result list.
            # this line appends the discovered project to the project list.
            projects.append(
                # this line is part of Python syntax and supports the surrounding lines.
                Project(
                    # this line is an element of a larger list, dictionary, or multiline text.
                    name=str(rel),
                    # this line is an element of a larger list, dictionary, or multiline text.
                    path=path,
                    # this line is an element of a larger list, dictionary, or multiline text.
                    npm=npm,
                    # this line is an element of a larger list, dictionary, or multiline text.
                    composer=composer,
                    # this line is an element of a larger list, dictionary, or multiline text.
                    python=python,
                # this line opens or closes a data structure or function call.
                )
            # this line opens or closes a data structure or function call.
            )

        # What: return all discovered projects to the caller.
    # this line ends the function and returns the result to the caller.
    return projects


# this line starts the default_tests function, a named reusable block of code.
def default_tests(project: Project) -> list[str]:
    # this line starts a multiline description of the file or function.
    """Return reasonable default test commands for a detected project."""

        # What: start with no commands and add only those matching detected tools.
    # this line creates an empty list with a type hint for readability.
    commands: list[str] = []

        # What: Composer projects commonly expose a "composer test" script.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.composer:
        # this line appends another command to the list of commands to run.
        commands.append("composer test")
        # What: --if-present prevents npm from failing when no test script exists.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.npm:
        # this line appends another command to the list of commands to run.
        commands.append("npm test --if-present")
        # What: pytest is the common Python test runner; config may override this.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.python:
        # this line appends another command to the list of commands to run.
        commands.append("python3 -m pytest")

    # this line ends the function and returns the result to the caller.
    return commands


# this line starts the default_builds function, a named reusable block of code.
def default_builds(project: Project) -> list[str]:
    # this line starts a multiline description of the file or function.
    """Return reasonable default build commands for a detected project."""

    # this line creates an empty list with a type hint for readability.
    commands: list[str] = []

    # this line checks a condition; the code below runs only if the condition is true.
    if project.npm:
        # this line appends another command to the list of commands to run.
        commands.append("npm run build --if-present")

    # this line ends the function and returns the result to the caller.
    return commands


# this line starts the make_template function, a named reusable block of code.
def make_template(root: Path, output: Path) -> None:
    # this line starts a multiline description of the file or function.
    """Create a starter JSON config from discovered projects.

      All projects are disabled by default. This prevents accidental bulk updates
      or deployments immediately after generating the file.
    this line opens or closes a multiline text description.
    """

        # What: discover projects first, then convert them into config entries.
    # this line assigns a value to a variable, saving the result under a name.
    projects = detect_projects(root)
        # What: this dict mirrors the final JSON file structure.
    # this line assigns a value to a variable, saving the result under a name.
    config = {
        # this line is an element of a larger list, dictionary, or multiline text.
        "ssh": {
            # this line is an element of a larger list, dictionary, or multiline text.
            "host": DEFAULT_HOST,
            # this line is an element of a larger list, dictionary, or multiline text.
            "port": DEFAULT_PORT,
            # this line is an element of a larger list, dictionary, or multiline text.
            "user": DEFAULT_USER,
            # this line is an element of a larger list, dictionary, or multiline text.
            "identity_file": "",
        # this line opens or closes a data structure or function call.
        },
        # this line is an element of a larger list, dictionary, or multiline text.
        "projects": [
            # this line opens or closes a data structure or function call.
            {
                # this line is an element of a larger list, dictionary, or multiline text.
                "name": p.name,
                # this line is an element of a larger list, dictionary, or multiline text.
                "path": str(p.path),
                # this line is an element of a larger list, dictionary, or multiline text.
                "enabled": False,
                # this line is an element of a larger list, dictionary, or multiline text.
                "deploy": False,
                # this line is an element of a larger list, dictionary, or multiline text.
                "remote_path": "/srv/apps/CHANGE_ME",
                # this line is an element of a larger list, dictionary, or multiline text.
                "test_commands": default_tests(p),
                # this line is an element of a larger list, dictionary, or multiline text.
                "build_commands": default_builds(p),
                # this line is an element of a larger list, dictionary, or multiline text.
                "remote_commands": [],
                # this line is an element of a larger list, dictionary, or multiline text.
                "excludes": [
                    # this line is an element of a larger list, dictionary, or multiline text.
                    ".git",
                    # this line is an element of a larger list, dictionary, or multiline text.
                    ".env",
                    # this line is an element of a larger list, dictionary, or multiline text.
                    "node_modules",
                    # this line is an element of a larger list, dictionary, or multiline text.
                    "storage/logs",
                    # this line is an element of a larger list, dictionary, or multiline text.
                    "tests",
                    # this line is an element of a larger list, dictionary, or multiline text.
                    "vendor",
                # this line opens or closes a data structure or function call.
                ],
            # this line opens or closes a data structure or function call.
            }
            # this line starts a loop, repeating operations for subsequent items.
            for p in projects
        # this line opens or closes a data structure or function call.
        ],
    # this line opens or closes a data structure or function call.
    }

        # What: persist the generated template to disk.
    # this line is part of Python syntax and supports the surrounding lines.
    write_json(output, config)
        # What: tell the operator where the file was written.
    # this line prints information in the terminal for the person running the script.
    print(f"Wrote template: {output}")
    # this line prints information in the terminal for the person running the script.
    print("All projects are disabled by default. Enable only projects that should be maintained.")


# this line starts the project_from_config function, a named reusable block of code.
def project_from_config(item: dict[str, Any]) -> Project:
    # this line starts a multiline description of the file or function.
    """Convert one JSON project entry into a Project object.

      item:
              One dictionary from config["projects"].

      The function re-detects manifest files from disk, because the local project
      may have changed since the config was generated.
    this line opens or closes a multiline text description.
    """

        # What: expand ~ and normalize relative segments to an absolute path.
    # this line converts a text path into a Path object and normalizes it.
    path = Path(item["path"]).expanduser().resolve()
        # What: list direct child file names if the directory exists; otherwise use empty set.
    # this line collects file names in the project directory to detect the project type.
    filenames = {p.name for p in path.iterdir()} if path.exists() and path.is_dir() else set()

        # What: build the runtime Project object used by the pipeline.
    # this line ends the function and returns the result to the caller.
    return Project(
        # this line is an element of a larger list, dictionary, or multiline text.
        name=item.get("name") or path.name,
        # this line is an element of a larger list, dictionary, or multiline text.
        path=path,
        # this line is an element of a larger list, dictionary, or multiline text.
        remote_path=item.get("remote_path"),
        # this line is an element of a larger list, dictionary, or multiline text.
        enabled=bool(item.get("enabled", True)),
        # this line is an element of a larger list, dictionary, or multiline text.
        deploy=bool(item.get("deploy", False)),
        # this line is an element of a larger list, dictionary, or multiline text.
        npm="package.json" in filenames,
        # this line is an element of a larger list, dictionary, or multiline text.
        composer="composer.json" in filenames,
        # this line is an element of a larger list, dictionary, or multiline text.
        python="requirements.txt" in filenames or "pyproject.toml" in filenames,
        # this line is an element of a larger list, dictionary, or multiline text.
        build_commands=list(item.get("build_commands", [])),
        # this line is an element of a larger list, dictionary, or multiline text.
        test_commands=list(item.get("test_commands", [])),
        # this line is an element of a larger list, dictionary, or multiline text.
        remote_commands=list(item.get("remote_commands", [])),
        # this line is an element of a larger list, dictionary, or multiline text.
        excludes=list(item.get("excludes", [])),
    # this line opens or closes a data structure or function call.
    )


# this line starts the update_dependencies function, a named reusable block of code.
def update_dependencies(project: Project, dry_run: bool) -> None:
    # this line starts a multiline description of the file or function.
    """Update dependency versions for one project.

      This is the risky mode. It may rewrite lockfiles:
          - composer update can change composer.lock.
          - npm update can change package-lock.json.
          - pip install -U updates installed Python packages in the active env.
    this line opens or closes a multiline text description.
    """

        # Risk: composer update may modify composer.lock and installed package versions.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.composer:
        # this line runs the prepared command and stores its exit code.
        rc = run(["composer", "update", "--no-interaction"], project.path, dry_run, timeout=1800)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: composer update failed")

        # Risk: npm update may modify package-lock.json.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.npm:
                # What: package-lock.json means npm can update within existing constraints.
        # this line builds the path to the npm lockfile.
        lock = project.path / "package-lock.json"
                # What: without a lockfile, npm install creates/resolves dependency tree.
        # this line creates a list of command arguments that will be run later.
        cmd = ["npm", "update"] if lock.exists() else ["npm", "install"]
        # this line runs the prepared command and stores its exit code.
        rc = run(cmd, project.path, dry_run, timeout=1800)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: npm update/install failed")

        # Risk: this updates the active Python environment, not a lockfile.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.python:
                # What: requirements.txt is the classic pip input file.
        # this line builds the path to requirements.txt.
        req = project.path / "requirements.txt"
        # this line checks a condition; the code below runs only if the condition is true.
        if req.exists():
            # this line runs the prepared command and stores its exit code.
            rc = run(["python3", "-m", "pip", "install", "-U", "-r", str(req)], project.path, dry_run, timeout=1800)
            # this line checks a condition; the code below runs only if the condition is true.
            if rc != 0:
                # this line deliberately raises an error because continuing would be incorrect.
                raise RuntimeError(f"{project.name}: pip install failed")


# this line starts the install_locked function, a named reusable block of code.
def install_locked(project: Project, dry_run: bool) -> None:
    # this line starts a multiline description of the file or function.
    """Install exact locked dependency versions for one project.

      This is the safer mode used when --apply-updates is not passed.
      It prepares dependencies without intentionally bumping versions.
    this line opens or closes a multiline text description.
    """

        # What: only run locked install when composer.lock exists.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.composer and (project.path / "composer.lock").exists():
        # this line runs the prepared command and stores its exit code.
        rc = run(["composer", "install", "--no-interaction", "--prefer-dist"], project.path, dry_run, timeout=1200)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: composer install failed")

        # What: npm ci requires package-lock.json and installs exact locked versions.
    # this line checks a condition; the code below runs only if the condition is true.
    if project.npm and (project.path / "package-lock.json").exists():
        # this line runs the prepared command and stores its exit code.
        rc = run(["npm", "ci"], project.path, dry_run, timeout=1200)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: npm ci failed")


# this line starts the run_commands function, a named reusable block of code.
def run_commands(project: Project, commands: list[str], dry_run: bool, label: str) -> None:
    # this line starts a multiline description of the file or function.
    """Run project-specific test/build commands.

      label:
              Human-readable phase name used in error messages, for example "tests".
    this line opens or closes a multiline text description.
    """

        # What: run commands in the order given by config.
    # this line starts a loop, repeating operations for subsequent items.
    for command in commands:
                # What: command is a string, so shell syntax in config is allowed.
        # this line runs the prepared command and stores its exit code.
        rc = run(command, project.path, dry_run, timeout=1800)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: {label} failed: {command}")


# this line starts the ssh_base function, a named reusable block of code.
def ssh_base(ssh: dict[str, Any]) -> list[str]:
    # this line starts a multiline description of the file or function.
    """Build the common SSH command prefix from config["ssh"]."""

        # What: argv list starts with the ssh executable.
    # this line creates a list of command arguments that will be run later.
    cmd = [
        # this line is an element of a larger list, dictionary, or multiline text.
        "ssh",
        # this line is an element of a larger list, dictionary, or multiline text.
        "-p",
        # this line is an element of a larger list, dictionary, or multiline text.
        str(ssh.get("port", DEFAULT_PORT)),
    # this line opens or closes a data structure or function call.
    ]

        # What: optional private key path from config.
    # this line reads the optional path to a private SSH key.
    identity = ssh.get("identity_file")
    # this line checks a condition; the code below runs only if the condition is true.
    if identity:
        # this line appends several items to the command list.
        cmd.extend(["-i", str(Path(identity).expanduser())])

        # What: append the SSH destination in user@host form.
    # this line appends one item to the end of the command list.
    cmd.append(f"{ssh.get('user', DEFAULT_USER)}@{ssh.get('host', DEFAULT_HOST)}")
        # What: return a reusable command prefix, not yet executed.
    # this line ends the function and returns the result to the caller.
    return cmd


# this line starts the deploy_project function, a named reusable block of code.
def deploy_project(project: Project, ssh: dict[str, Any], dry_run: bool) -> None:
    # this line starts a multiline description of the file or function.
    """Upload one project with rsync and run optional remote commands.

      The upload uses --delete, so files removed locally are also removed remotely.
      That is useful for clean deployments, but it makes remote_path accuracy
      critical.
    this line opens or closes a multiline text description.
    """

        # What: deployment cannot proceed without a destination directory.
    # this line checks a condition; the code below runs only if the condition is true.
    if not project.remote_path:
        # this line deliberately raises an error because continuing would be incorrect.
        raise RuntimeError(f"{project.name}: remote_path is required for deploy")

        # What: base rsync excludes protect local-only/runtime files from upload.
        # Risk: excluding .env prevents overwriting production secrets.
    # this line starts the exclusion list for rsync.
    excludes = [
        # this line is an element of a larger list, dictionary, or multiline text.
        "--exclude",
        # this line is an element of a larger list, dictionary, or multiline text.
        ".git",
        # this line is an element of a larger list, dictionary, or multiline text.
        "--exclude",
        # this line is an element of a larger list, dictionary, or multiline text.
        "node_modules",
        # this line is an element of a larger list, dictionary, or multiline text.
        "--exclude",
        # this line is an element of a larger list, dictionary, or multiline text.
        ".env",
    # this line opens or closes a data structure or function call.
    ]

        # What: append project-specific exclude rules from config.
    # this line starts a loop, repeating operations for subsequent items.
    for item in project.excludes:
                # What: rsync expects each exclude as two argv tokens: --exclude PATTERN.
        # this line extends the list of patterns that rsync must not send to the server.
        excludes.extend(["--exclude", item])

        # What: rsync receives SSH transport as one string after -e.
    # this line builds the SSH command fragment used by rsync.
    ssh_cmd = f"ssh -p {int(ssh.get('port', DEFAULT_PORT))}"
        # What: optional private key path from config.
    # this line reads the optional path to a private SSH key.
    identity = ssh.get("identity_file")
    # this line checks a condition; the code below runs only if the condition is true.
    if identity:
        # this line assigns a value to a variable, saving the result under a name.
        ssh_cmd += f" -i {shlex.quote(str(Path(identity).expanduser()))}"

        # What: build rsync remote target in user@host:/path/ format.
        # Why: rstrip avoids accidental double slash before the final /.
    # this line assembles the remote address in user@host:path format.
    remote = f"{ssh.get('user', DEFAULT_USER)}@{ssh.get('host', DEFAULT_HOST)}:{project.remote_path.rstrip('/')}/"
        # What: build argv list for rsync.
    # this line starts building the rsync command responsible for sending files.
    rsync_cmd = [
                # What: executable name.
        # this line is an element of a larger list, dictionary, or multiline text.
        "rsync",
                # What: -a preserves metadata recursively, -z compresses transfer.
        # this line is an element of a larger list, dictionary, or multiline text.
        "-az",
                # Risk: --delete removes remote files missing locally. Use only with verified remote_path.
        # this line is an element of a larger list, dictionary, or multiline text.
        "--delete",
                # What: expand the excludes list inline into rsync argv.
        # this line is an element of a larger list, dictionary, or multiline text.
        *excludes,
                # What: -e tells rsync which remote shell command to use.
        # this line is an element of a larger list, dictionary, or multiline text.
        "-e",
        # this line is an element of a larger list, dictionary, or multiline text.
        ssh_cmd,
                # What: trailing slash means copy directory contents, not the directory itself.
        # this line is an element of a larger list, dictionary, or multiline text.
        f"{str(project.path).rstrip('/')}/",
                # What: remote destination assembled above.
        # this line is an element of a larger list, dictionary, or multiline text.
        remote,
    # this line opens or closes a data structure or function call.
    ]

        # What: upload files unless dry-run is active.
    # this line runs the prepared command and stores its exit code.
    rc = run(rsync_cmd, None, dry_run, timeout=1800)
        # What: non-zero rsync exit code stops this project.
    # this line checks a condition; the code below runs only if the condition is true.
    if rc != 0:
        # this line deliberately raises an error because continuing would be incorrect.
        raise RuntimeError(f"{project.name}: rsync failed")

        # What: run post-deploy commands on the server in configured order.
    # this line starts a loop, repeating operations for subsequent items.
    for command in project.remote_commands:
                # What: cd into deploy directory first, then run the configured command.
        # this line creates a command that first changes into the server directory.
        remote_command = f"cd {shlex.quote(project.remote_path)} && {command}"
                # What: *ssh_base expands the SSH argv prefix into this command list.
        # this line runs the prepared command and stores its exit code.
        rc = run([*ssh_base(ssh), remote_command], None, dry_run, timeout=1200)
        # this line checks a condition; the code below runs only if the condition is true.
        if rc != 0:
            # this line deliberately raises an error because continuing would be incorrect.
            raise RuntimeError(f"{project.name}: remote command failed: {command}")


# this line starts the execute function, a named reusable block of code.
def execute(config_path: Path, apply_updates: bool, deploy: bool, dry_run: bool, only: set[str]) -> int:
    # this line starts a multiline description of the file or function.
    """Run the maintenance pipeline for all selected projects.

      Pipeline per project:
      this line is an element of a larger list, dictionary, or multiline text.
      1. install locked dependencies or update dependencies,
      this line is an element of a larger list, dictionary, or multiline text.
      2. run tests,
      this line is an element of a larger list, dictionary, or multiline text.
      3. run builds,
          4. optionally deploy.

      Return:
              0 when all selected projects pass, 1 when at least one fails.
    this line opens or closes a multiline text description.
    """

        # What: read the operator-maintained JSON config from disk.
    # this line reads the JSON configuration from a file.
    config = load_json(config_path)
        # What: SSH settings are optional; defaults fill missing keys.
    # this line reads SSH settings from the config or uses an empty dictionary.
    ssh = config.get("ssh", {})
        # What: convert raw JSON project dictionaries into Project objects.
    # this line creates a project list using list-comprehension syntax.
    projects = [project_from_config(item) for item in config.get("projects", [])]
        # What: keep only enabled projects, and optionally only names requested by --only.
    # this line creates a project list using list-comprehension syntax.
    projects = [p for p in projects if p.enabled and (not only or p.name in only)]

        # What: empty selection is not an error; there is simply nothing to do.
    # this line checks a condition; the code below runs only if the condition is true.
    if not projects:
        # this line prints information in the terminal for the person running the script.
        print("No enabled projects matched.")
        # this line ends the function and returns the result to the caller.
        return 0

        # What: collect failures instead of aborting the whole batch on first error.
    # this line creates an empty list with a type hint for readability.
    failures: list[str] = []

        # What: process projects one by one.
    # this line starts a loop, repeating operations for subsequent items.
    for project in projects:
                # What: visible section marker in terminal output.
        # this line prints information in the terminal for the person running the script.
        print(f"\n=== {project.name} ===")

                # Why: per-project try/except lets later projects continue after one failure.
        # this line starts a block where errors may occur and be caught below.
        try:
                        # What: fail early if config points to a missing local directory.
            # this line checks a condition; the code below runs only if the condition is true.
            if not project.path.exists():
                # this line deliberately raises an error because continuing would be incorrect.
                raise RuntimeError(f"path does not exist: {project.path}")

                        # What: choose between risky update mode and safer locked install mode.
            # this line checks a condition; the code below runs only if the condition is true.
            if apply_updates:
                # this line is part of Python syntax and supports the surrounding lines.
                update_dependencies(project, dry_run)
            # this line marks the fallback branch when the earlier condition was not met.
            else:
                # this line is part of Python syntax and supports the surrounding lines.
                install_locked(project, dry_run)

                        # What: tests must pass before builds.
            # this line is part of Python syntax and supports the surrounding lines.
            run_commands(project, project.test_commands, dry_run, "tests")
                        # What: builds must pass before deployment.
            # this line is part of Python syntax and supports the surrounding lines.
            run_commands(project, project.build_commands, dry_run, "build")

                        # What: deploy requires both global --deploy and per-project deploy=true.
            # this line checks a condition; the code below runs only if the condition is true.
            if deploy and project.deploy:
                # this line is part of Python syntax and supports the surrounding lines.
                deploy_project(project, ssh, dry_run)
            # this line checks another condition if the previous conditions did not match.
            elif deploy:
                                # What: explain why upload did not happen for this project.
                # this line prints information in the terminal for the person running the script.
                print("Deploy skipped: project.deploy=false")

                # What: any exception in this project is recorded as a failure.
        # this line handles an error so the whole script does not stop immediately.
        except Exception as exc:
                        # What: keep project name together with the exception message.
            # this line records the error description so it can be shown in the summary.
            failures.append(f"{project.name}: {exc}")
                        # What: stderr separates errors from normal command logs.
            # this line prints information in the terminal for the person running the script.
            print(f"ERROR: {exc}", file=sys.stderr)

        # What: final summary makes long batch output scannable.
    # this line prints information in the terminal for the person running the script.
    print("\n=== Summary ===")
    # this line prints information in the terminal for the person running the script.
    print(f"Projects: {len(projects)}")
    # this line prints information in the terminal for the person running the script.
    print(f"Failures: {len(failures)}")

        # What: print each failure on its own line for easy copy/paste.
    # this line starts a loop, repeating operations for subsequent items.
    for failure in failures:
        # this line prints information in the terminal for the person running the script.
        print(f"- {failure}")

        # What: non-zero process exit means automation/CI can detect failure.
    # this line ends the function and returns the result to the caller.
    return 1 if failures else 0


# this line starts the main function, a named reusable block of code.
def main() -> int:
    # this line starts a multiline description of the file or function.
    """CLI entry point.

      Parses arguments, creates a template if requested, and otherwise starts the
      maintenance pipeline.
    this line opens or closes a multiline text description.
    """

        # What: create the command-line parser and top-level help text.
    # this line creates an argument parser, the mechanism that understands CLI options.
    parser = argparse.ArgumentParser(description="Update, test, build and deploy configured projects.")
        # What: --root is used only when generating a config template.
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--root", default="/workspace", help="Workspace root for template generation.")
        # What: --config points to the JSON file controlling projects and SSH.
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--config", default="./maintenance.config.json", help="Config file path.")
        # What: store_true means the flag becomes True when present.
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--init-config", action="store_true", help="Create a disabled template config and exit.")
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--apply-updates", action="store_true", help="Run package update commands instead of locked installs.")
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--deploy", action="store_true", help="Deploy projects with deploy=true via rsync/SSH.")
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--execute", action="store_true", help="Actually run commands. Without this, dry-run is used.")
    # this line adds one command-line option that can be used when running the script.
    parser.add_argument("--only", action="append", default=[], help="Run only a named project. Can be repeated.")
        # What: parse sys.argv according to definitions above.
    # this line reads command-line arguments and stores them in the args object.
    args = parser.parse_args()

        # What: normalize --root to an absolute pathlib.Path.
    # this line converts a text path into a Path object and normalizes it.
    root = Path(args.root).expanduser().resolve()
        # What: normalize --config to an absolute pathlib.Path.
    # this line converts a text path into a Path object and normalizes it.
    config_path = Path(args.config).expanduser().resolve()

        # What: template generation is a separate mode and exits immediately.
    # this line checks a condition; the code below runs only if the condition is true.
    if args.init_config:
        # this line is part of Python syntax and supports the surrounding lines.
        make_template(root, config_path)
        # this line ends the function and returns the result to the caller.
        return 0

        # What: normal run requires an existing config file.
    # this line checks a condition; the code below runs only if the condition is true.
    if not config_path.exists():
        # this line prints information in the terminal for the person running the script.
        print(f"Config not found: {config_path}", file=sys.stderr)
        # this line prints information in the terminal for the person running the script.
        print(f"Create one with: {sys.argv[0]} --init-config", file=sys.stderr)
        # this line ends the function and returns the result to the caller.
        return 2

        # What: lack of --execute means dry-run mode. This is the main safety default.
    # this line decides whether the script only prints commands or actually executes them.
    dry_run = not args.execute

    # this line checks a condition; the code below runs only if the condition is true.
    if dry_run:
        # this line prints information in the terminal for the person running the script.
        print("DRY RUN: pass --execute to run commands.")
    # this line checks a condition; the code below runs only if the condition is true.
    if args.deploy and dry_run:
        # this line prints information in the terminal for the person running the script.
        print("Deploy is also dry-run. Nothing will be uploaded.")

        # What: hand parsed CLI values into the orchestration function.
    # this line ends the function and returns the result to the caller.
    return execute(
        # this line is an element of a larger list, dictionary, or multiline text.
        config_path=config_path,
        # this line is an element of a larger list, dictionary, or multiline text.
        apply_updates=args.apply_updates,
        # this line is an element of a larger list, dictionary, or multiline text.
        deploy=args.deploy,
        # this line is an element of a larger list, dictionary, or multiline text.
        dry_run=dry_run,
        # this line is an element of a larger list, dictionary, or multiline text.
        only=set(args.only),
    # this line opens or closes a data structure or function call.
    )


# What: this block runs only when the file is executed as a script, not imported.
# this line checks a condition; the code below runs only if the condition is true.
if __name__ == "__main__":
        # What: SystemExit uses main() return code as the process exit status.
    # this line deliberately raises an error because continuing would be incorrect.
    raise SystemExit(main())
