import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
# README = (HERE / "README.rst").read_text()

# This call to setup() does all the work
setuptools.setup(
    name="api_access_server",
    version="0.0.1",
    description="Serve internal APIs with common access management",
    # long_description=README,
    # long_description_content_type="text/x-rst",
    author="Alab laboratoria / Adam Morawski",
    author_email="adam.morawski@alab.com.pl",
    license="proprietary",
    classifiers=[
        "Programming Language :: Python"
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.4"
)