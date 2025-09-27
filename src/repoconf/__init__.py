"""
🧠 Centrally configure your decentralised 🐙 git repo.

Create, edit, set, unset, ... etc. the repo's central configurations. These configurations are stored in a branch which
can then be shared with all the repo's collaborators.
"""
import logging

from logician.configurators.env import LgcnEnvListLC
from logician.stdlog.configurator import StdLoggerConfigurator, VQCommLoggerConfigurator

REPOCONF_LOG_ENV = "REPOCONF_LOG"

repoconf_lc = LgcnEnvListLC([REPOCONF_LOG_ENV], VQCommLoggerConfigurator(None, StdLoggerConfigurator()))
