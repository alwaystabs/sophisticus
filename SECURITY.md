# Security Policy

## Supported Versions

We are currently in active development (beta). Security updates are provided only for the latest version.

| Version      | Supported          |
| -----------  | ------------------ |
| **0.3-beta** | :white_check_mark: |
| < 0.3-beta   | :x:                |

## Reporting a Vulnerability

We take security issues seriously. If you discover a vulnerability in Sophisticus, please do **not** open a public GitHub issue.

### Preferred Method (Recommended)

1.  Go to the **Security** tab of this repository.
2.  Click on **"Report a vulnerability"** (GitHub Private Security Advisory).
3.  Fill out the form with as many details as possible.

This method is private and ensures that the issue is handled securely and responsibly.

### Alternative Method (Email)

If you cannot use the GitHub Security Advisory feature, you can send an email to `reservedstep@gmail.com`. Please do not include sensitive data in the initial email; we will provide a secure channel for further communication.

### What to Include in Your Report

To help us understand and resolve the issue quickly, please include:

- **A clear description** of the vulnerability.
- **Steps to reproduce** the issue.
- The **affected versions** of Sophisticus.
- The **potential impact** of the vulnerability (e.g., information disclosure, remote code execution, etc.).
- Any **suggested fixes** or mitigations you have identified (optional).

## Disclosure Policy

We follow a coordinated disclosure policy:

1.  You report the vulnerability privately.
2.  We acknowledge the report and work on a fix.
3.  We will release a patch in a new version and publicly disclose the issue via a **GitHub Security Advisory**.
4.  We will give credit to the reporter (unless anonymity is requested).

## Security Best Practices

To keep your own instance of Sophisticus secure, please follow these guidelines:

- **Keep `config.py` secure:** Never commit your `config.py` file to version control. It contains your Telegram Bot Token and API keys.
- **Use strong secrets:** Generate a strong, unique `TOKEN` for your Telegram bot.
- **Limit Admin Access:** Your `ADMIN_ID` has extensive control over the bot (`/shutdown`, `/logs`, etc.). Keep your Telegram account secure.
- **Keep dependencies updated:** Regularly update the libraries listed in `requirements.txt` to get the latest security patches.
- **Isolate the environment:** Consider running the bot in a dedicated Python virtual environment.
- **Firewall:** It's recommended to run the bot on a secure local network.

Thank you for helping make Sophisticus a safer project for everyone.