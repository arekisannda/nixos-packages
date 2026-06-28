{ writeTextFile, ... }:

writeTextFile {
  name = "pinentry-rofi";
  destination = "/bin/pinentry-rofi";
  executable = true;
  text = builtins.readFile ./pinentry-rofi;
}
