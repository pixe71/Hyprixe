{ config, lib, pkgs, ... }:

let
  cfg = config.programs.hyprixe.sddm;
  packages = import ../packages/sddm.nix { inherit pkgs; dynamic = cfg.sync.enable; };
  service = "hyprixe-sddm-sync";
  receiver = "hyprixe-theme";
  socketGroup = "hyprixe-sddm-sync";
  realUsers = lib.filter (name: config.users.users.${name}.isNormalUser or false)
    (lib.unique cfg.sync.users);
in
{
  options.programs.hyprixe.sddm = {
    enable = lib.mkEnableOption "the Frosted Glass theme for the host's SDDM";
    sync.enable = lib.mkEnableOption "publication of login wallpaper and colours from authorized desktop accounts";
    sync.users = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Declared local, normal user names allowed to publish the shared greeter snapshot.";
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = !cfg.enable || config.services.displayManager.sddm.enable;
          message = "programs.hyprixe.sddm.enable requires the host to enable services.displayManager.sddm.";
        }
        {
          assertion = !cfg.sync.enable || (cfg.enable && realUsers != [ ] && realUsers == lib.unique cfg.sync.users);
          message = "Hyprixe SDDM synchronization requires the Hyprixe greeter and a list of declared local, normal users.";
        }
        {
          assertion = !cfg.sync.enable || (
            !(lib.elem receiver cfg.sync.users) && !(config.users.users.${receiver}.isNormalUser or false)
          );
          message = "hyprixe-theme is reserved for the isolated Hyprixe SDDM receiver and cannot be a publisher or a normal account.";
        }
      ];
    }
    (lib.mkIf cfg.enable {
      environment.systemPackages = [ packages.theme ];
      environment.pathsToLink = [ "/share/sddm/themes" ];
      fonts.packages = [ pkgs.jetbrains-mono ];
      services.displayManager.sddm = {
        theme = packages.name;
        extraPackages = with pkgs.kdePackages; [ qtdeclarative qtsvg ];
        settings = {
          General.InputMethod = "";
          Theme.EnableAvatars = false;
        };
      };
    })
    (lib.mkIf (cfg.enable && cfg.sync.enable) {
      users.groups.${receiver} = { };
      users.groups.${socketGroup} = { };
      users.users = {
        ${receiver} = {
          isSystemUser = true;
          group = receiver;
          shell = pkgs.shadow + "/bin/nologin";
        };
      } // lib.genAttrs cfg.sync.users (_: { extraGroups = [ socketGroup ]; });

      environment.etc."hyprixe/sddm-sync-users.json" = {
        mode = "0444";
        text = builtins.toJSON { format = 2; users = realUsers; };
      };
      systemd.sockets.${service} = {
        description = "Hyprixe login theme synchronization socket";
        wantedBy = [ "sockets.target" ];
        socketConfig = {
          ListenSequentialPacket = "/run/${service}.sock";
          SocketMode = "0660";
          SocketGroup = socketGroup;
          RemoveOnStop = true;
        };
      };
      systemd.services.${service} = {
        description = "Hyprixe login theme snapshot receiver";
        requires = [ "${service}.socket" ];
        after = [ "${service}.socket" ];
        serviceConfig = {
          Type = "exec";
          ExecStart = lib.getExe packages.receiver;
          User = receiver;
          Group = receiver;
          StateDirectory = "hyprixe/theme";
          StateDirectoryMode = "0755";
          UMask = "0022";
          NoNewPrivileges = true;
          ProtectSystem = "strict";
          ProtectHome = true;
          PrivateTmp = true;
          PrivateDevices = true;
          PrivateNetwork = true;
          ProtectKernelTunables = true;
          ProtectKernelModules = true;
          ProtectControlGroups = true;
          RestrictSUIDSGID = true;
          RestrictAddressFamilies = [ "AF_UNIX" ];
          CapabilityBoundingSet = "";
          LockPersonality = true;
          MemoryMax = "512M";
          TasksMax = 8;
          TimeoutStopSec = "5s";
        };
      };
    })
  ];
}
