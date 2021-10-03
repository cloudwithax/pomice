import setuptools

with open("README.md") as f:
    readme = f.read()


setuptools.setup(
    name="pomice",
    author="cloudwithax",
    version="1.0.4",
    url="https://github.com/cloudwithax/pomice",
    packages=setuptools.find_packages(),
    license="GPL",
    description="The modern Lavalink wrapper designed for Discord.py",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=['discord.py>=1.7.1'],
    extra_require=None,
    classifiers=[
        "Framework :: AsyncIO",
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries',
        "Topic :: Internet"
    ],
    python_requires='>=3.8',
    keywords=['pomice', 'lavalink', "discord.py"],
)