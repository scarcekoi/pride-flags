{
  description = "catppuccin-flags dev + CI environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python3
          python3Packages.pyyaml

          inkscape
          libwebp
          curl
          git

          xorg.libX11
          xorg.libXcursor
          xorg.libXi
          mesa
          fontconfig
          harfbuzz
          freetype
          zlib
          libjpeg
          libpng
          giflib
          libglvnd
        ];

        shellHook = ''
          set -e

          mkdir -p .nix-tools/bin

          if [ ! -x .nix-tools/bin/whiskers ]; then
            echo "Fetching whiskers binary..."
            curl -L -o .nix-tools/bin/whiskers \
              https://github.com/catppuccin/whiskers/releases/latest/download/whiskers-x86_64-unknown-linux-gnu
            chmod +x .nix-tools/bin/whiskers
          fi

          chmod +x resources/Aseprite.AppImage
          ln -sf $PWD/resources/Aseprite.AppImage $PWD/aseprite

          export PATH="$PWD/.nix-tools/bin:$PWD:$PATH"
        '';
      };
    };
}
