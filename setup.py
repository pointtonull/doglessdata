from distutils.core import setup

setup(
    # Application name:
    name="DoglessData",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Carlos M. Cabrera",
    author_email="point.to@gmail.com",

    # Packages
    packages=["doglessdata"],

    # Include additional files into the package
    include_package_data=False,

    # Details
    url="https://github.com/pointtonull/doglessdata",

    license="LICENSE",
    description="Agentless implementation for Datadog for AWS Lambda",

    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[],
)
