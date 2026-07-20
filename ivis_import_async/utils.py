import logging
import os

_logger = logging.getLogger(__name__)


def must_run_without_delay(env):
    """Retrun true if jobs have to run immediately.

    :param env: `odoo.api.Environment` instance
    """
    if os.getenv("QUEUE_JOB__NO_DELAY"):
        _logger.warning("`QUEUE_JOB__NO_DELAY` env var found. NO JOB scheduled.")
        return True

    # TODO: drop in v17
    deprecated_keys = ("_job_force_sync")
    for key in deprecated_keys:
        if env.context.get(key):
            _logger.warning(
                "`%s` ctx key found. NO JOB scheduled. "
                "Note that this key is deprecated: please use `queue_job__no_delay`",
                key,
            )
            return True

    if env.context.get("queue_job__no_delay"):
        _logger.warning("`queue_job__no_delay` ctx key found. NO JOB scheduled.")
        return True
