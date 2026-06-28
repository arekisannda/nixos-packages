{
  stdenv,
  fetchFromGitHub,
  python3,
  python3Packages,
}:

with python3Packages;

stdenv.mkDerivation rec {
  pname = "swayrst";
  version = "1.3.0";

  src = fetchFromGitHub {
    owner = "Nama";
    repo = "swayrst";
    rev = "1.3";
    sha256 = "sha256-+tIsSegkLdqNDbrT47e5RusdWBmzUWNlVYLDwLEQ5v4=";
  };

  dontPatchELF = true;
  dontStrip = true;

  nativeBuildInputs = [
    python3
    i3ipc
    pyinstaller
  ];

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin
    python3 -m PyInstaller --onefile swayrst/swayrst.py
    cp dist/swayrst $out/bin
    runHook postInstall
  '';
}
