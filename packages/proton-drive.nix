{ stdenv }:

stdenv.mkDerivation rec {
  pname = "proton-drive";
  version = "0.8.8";

  src = builtins.fetchurl {
    url = "https://proton.me/download/drive/cli/${version}/linux-x64/proton-drive";
    sha256 = "sha256-lEPXcXGciSeQ2xfm8C7Nma18U1kzKfOmfHdnfc5XdzU=";
  };

  dontUnpack = true;
  dontConfigure = true;
  dontBuild = true;
  dontStrip = true;

  buildInputs = [ ];

  installPhase = ''
    runHook preInstall
    install -Dm755 $src $out/bin/proton-drive
    runHook postInstall
  '';
}
