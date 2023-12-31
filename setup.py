from setuptools import setup, find_packages

setup(
    name='ForecastBlurDenoise',
    version='0.1.0',
    packages=['forecast_blur_denoise'],
    install_requires=[
        # List your dependencies here
        'torch',
        'numpy',
        'pandas',
        'optuna',
        'gpytorch'
        # Add other dependencies as needed
    ],
    license='MIT'
)
