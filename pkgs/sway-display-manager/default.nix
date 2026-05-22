{
  python3,
  python3Packages,
}:

with python3Packages;

buildPythonPackage {
  pname = "sway-display-manager";
  version = "0.0.1";

  src = ./.;

  propagatedBuildInputs = [
    i3ipc
    pyyaml
  ];

  pyproject = true;

  buildInputs = [
    python3
    setuptools
  ];
}
