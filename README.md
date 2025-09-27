# py-repoconf

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/repoconf)
![PyPI - Types](https://img.shields.io/pypi/types/repoconf)
![GitHub License](https://img.shields.io/github/license/Vaastav-Technologies/py-repoconf)
[![🔧 test](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/test.yml/badge.svg)](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/test.yml)
[![💡 typecheck](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/typecheck.yml/badge.svg)](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/typecheck.yml)
[![🛠️ lint](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/lint.yml/badge.svg)](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/lint.yml)
[![📊 coverage](https://codecov.io/gh/Vaastav-Technologies/py-repoconf/branch/main/graph/badge.svg)](https://codecov.io/gh/Vaastav-Technologies/py-repoconf)
[![📤 Upload Python Package](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Vaastav-Technologies/py-repoconf/actions/workflows/python-publish.yml)
![PyPI - Version](https://img.shields.io/pypi/v/repoconf)

---

**🧠 Centrally configure your decentralised 🐙 git repo.**

Git, being an awesomely decentralised system, has ways to have decentralised configurations per user. However, 
times require certain configurations to be shared and tracked centrally among various collaborators. Some examples of
centrally sharable configurations are:

- 💻 Branch descriptions (or better, branch READMEs).
- 💡Issues/Features/Tasks related to the repo.
- 🪼 Certain properties that closely relate to the repo.
- 📕 Rules related to per-branch collaborations and conventions.
- 🔒 Encrypted secrets.
- 🎁 Deployment, packaging and distribution mechanics.
- ⬆️ ... and more


Repoconf is developed to address this issue. It stores central configuration in the `__repoconf/default/main` branch
and this centrally stored distributed configuration can be:

- 🟢 accessed using git config commands and aliases
- ➕ added
- ➖ removed
- ↗️ pushed
- ↙️ pulled

... just like any other git branches 👏👻.

## Quick Start

### Command usage

* List all the configurations for the current repo

    ```shell
    repoconf config --list
    ```

* Add configuration

    ```shell
    repoconf config branch.my-branch.description "This branch is created for something which one may not readily remember in the future."
    repoconf config branch.my-sharable-branch.description "This branch is to be shared with others and thus requires concise description on what it is created for."
    ```

... supports nearly all options that `git config` command supports. 
See [git config documentation](https://git-scm.com/docs/git-config) for more details.

## Installation

```shell
pip install repoconf
```
