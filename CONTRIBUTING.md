# Contributing to TellySeerr

First off, thank you for considering contributing! We welcome any help, whether it's reporting a bug, suggesting a feature, or writing code.

To ensure a smooth process, please review these guidelines.

## 🐞 Reporting Bugs

If you find a bug, please [open an issue](https://github.com/DESTROYER-32/TellySeerr/issues) and provide the following:

* A clear and descriptive title.
* Steps to reproduce the bug.
* Any relevant error messages or logs from your console.
* The version of the bot you are running.

## ✨ Suggesting Features

We'd love to hear your ideas! Please [open an issue](https://github.com/DESTROYER-32/TellySeerr/issues) to suggest a new feature, explaining what it should do and why it would be useful.

## 🧑‍💻 Submitting Code (Pull Requests)

If you'd like to fix a bug or add a feature, here's how to get your development environment set up.

### 1. Setup Your Environment

1.  **Fork** the repository to your own GitHub account.
2.  **Clone** your fork locally:
    ```bash
    git clone [https://github.com/your-username/TellySeerr.git](https://github.com/your-username/TellySeerr.git)
    cd TellySeerr
    ```
3.  **Install dependencies** using Pipenv. This will also install the development tools like `ruff`.
    ```bash
    pipenv install --dev
    ```
4.  **Set up your secrets file** by copying the sample:
    ```bash
    cp .env.sample .env
    ```
    Now, edit `.env` with your own API keys for testing. **Do not commit this file.**

5.  **Install the pre-commit hooks.** This is a crucial step! It will automatically run `ruff` to format your code before you commit.
    ```bash
    pipenv run pre-commit install
    ```

### 2. Make Your Changes

1.  Create a new branch for your feature or bugfix:
    ```bash
    git checkout -b feature/my-new-feature
    ```
2.  Write your code!
    * Follow the existing code style.
    * If you add a new handler, be sure to add it in the `bot/handlers/` directory. The loader will pick it up automatically.
    * If you add a new user-facing command, please add it to the `USER_COMMANDS` or `ADMIN_COMMANDS` list in `main.py`.

### 3. Submit Your Pull Request

1.  Commit your changes. The pre-commit hook should automatically format your files.
    ```bash
    git commit -m "feat: Add my new feature"
    ```
2.  Push your branch to your fork:
    ```bash
    git push origin feature/my-new-feature
    ```
3.  Go to the original repository on GitHub (`https://github.com/DESTROYER-32/TellySeerr`) and open a **Pull Request**.
4.  Write a clear description of what your PR does and link to any relevant issues.

Thank you for contributing!