{ stdenv }:

stdenv.mkDerivation rec {
  pname = "lspx";
  version = "0.3.1";

  src = fetchTarball {
    url = "https://github.com/thefrontside/lspx/releases/download/v${version}/lspx-x86_64-unknown-linux-gnu.tar.gz";
    sha256 = "sha256-/Q1Hs6h/2R47jjhMgRVKlrEqJUmtTs/yY3e11nbZ/vE=";
  };

  dontPatchELF = true;
  dontStrip = true;

  buildInputs = [ ];

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin
    cp lspx $out/bin
    runHook postInstall
  '';
}
