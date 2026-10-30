# Hyprixe interactive shell only. Bash scripts keep their own shebangs.
# The installer prepares the pinned daemon; never download during startup.
typeset -g GITSTATUS_AUTO_INSTALL=0
# Keep the upstream Instant Prompt preamble before initialization and console I/O.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

typeset -U path
path=("$HOME/.local/bin" $path)
typeset -g HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/hyprixe/zsh/history"
typeset -g HISTSIZE=50000 SAVEHIST=50000
mkdir -p -m 700 -- "${HISTFILE:h}" "${XDG_CACHE_HOME:-$HOME/.cache}/hyprixe/zsh"
setopt EXTENDED_HISTORY SHARE_HISTORY HIST_IGNORE_ALL_DUPS HIST_SAVE_NO_DUPS
setopt HIST_FIND_NO_DUPS HIST_REDUCE_BLANKS HIST_IGNORE_SPACE

autoload -Uz compinit
compinit -d "${XDG_CACHE_HOME:-$HOME/.cache}/hyprixe/zsh/zcompdump-${ZSH_VERSION}"
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'
bindkey -e
bindkey '^[[A' history-beginning-search-backward
bindkey '^[[B' history-beginning-search-forward

source "$HOME/.p10k.zsh"
source "${XDG_DATA_HOME:-$HOME/.local/share}/hyprixe/powerlevel10k/powerlevel10k.zsh-theme"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#6d919c'
source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh

typeset -A ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[default]='fg=#e6f1f4'
ZSH_HIGHLIGHT_STYLES[command]='fg=#b4f9f8'
ZSH_HIGHLIGHT_STYLES[builtin]='fg=#b4f9f8'
ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#f7768e'
ZSH_HIGHLIGHT_STYLES[path]='fg=#7ed6ff'
ZSH_HIGHLIGHT_STYLES[single-quoted-argument]='fg=#cbe2e8'
ZSH_HIGHLIGHT_STYLES[double-quoted-argument]='fg=#cbe2e8'
# Last plugin: it wraps the widgets installed by completion/autosuggestions.
source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
