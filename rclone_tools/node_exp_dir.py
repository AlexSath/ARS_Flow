import logging, os, uuid
from datetime import datetime
from pathlib import Path, PurePosixPath
from subprocess import CompletedProcess
from typing import Tuple, List

from .rclone import _rclone_process

class RcloneError(RuntimeError):
    def __init__(self, argv, proc: CompletedProcess):
        self.argv, self.proc = argv, proc
        super().__init__(
            f"rclone {' '.join(argv)} failed (exit {proc.returncode}): "
            f"{(proc.stderr or '').strip()[-2000:]}"
        )

class NodeExperimentsDirectory:

    def __init__(self, drive: str, source_relpath: str,
                 node_mountpath: str, output_dirname: str = "out",
                 proxy: str | None = None):
        self.drive = drive
        self.source_relpath = source_relpath.rstrip("/")
        self.remote_path = f"{self.drive}:{self.source_relpath}"

        self.experiment_name = PurePosixPath(self.source_relpath).name
        if not self.experiment_name:
            raise ValueError(f"source_relpath has no final component: {source_relpath!r}")

        self.node_root = Path(node_mountpath)
        self.dest_dirpath = self.node_root / self.experiment_name
        self.output_dirname = output_dirname
        self.output_dirpath = self.dest_dirpath / self.output_dirname

        self._run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.log_filepath = (
            self.node_root / "log" / f"{self.experiment_name}-{self._run_id}.log"
        )
        self.logger, self._log_handler = self._setup_logger()

        self.os_env = os.environ.copy()
        if proxy is not None:
            self.os_env["HTTP_PROXY"] = proxy
            self.os_env["HTTPS_PROXY"] = proxy
            self.logger.info("Proxy set to %s", proxy)

        self._staged = False
        self._closed = False

    # --- construction helpers -------------------------------------------

    def _setup_logger(self) -> Tuple[logging.Logger, logging.FileHandler]:
        self.log_filepath.parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(f"{__name__}.{self._run_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.handlers.clear()          # defensive; run_id should be unique
        handler = logging.FileHandler(self.log_filepath, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        logger.addHandler(handler)
        logger.info("Log initialized for %s", self.remote_path)
        return logger, handler

    # --- rclone ----------------------------------------------------------

    def _rclone(self, argv: List[str], check: bool = True) -> CompletedProcess:
        proc = _rclone_process(*argv, env=self.os_env, timeout=None)
        stream = self.logger.error if proc.returncode else self.logger.info
        if proc.stdout:
            self.logger.info("rclone stdout: %s", proc.stdout.strip())
        if proc.stderr:
            stream("rclone stderr: %s", proc.stderr.strip())
        if check and proc.returncode != 0:
            raise RcloneError(argv, proc)
        return proc

    def _assert_remote_exists(self) -> None:
        proc = self._rclone(["lsd", self.remote_path], check=False)
        if proc.returncode == 3:
            raise FileNotFoundError(
                f"{self.source_relpath!r} not found on drive {self.drive!r}"
            )
        if proc.returncode != 0:
            raise RcloneError(["lsd", self.remote_path], proc)

    # --- lifecycle -------------------------------------------------------

    def stage(self) -> "NodeExperimentsDirectory":
        """Copy the remote experiment directory to the node. Idempotent per instance."""
        if self._staged:
            return self
        self._assert_remote_exists()
        try:
            self.dest_dirpath.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise FileExistsError(
                f"{self.dest_dirpath} already exists; another run may own it"
            ) from None

        self.logger.info("Copying %s -> %s", self.remote_path, self.dest_dirpath)
        self._rclone(["copy", self.remote_path, str(self.dest_dirpath)])

        self.output_dirpath.mkdir(exist_ok=True)
        self.logger.info("Output directory: %s", self.output_dirpath)
        self._staged = True
        return self

    def publish(self) -> None:
        """Copy analysis outputs back to the drive. Safe to call repeatedly."""
        if not self._staged:
            raise RuntimeError("publish() before stage()")
        if self._closed:
            raise RuntimeError("publish() after close()")
        self._rclone([
            "copy", str(self.output_dirpath),
            f"{self.remote_path}/{self.output_dirname}",
        ])

    def close(self) -> None:
        """Flush and upload the log. Idempotent; the instance is done after this."""
        self.publish()
        if self._closed:
            return
        self._closed = True
        try:
            if self._staged:
                self._log_handler.flush()
                self._log_handler.close()
                self._rclone([
                    "copyto", str(self.log_filepath),
                    f"{self.remote_path}/{self.output_dirname}/logs/{self.log_filepath.name}",
                ], check=False)   # don't raise during teardown
        finally:
            self.logger.removeHandler(self._log_handler)
            self._log_handler.close()   # no-op if already closed

    def __enter__(self):
        return self.stage()

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.publish()
            else:
                self.logger.error("Run failed; skipping output publish", exc_info=exc)
        finally:
            self.close()
        return False