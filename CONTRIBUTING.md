# 🤝 Contributing to RAINGOD-ComfyUI-Integration

Thank you for your interest in contributing to the RAINGOD AI Music Kit! This project aims to revolutionize AI-driven music production workflows, and your contributions help make that vision a reality.

---

## 🎯 Project Mission

**RAINGOD-ComfyUI-Integration** is the visual generation engine for AI music production. We're building production-grade tooling for:

- Automated album cover generation
- Music video frame creation
- Audio-visual synchronization
- ComfyUI workflow optimization for music content

---

## 👥 Ways to Contribute

### 1. 🐛 Bug Reports

**Found a bug?** Help us fix it!

- Use the [Issue Tracker](https://github.com/POWDER-RANGER/RAINGOD-ComfyUI-Integration/issues)
- Check if the issue already exists before creating a new one
- Provide detailed reproduction steps
- Include error messages, system info, and screenshots
- Label with `bug` tag

**Good Bug Report Example:**
```
Title: ComfyUI API returns 500 error on thumbnail generation

Environment:
- OS: Windows 11
- Python: 3.10.8
- ComfyUI Version: Latest (git hash: abc123)

Steps to Reproduce:
1. Run `python generate_album_art.py --preset thumbnail`
2. Error occurs during API call to /prompt endpoint

Expected: 512x512 thumbnail generated
Actual: HTTP 500 error

Error Log:
[paste error trace here]
```

### 2. ✨ Feature Requests

**Have an idea?** We'd love to hear it!

- Open an issue with the `enhancement` label
- Describe the use case and expected benefit
- Explain how it fits with the RAINGOD workflow
- Consider implementation complexity

### 3. 📝 Documentation

**Documentation is critical!**

- Fix typos, clarify explanations
- Add usage examples
- Improve API documentation
- Write tutorials or guides
- Update README or wiki pages

### 4. 💻 Code Contributions

**Ready to code?** Follow the process below:

#### Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/RAINGOD-ComfyUI-Integration.git
cd RAINGOD-ComfyUI-Integration
```

#### Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

#### Make Your Changes
- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

#### Test Your Changes
```bash
# Run tests (when test suite is added)
pytest tests/

# Manual testing
python examples/your_example.py
```

#### Commit with Clear Messages
```bash
git add .
git commit -m "feat: add audio-reactive frame generation"
# or
git commit -m "fix: resolve ComfyUI timeout issue"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

#### Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear title describing the change
- Detailed description of what and why
- Reference any related issues
- Screenshots/examples if applicable

---

## 📜 Code Style Guidelines

### Python

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use meaningful variable names
- Write docstrings for functions and classes

```python
def generate_image(prompt: str, preset: str = "quality") -> dict:
    """
    Generate image using ComfyUI API.
    
    Args:
        prompt: Text prompt for image generation
        preset: Sampler preset ("fast", "quality", "ultra")
        
    Returns:
        dict: Response containing image URL and metadata
    """
    pass
```

### JavaScript/HTML

- Use 2-space indentation
- Semicolons required
- ES6+ syntax preferred
- Use `const` and `let`, avoid `var`

### Shell Scripts

- Use `#!/bin/bash` shebang
- Add comments for complex operations
- Test on multiple platforms if possible

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] Test on fresh Python environment
- [ ] Verify ComfyUI API connectivity
- [ ] Test all affected workflows
- [ ] Check error handling
- [ ] Verify documentation accuracy

### Automated Tests (Coming Soon)

```bash
# Run full test suite
pytest

# Run specific test file
pytest tests/test_backend.py

# Run with coverage
pytest --cov=backend
```

---

## 🔍 Pull Request Review Process

1. **Automated Checks**: CI/CD runs linting and tests
2. **Code Review**: Maintainer reviews code quality and design
3. **Feedback**: Address any requested changes
4. **Approval**: Maintainer approves PR
5. **Merge**: PR is merged into main branch

**Review Timeline:**
- Small fixes: 1-3 days
- Features: 3-7 days
- Major changes: 7-14 days

---

## 🚫 What NOT to Contribute

- **Malicious code** or security vulnerabilities
- **Copyrighted content** without permission
- **Spam** or low-quality PRs
- **Breaking changes** without discussion
- **Unrelated features** outside project scope

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

See [LICENSE](LICENSE) for details.

---

## 👤 Attribution

All contributors will be recognized in:
- Repository contributors list
- Release notes (for significant contributions)
- Special mentions in documentation

---

## 💬 Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **ComfyUI Discussion**: [#11176](https://github.com/comfyanonymous/ComfyUI/discussions/11176)
- **Contact**: See [CONTACT.md](CONTACT.md) for direct communication

---

## 🌟 Recognition

### Top Contributors

(List will be populated as contributions come in)

### Special Thanks

- **ComfyUI Team**: For the incredible framework
- **Early Adopters**: For testing and feedback
- **Community**: For support and suggestions

---

## ❓ Questions?

Not sure where to start? Here are some beginner-friendly tasks:

- [ ] Fix typos in documentation
- [ ] Add usage examples
- [ ] Improve error messages
- [ ] Write tests for existing code
- [ ] Create workflow templates

**Need help?** Open an issue labeled `question` or reach out via [CONTACT.md](CONTACT.md).

---

**Thank you for making RAINGOD better! 🎵✨**

---

*Last Updated: December 7, 2025*  
*Maintainer: Curtis Charles Farrar*  
*ORCID: 0009-0008-9273-2458*
