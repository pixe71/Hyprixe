-- Concrete IDs create real persistent workspaces, even when empty (Hyprland 0.56.2).
-- No monitor binding: Hyprland selects an available output automatically.
for id = 1, 4 do
  hl.workspace_rule({ workspace = tostring(id), persistent = true })
end
