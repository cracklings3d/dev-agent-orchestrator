from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="household-orchestrator",
    version="1.0.0",
    description="AI Agent 编排系统 - 使用 LangGraph 实现多 Agent 协作开发",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "langgraph>=0.2.0",
        "langchain>=0.3.0",
        "langchain-openai>=0.2.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "click>=8.1.0",
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "orchestrator=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
