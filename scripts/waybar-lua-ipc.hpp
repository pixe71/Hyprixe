// Minimal Lua workspace IPC compatibility for Waybar 0.12.
// SPDX-License-Identifier: GPL-3.0-or-later
// Same hl.dsp calls as upstream Waybar's newer Lua-capable IPC backend.
#pragma once
#include <string>

namespace hyprixe {
inline std::string luaQuote(const std::string& value) {
  static constexpr char hex[] = "0123456789abcdef";
  std::string result = "\"";
  for (unsigned char ch : value) {
    if (ch == '"' || ch == '\\') {
      result += '\\';
      result += static_cast<char>(ch);
    } else if (ch < 32 || ch == 127) {
      result += "\\x";
      result += hex[ch >> 4];
      result += hex[ch & 15];
    } else {
      result += static_cast<char>(ch);
    }
  }
  return result + '"';
}

inline std::string waybarLuaRequest(const std::string& request) {
  const std::string workspace = "dispatch workspace ";
  const std::string current = "dispatch focusworkspaceoncurrentmonitor ";
  const std::string special = "dispatch togglespecialworkspace";
  if (request.starts_with(workspace))
    return "/dispatch hl.dsp.focus({ workspace = " + luaQuote(request.substr(workspace.size())) + " })";
  if (request.starts_with(current))
    return "/dispatch hl.dsp.focus({ workspace = " + luaQuote(request.substr(current.size())) + ", on_current_monitor = true })";
  if (request == special)
    return "/dispatch hl.dsp.workspace.toggle_special()";
  if (request.starts_with(special + " "))
    return "/dispatch hl.dsp.workspace.toggle_special(" + luaQuote(request.substr(special.size() + 1)) + ")";
  return request;
}
}
