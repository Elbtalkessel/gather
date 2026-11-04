{ pkgs, lib, ... }:
{
  name = "gather";
  languages = {
    python = {
      enable = true;
      uv = {
        enable = true;
        sync.enable = true;
      };
    };
  };
  # `ruff` and `ty` are provided by nixpkgs rather than PyPI because the PyPI
  # wheels are dynamically linked and do not run on NixOS without a stub ld.
  # Keeping them in the devenv shell makes the gate commands (`ruff check .`,
  # `ty check`) work everywhere `devenv` works.
  packages = [
    pkgs.ruff
    pkgs.ty
  ];
  enterShell = ''
    export VIRTUAL_ENV=${toString ./.devenv/state/venv}
  '';
  git-hooks.hooks = {
    ruff.enable = true;
    ty = {
      enable = true;
      name = "ty";
      entry = "${lib.getExe pkgs.ty} check";
      files = "\\.py$";
      language = "system";
      pass_filenames = true;
    };
  };
}
