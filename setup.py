from setuptools import setup, find_packages, find_namespace_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# workaround a bug introduced by pyproject.toml
# https://github.com/pypa/pip/issues/7953#issuecomment-645133255
import site, sys; site.ENABLE_USER_SITE = True

setup(
  name='spinalcordtoolbox-data-PAM50',
  description='Part of https://github.com/neuropoly/spinalcordtoolbox',
  long_description=(here / 'README.md').read_text(encoding='utf-8'),
  long_description_content_type='text/markdown',
  author='Neuropoly',
  author_email='neuropoly@googlegroups.com',
  url='https://spinalcordtoolbox.com/',
  project_urls={
      'Source': 'https://github.com/sct-data/PAM50',
      #'Documentation': '',
  },
  #license='CC-BY-NC', ??
  #license_files=[ ... ] # TODO?

  packages=find_namespace_packages('src/'),
  package_dir={"":"src/"},

  # with setuptools_scm, means it includes non-python files if they're under git
  include_package_data=True,

  # with setuptools_scm, get the version out of the most recent git tag.
  # the tags must be formatted as semver.
  use_scm_version=True,

  # pyproject.toml::build-system.requires is supposed to supersede this, but it's still very new so we duplicate it.
  setup_requires=[
    'setuptools',
    'setuptools_scm[toml]',
    'wheel',
  ],

  zip_safe=False, # guarantees that importlib.resources.path() is safe
)

