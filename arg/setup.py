from setuptools import setup, find_packages

setup(
    name="azure-resource-graph",
    version="0.1.0",
    py_modules=["azure_resource_graph"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            "azure-resource-graph=azure_resource_graph:main",
        ],
    },
    author="Azure Resource Graph Generator",
    author_email="example@example.com",
    description="A tool to visualize Azure resource dependencies",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/azure-resource-graph",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.6",
) 