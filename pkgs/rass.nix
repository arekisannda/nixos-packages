{
  fetchFromGitHub,
  python3,
  python3Packages,
}:

with python3Packages;

buildPythonPackage rec {
  pname = "rass";
  version = "0.3.3";

  src = fetchFromGitHub {
    owner = "joaotavora";
    repo = "rassumfrassum";
    rev = "v${version}";
    sha256 = "sha256-3Hcews5f7o45GUmFdpLwkAHf0bthC1tUikkxau952Ec=";
  };

  # patchPhase = ''
  #   echo "from setuptools import setup; setup()" > setup.py
  # '';

  pyproject = true;

  buildInputs = [
    python3
    setuptools
  ];
}
