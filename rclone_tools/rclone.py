
import subprocess
from subprocess import CompletedProcess

def _rclone_process(*rclone_args, **process_kwargs) -> CompletedProcess:
    # TODO: add checking for process_kwargs to prevent duplicates
    process = subprocess.run(
        [
            "rclone",
            *rclone_args
        ],
        # capture_output=True,
        # text=True,
        # shell=False,
        # env=env,
        # timeout=timeout,
        **process_kwargs
    )
    return process