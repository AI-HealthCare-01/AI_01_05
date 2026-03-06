# SYSTEM_DESIGN

This document defines the core system design rules for this project.

---

## 1. Python Version & Typing

- We use **Python 3.13 or higher**.
- Do **not** use the `typing` module for type hints.
- Always use **built-in types** for annotations (e.g., `int`, `str`, `list`, `dict`, etc.).

---

## 2. Code Style

- Follow the **Google Python Style Guide**:
  - <https://google.github.io/styleguide/pyguide.html>
- Follow **PEP 8** (Python’s official style guide):
  - <https://peps.python.org/pep-0008/>

If there is any conflict between local conventions and these guides, prefer clarity and consistency within this project.

---

## 3. Object-Oriented Design

We favor **object-oriented programming (OOP)** and its core principles:

- **Encapsulation** – Group related data and behavior inside classes and hide internal details.
- **Abstraction** – Expose clear interfaces and hide unnecessary implementation details.
- **Inheritance** – Reuse behavior via well-designed base classes and subclasses when appropriate.
- **Polymorphism** – Design interfaces so that different implementations can be used interchangeably.

OOP should improve readability and maintainability, not add unnecessary complexity.

---

## 4. Architectural Pattern

- We **aim for a layered architecture pattern** (e.g., presentation, application/service, domain, infrastructure).
- Each layer should have a clear responsibility and minimal knowledge of other layers.

At the same time:

- Do **not** over-apply design patterns or split the codebase into too many tiny files.
- Avoid “architecture for architecture’s sake.”
- Aim for:
  - **Reasonable maintainability**
  - **Reasonable separation of concerns**
  - **Always pragmatic, balanced design**

In short, we prefer a **practical, moderately layered architecture** that is easy to understand, extend, and maintain, rather than a theoretically "perfect" but over-engineered structure.
