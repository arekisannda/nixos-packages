{
  lib,
  fetchFromGitHub,
  buildNpmPackage,
}:

buildNpmPackage rec {
  pname = "action-languageserver";
  version = "0.3.49";

  src = fetchFromGitHub {
    owner = "actions";
    repo = "languageservices";
    rev = "release-v${version}";
    sha256 = "sha256-bW1tu/xrBz3Ng8GY8OjB/clubJy9qcwWqbLXDlHwRQ0=";
  };

  npmDepsHash = "sha256-M5mRN0B9+5YvOJlAUZm4eO8MaKHSWNsMhr59gtqF9Uo=";
  npmInstallFlags = [ "--include=dev" ];
  makeCacheWritable = true;

  postPatch = ''
    cp ${./package-lock.json} package-lock.json
  '';

  buildPhase = ''
    npm run build --workspaces --if-present
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,dist}
    cp -r languageserver/dist/* $out/dist
    cp -r languageserver/bin/* $out/bin

    runHook postInstall
  '';

  meta = {
    description = "Language services for GitHub Actions workflows and expressions.";
    homepage = "https://github.com/actions/languageservices";
  };
}
