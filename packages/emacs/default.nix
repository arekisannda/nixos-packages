{
  emacs31,
  runCommand,
  patchutils,
}:

let
  canvas-patch =
    runCommand "canvas-31.patch"
      {
        nativeBuildInputs = [ patchutils ];
      }
      ''
        filterdiff -x '*/etc/NEWS' ${./patch/canvas-31.patch} > $out
      '';
in
(emacs31.override {
  withPgtk = true;
  withNativeCompilation = true;
  withTreeSitter = true;
}).overrideAttrs
  (super: {
    outputs = (super.outputs or [ "out" ]) ++ [ "dev" ];

    patches = (super.patches or [ ]) ++ [
      canvas-patch
    ];

    # Don't pass --includedir=$dev/include to configure
    # (Emacs embeds its configure flags in $out → would reference $dev → cycle)
    setOutputFlags = false;

    # Don't move $out/include into $dev; Emacs packages expect it in $out
    moveToDev = false;

    # Copy (not move) the headers into the dev output
    postInstall = (super.postInstall or "") + ''
      mkdir -p $dev
      cp -r $out/include $dev/include
    '';
  })
