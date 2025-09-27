"""
Library core of ``repoconf``.
"""

import logging

import repoconf

rclc = repoconf.repoconf_lc.clone_with_envs(f"{repoconf.REPOCONF_LOG_ENV}_CORE")
rclc_log = logging.getLogger(__name__)
rclc_logger = rclc.configure(rclc_log)


def main():
    rclc_logger.success("repoconf")


if __name__ == "__main__":
    main()
