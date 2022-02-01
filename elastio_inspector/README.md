# Elastio Inspector

Inspects the account for elastio resources.

This python package aims to be compliant with PEP standards 8, 345, and 420. It is not concerned with PEP 3108.

## How To

### Development

Create a virtual environment. All code is in the `src/elastio_inspector` sub directory.

### Testing

This package uses `tox` and `pytest` for testing. The single dependency for test can be resolved using the command `pip install tox && tox -r`

### Release

Use python `setuptools` to release a `sdist` or `bdist` package as required.

## Usage

`pip install . && elastio_inspector`

### Destruction

`elastio_inspector --d` or `elastio_inspector --destroy` will destroy resources.

The string `elastio` is hard coded into the application.

Please use with caution.
