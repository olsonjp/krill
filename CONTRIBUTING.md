# Contributing to Krill

Thank you for your interest in contributing to Krill! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Your environment (OS, Python version, Django version)
- Any relevant error messages or logs

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:
- A clear description of the feature
- Use cases and examples
- Potential implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository** and clone your fork
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**:
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass
4. **Commit your changes**:
   ```bash
   git commit -m "Add: description of your changes"
   ```
   Use clear, descriptive commit messages
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request**:
   - Provide a clear description of your changes
   - Reference any related issues
   - Ensure CI checks pass

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/krill.git
   cd krill
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Comment complex logic

## Testing

- Write tests for new features and bug fixes
- Ensure all existing tests pass before submitting
- Aim for good test coverage
- Run tests with:
  ```bash
  python manage.py test
  ```

## Documentation

- Update README.md if you add features that affect setup or usage
- Add docstrings to new functions and classes
- Update inline comments for complex logic
- Keep documentation clear and concise

## Project Structure

```
krill/
├── krill/              # Main Django project
│   ├── settings.py     # Base settings
│   └── management/     # Custom management commands
├── person/             # User management app
├── sample/             # Sample tracking app
├── storage/            # Storage management app
├── reports/            # Reporting app
└── transaction/        # Transaction tracking app
```

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the `question` label
- Check existing issues and discussions

Thank you for contributing to Krill!

