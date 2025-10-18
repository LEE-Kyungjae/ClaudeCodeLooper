"""
ClaudeCodeLooper - Automated monitoring and restart system for Claude Code usage limits
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

# Read requirements
def read_requirements(filename):
    with open(filename, encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="claude-code-looper",
    version="1.0.0",
    author="Kyungjae Lee",
    author_email="your-email@example.com",
    description="Automated monitoring and restart system for Claude Code usage limits",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/LEE-Kyungjae/ClaudeCodeLooper",
    packages=find_packages(exclude=["tests", "tests.*", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-looper=src.cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", ".claude/commands/*.md"],
    },
    keywords=[
        "claude",
        "claude-code",
        "automation",
        "monitoring",
        "restart",
        "cli",
        "ai",
        "assistant",
    ],
    project_urls={
        "Bug Reports": "https://github.com/LEE-Kyungjae/ClaudeCodeLooper/issues",
        "Source": "https://github.com/LEE-Kyungjae/ClaudeCodeLooper",
        "Documentation": "https://github.com/LEE-Kyungjae/ClaudeCodeLooper/wiki",
    },
)
